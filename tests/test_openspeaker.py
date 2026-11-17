"""Narração pelo OpenSpeaker (ai33.pro), a alternativa barata à GenAIPro (troca pedida pelo usuário em 2026-11-17).

O que estes testes seguram: o prefixo do provedor no voice_id (os perfis guardam o id cru da ElevenLabs), o
limite de velocidade, a tarefa retomada que não é cobrada duas vezes, o tempo das palavras vindo do json ou do
srt, e o preço do crédito, que é de outro pacote e não pode cair no da GenAIPro.
"""
import json

import pytest

from fabrica import custos_reais, openspeaker


# ---------------------------------------------------------------- voz e corpo da tarefa

def test_id_cru_da_elevenlabs_ganha_o_prefixo():
    assert openspeaker.voz_prefixada("hpp4J3VqNfWAUOO0d1Us") == "elevenlabs_hpp4J3VqNfWAUOO0d1Us"


def test_id_que_ja_tem_prefixo_fica_como_esta():
    for voz in ("minimax_male-qn-qingse", "clone_123", "edge_vi-VN-HoaiMyNeural"):
        assert openspeaker.voz_prefixada(voz) == voz


def test_velocidade_fica_dentro_do_que_a_api_aceita():
    assert openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc", "velocidade": 2.0})["speed"] == 1.5
    assert openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc", "velocidade": 0.1})["speed"] == 0.5


def test_corpo_pede_a_transcricao():
    corpo = openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc"})
    assert corpo["with_transcript"] == "true" and corpo["text"] == "oi"


def test_sem_voz_no_perfil_explica_o_que_fazer():
    with pytest.raises(SystemExit) as erro:
        openspeaker.corpo_da_tarefa("oi", {"voice_id": "COLE AQUI"})
    assert "voz.voice_id" in str(erro.value)


# ---------------------------------------------------------------- tempo das palavras

def test_json_de_palavras_em_segundos():
    palavras = openspeaker.ler_json_de_palavras({"words": [{"word": "oi", "start": 0.0, "end": 0.4}]})
    assert palavras == [("oi", 0.0, 0.4)]


def test_json_em_milissegundos_vira_segundos():
    palavras = openspeaker.ler_json_de_palavras([{"text": "bom", "start": 12000, "end": 12500}])
    assert palavras == [("bom", 12.0, 12.5)]


def test_json_por_trechos():
    dados = {"segments": [{"words": [{"word": "a", "start": 0, "end": 1}]},
                          {"words": [{"word": "b", "start": 1, "end": 2}]}]}
    assert [p[0] for p in openspeaker.ler_json_de_palavras(dados)] == ["a", "b"]


def test_json_estragado_nao_derruba():
    assert openspeaker.ler_json_de_palavras({"nada": 1}) == []
    assert openspeaker.ler_json_de_palavras([{"word": "sem tempo"}]) == []


# ---------------------------------------------------------------- narração

class _Resposta:
    def __init__(self, dados=None, conteudo=b""):
        self._dados, self.content = dados or {}, conteudo

    def json(self):
        return self._dados

    def raise_for_status(self):
        pass


def _api_falsa(monkeypatch, tmp_path, srt="1\n00:00:00,000 --> 00:00:01,000\noi mundo\n", custo=224):
    """A API respondendo como a documentação descreve: tarefa criada, tarefa pronta, áudio e legenda."""
    pedidos = []

    def pedir(metodo, caminho, **kw):
        pedidos.append((metodo, caminho))
        if caminho == "/v3/text-to-speech":
            return _Resposta({"success": True, "task_id": "tarefa-1"})
        if caminho.startswith("/v1/task/"):
            return _Resposta({"id": "tarefa-1", "status": "done", "credit_cost": custo,
                              "metadata": {"audio_url": "https://x/a.mp3", "srt_url": "https://x/a.srt"}})
        raise AssertionError(f"pedido inesperado: {caminho}")

    def baixar(url, **kw):
        return _Resposta(conteudo=srt.encode("utf-8") if url.endswith(".srt") else b"MP3")

    monkeypatch.setattr(openspeaker, "_pedir", pedir)
    monkeypatch.setattr(openspeaker.httpx, "get", baixar)
    monkeypatch.setattr(openspeaker, "_arquivo_velocidade", lambda: tmp_path / "openspeaker_vozes.json")
    return pedidos


def test_narrar_grava_o_audio_e_devolve_os_creditos_cobrados(tmp_path, monkeypatch):
    _api_falsa(monkeypatch, tmp_path)
    mp3 = tmp_path / "bloco.mp3"
    palavras, creditos = openspeaker.narrar("oi mundo", {"voice_id": "abc"}, mp3, log=lambda *_: None)
    assert mp3.read_bytes() == b"MP3"
    assert creditos == 224  # o credit_cost da própria tarefa, não uma estimativa
    assert [p[0] for p in palavras] == ["oi", "mundo"]


def test_tarefa_retomada_nao_entra_na_conta_de_novo(tmp_path, monkeypatch):
    pedidos = _api_falsa(monkeypatch, tmp_path)
    mp3 = tmp_path / "bloco.mp3"
    corpo = openspeaker.corpo_da_tarefa("oi mundo", {"voice_id": "abc"})
    mp3.with_name(mp3.name + ".tarefa.json").write_text(
        json.dumps({"id": "tarefa-1", "corpo": corpo}), encoding="utf-8")
    palavras, creditos = openspeaker.narrar("oi mundo", {"voice_id": "abc"}, mp3, log=lambda *_: None)
    assert creditos == 0  # a tarefa já foi paga quando foi criada
    assert palavras and ("POST", "/v3/text-to-speech") not in pedidos  # e nenhuma tarefa nova foi criada


def test_anotacao_some_quando_o_audio_chega(tmp_path, monkeypatch):
    _api_falsa(monkeypatch, tmp_path)
    mp3 = tmp_path / "bloco.mp3"
    openspeaker.narrar("oi mundo", {"voice_id": "abc"}, mp3, log=lambda *_: None)
    assert not mp3.with_name(mp3.name + ".tarefa.json").exists()


def test_tarefa_com_erro_explica_em_portugues(tmp_path, monkeypatch):
    _api_falsa(monkeypatch, tmp_path)
    monkeypatch.setattr(openspeaker, "_pedir", lambda m, c, **kw: _Resposta(
        {"success": True, "task_id": "tarefa-1"} if c == "/v3/text-to-speech"
        else {"status": "error", "error_message": "sem créditos"}))
    with pytest.raises(SystemExit) as erro:
        openspeaker.narrar("oi", {"voice_id": "abc"}, tmp_path / "b.mp3", log=lambda *_: None)
    assert "sem créditos" in str(erro.value)


# ---------------------------------------------------------------- preço

def test_preco_do_openspeaker_nao_sai_do_pacote_da_genaipro():
    config = {"assinaturas": {"genaipro": {"preco_mensal": 22.0, "incluido_no_mes": 1000000}},
              "precos": {"openspeaker_por_mil_creditos": 0.00476}}
    assert custos_reais.preco_por_credito(config)[0] == pytest.approx(0.000022)
    assert custos_reais.preco_por_credito(config, "openspeaker")[0] == pytest.approx(0.00000476)


def test_pacote_comprado_do_openspeaker_manda_no_preco():
    config = {"assinaturas": {"openspeaker": {"plano": "OpenSpeaker 2,1 milhões", "preco_mensal": 10.0,
                                              "incluido_no_mes": 2100000}}}
    por_credito, origem = custos_reais.preco_por_credito(config, "openspeaker")
    assert por_credito == pytest.approx(10 / 2100000)
    assert "OpenSpeaker" in origem


def test_caractere_do_openspeaker_custa_1_29_credito():
    """1,29 é o que a API cobrou de verdade por um bloco de roteiro: 1,12 da fala mais a transcrição."""
    config = {"precos": {"openspeaker_por_mil_creditos": 0.00476}}
    taxa, _ = custos_reais.creditos_por_caractere(config, provedor="openspeaker")
    assert taxa == pytest.approx(1.29)
    # o caractere sai bem mais barato que os US$ 0,000022 da GenAIPro, mesmo gastando mais créditos
    assert custos_reais.preco_por_caractere(config, provedor="openspeaker")[0] == pytest.approx(0.0000061404)
