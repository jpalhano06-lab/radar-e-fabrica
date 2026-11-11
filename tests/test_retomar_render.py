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
    assert vista == [True]  # durante o render a marca está lá: a fábrica caindo aqui deixa ela para a partida
    assert not (tmp_path / "p" / api.RENDER_ANDAMENTO).exists()
