"""Uma conta do YouTube por canal (2026-11-17). O token do OAuth fica preso ao canal escolhido na tela de
consentimento do Google, então publicar em vários canais pede um login por canal."""
import json

import pytest

from fabrica import youtube_publicar as yt


@pytest.fixture
def contas(tmp_path, monkeypatch):
    monkeypatch.setattr(yt, "ARQUIVO_CONTA", tmp_path / "youtube_conta.json")
    monkeypatch.setattr(yt, "ARQUIVO_CONTAS", tmp_path / "youtube_contas.json")
    return tmp_path


def _conta(canal_id, nome="Canal"):
    return {"canal_id": canal_id, "canal_nome": nome, "refresh_token": "r-" + canal_id,
            "access_token": "a-" + canal_id, "expira_em": 1e12}


def test_sem_nada_conectado(contas):
    assert yt.contas() == [] and yt.conta() is None and yt.conectada() is False


def test_a_conta_unica_de_antes_vira_a_primeira(contas):
    (contas / "youtube_conta.json").write_text(json.dumps(_conta("UC1")), encoding="utf-8")
    assert [c["canal_id"] for c in yt.contas()] == ["UC1"]
    assert yt.conta()["canal_id"] == "UC1" and yt.conectada("UC1")


def test_cada_canal_guarda_a_sua(contas):
    yt._salvar_conta(_conta("UC1", "Um"))
    yt._salvar_conta(_conta("UC2", "Dois"))
    assert sorted(c["canal_id"] for c in yt.contas()) == ["UC1", "UC2"]
    assert yt.conta("UC2")["canal_nome"] == "Dois"
    # sem dizer o canal, com mais de um conectado, não há escolha automática: nunca postar no canal errado
    assert yt.conta() is None
    assert yt.conectada() and yt.conectada("UC1") and not yt.conectada("UC3")


def test_token_pede_o_canal_quando_ha_mais_de_um(contas):
    yt._salvar_conta(_conta("UC1"))
    assert yt._token_valido() == "a-UC1"          # uma só: não precisa dizer qual
    yt._salvar_conta(_conta("UC2"))
    with pytest.raises(SystemExit, match="mais de um canal"):
        yt._token_valido()
    assert yt._token_valido("UC2") == "a-UC2"


def test_desconectar_tira_so_aquele_canal(contas, monkeypatch):
    monkeypatch.setattr(yt.httpx, "post", lambda *a, **k: None)
    yt._salvar_conta(_conta("UC1"))
    yt._salvar_conta(_conta("UC2"))
    yt.desconectar("UC1")
    assert [c["canal_id"] for c in yt.contas()] == ["UC2"]
