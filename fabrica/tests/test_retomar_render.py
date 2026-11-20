"""O render interrompido pela fábrica caindo volta sozinho na partida (pedido 92, 2026-11-10)."""

import json

from fastapi import HTTPException

from fabrica import api


def _marca(raiz, nome, retomadas=0, vertical=False):
    pasta = raiz / nome
    pasta.mkdir()
    (pasta / api.RENDER_ANDAMENTO).write_text(json.dumps(
        {"inicio": "2026-11-10T21:57:00", "retomadas": retomadas, "payload": {"vertical": vertical}}), encoding="utf-8")
    return pasta


def test_retoma_o_render_marcado_e_conta_a_retomada(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    pasta = _marca(tmp_path, "groceries", vertical=True)
    (tmp_path / "sem-render").mkdir()
    disparados = []
    monkeypatch.setattr(api, "disparar_render", lambda nome, payload, bg: disparados.append((nome, payload.vertical)))
    assert api.retomar_renders_interrompidos() == ["groceries"]
    assert disparados == [("groceries", True)]
    assert json.loads((pasta / api.RENDER_ANDAMENTO).read_text(encoding="utf-8"))["retomadas"] == 1


def test_desiste_depois_de_retomar_demais(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    pasta = _marca(tmp_path, "derruba", retomadas=api.RENDER_RETOMADAS_MAX)
    monkeypatch.setattr(api, "disparar_render", lambda *a: (_ for _ in ()).throw(AssertionError("não devia renderizar")))
    assert api.retomar_renders_interrompidos() == []
    assert not (pasta / api.RENDER_ANDAMENTO).exists()


def test_recusa_da_fabrica_nao_derruba_a_partida(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    _marca(tmp_path, "criando")

    def recusa(*a):
        raise HTTPException(status_code=409, detail="ainda criando")

    monkeypatch.setattr(api, "disparar_render", recusa)
    assert api.retomar_renders_interrompidos() == []


def test_marca_guarda_o_pedido_e_mantem_as_retomadas(tmp_path):
    api._marcar_render(tmp_path, api.RenderPayload(vertical=True))
    dados = json.loads((tmp_path / api.RENDER_ANDAMENTO).read_text(encoding="utf-8"))
    assert dados["retomadas"] == 0 and dados["payload"]["vertical"] is True
    (tmp_path / api.RENDER_ANDAMENTO).write_text(json.dumps({**dados, "retomadas": 1}), encoding="utf-8")
    api._marcar_render(tmp_path, api.RenderPayload())
    assert json.loads((tmp_path / api.RENDER_ANDAMENTO).read_text(encoding="utf-8"))["retomadas"] == 1


def test_partida_nao_entrega_duas_vezes_o_que_volta_a_renderizar(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    monkeypatch.setattr(api, "_ler_criacao", lambda nome: {"status": "concluido"})
    monkeypatch.setattr(api, "retomar_renders_interrompidos", lambda: ["a"])
    monkeypatch.setattr(api, "entregas_que_faltam", lambda: ["a", "b"])
    entregues = []
    monkeypatch.setattr(api, "iniciar_publicacao", entregues.append)
    api.retomar_criacoes_interrompidas()
    assert entregues == ["b"]


class _Ja:
    def add_task(self, funcao, *a, **k):
        funcao(*a, **k)


def test_render_que_termina_tira_a_marca_e_o_que_cai_deixa(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    (tmp_path / "p").mkdir()
    monkeypatch.setattr(api, "_recusar_se_criando", lambda *a: None)
    monkeypatch.setattr(api, "_recusar_se_ocupado", lambda *a: None)
    monkeypatch.setattr(api, "Projeto", lambda nome: type("P", (), {"config": {}})())
    vista = []

    def erro(p, **k):
        vista.append((tmp_path / "p" / api.RENDER_ANDAMENTO).exists())
        raise RuntimeError("ffmpeg falhou")

    monkeypatch.setattr(api.render, "renderizar", erro)
    api.disparar_render("p", api.RenderPayload(), _Ja())
    assert vista == [True, True]  # durante o render (e a segunda tentativa) a marca está lá: a fábrica caindo aqui deixa ela
    assert not (tmp_path / "p" / api.RENDER_ANDAMENTO).exists()


def _render_falso(monkeypatch, tmp_path, falhas):
    """Projeto "p" com criação concluída; o render falha com cada erro de falhas, em ordem, e depois dá certo."""
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    (tmp_path / "p").mkdir()
    monkeypatch.setattr(api, "_recusar_se_criando", lambda *a: None)
    monkeypatch.setattr(api, "_recusar_se_ocupado", lambda *a: None)
    monkeypatch.setattr(api, "Projeto", lambda nome: type("P", (), {"config": {}, "existe": lambda s, a: False})())
    monkeypatch.setattr(api, "iniciar_revisao_video", lambda nome: None)
    monkeypatch.setattr(api, "iniciar_publicacao", lambda nome: None)
    criacao = {"tarefa_id": "criar_p_1", "projeto": "p", "tipo": "criacao", "status": "concluido", "concluido": True,
               "logs": []}
    (tmp_path / "p" / api.ARQ_CRIACAO).write_text(json.dumps(criacao), encoding="utf-8")
    chamadas = []

    def renderizar(p, **k):
        chamadas.append(1)
        if falhas:
            raise RuntimeError(falhas.pop(0))
        final = tmp_path / "p" / "final.mp4"
        final.write_bytes(b"x")
        return final

    monkeypatch.setattr(api.render, "renderizar", renderizar)
    faxinas = []
    monkeypatch.setattr(api.faxina, "faxinar", lambda log=print, cfg=None, **k: faxinas.append(cfg) or 0)
    return chamadas, faxinas


def test_render_que_falha_tenta_mais_uma_vez_e_da_certo(monkeypatch, tmp_path):
    chamadas, faxinas = _render_falso(monkeypatch, tmp_path, ["ffmpeg falhou"])
    api.disparar_render("p", api.RenderPayload(), _Ja())
    assert len(chamadas) == 2 and faxinas == []
    assert api._ler_criacao("p")["status"] == "concluido"


def test_sem_espaco_faz_faxina_antes_da_segunda_tentativa(monkeypatch, tmp_path):
    chamadas, faxinas = _render_falso(monkeypatch, tmp_path, ["[Errno 28] No space left on device"])
    api.disparar_render("p", api.RenderPayload(), _Ja())
    assert len(chamadas) == 2
    assert faxinas and faxinas[0]["livre_gb"] >= api.FAXINA_FOLGA_RENDER_GB


def test_duas_falhas_param_a_criacao_e_avisam(monkeypatch, tmp_path):
    chamadas, _ = _render_falso(monkeypatch, tmp_path, ["No space left on device", "No space left on device"])
    api.disparar_render("p", api.RenderPayload(), _Ja())
    assert len(chamadas) == 2  # tenta uma vez só, não fica num ciclo
    estado = api._ler_criacao("p")
    assert estado["status"] == "erro" and estado["precisa_voce"] and not estado["concluido"]
    assert "espaço no disco" in estado["erro"]
