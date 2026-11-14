"""O modelo de visão aponta na folha de quadros onde o trecho do garimpo começa (2026-11-14)."""

import pytest

from fabrica import garimpo, midia, openrouter_local


class _P:
    offline = False
    config = {}

    def __init__(self, pasta):
        self.pasta = pasta

    def caminho(self, *partes):
        return self.pasta.joinpath(*partes)


def _armar(monkeypatch, tmp_path, tempos, numero):
    monkeypatch.setattr(garimpo, "cfg_do_projeto", lambda p: {})
    monkeypatch.setattr(garimpo, "folha_de_quadros", lambda c, destino, cfg=None: tempos)
    monkeypatch.setattr(openrouter_local.VISAO, "perguntar", lambda *a, **k: {"numero": numero})
    return _P(tmp_path)


CENA = {"n": 6, "texto": "Lidl shelves", "busca": "lidl shelves"}
CAND = {"id": "v", "arquivo": "u", "yt_duracao": 300}


def test_quadro_escolhido_vira_o_inicio_do_trecho(monkeypatch, tmp_path):
    p = _armar(monkeypatch, tmp_path, {1: 50.0, 2: 120.0}, 2)
    assert midia._momento_pelos_quadros(p, CENA, CAND, "0006") == 119.0


def test_nenhum_quadro_serve_nem_baixa(monkeypatch, tmp_path):
    p = _armar(monkeypatch, tmp_path, {1: 50.0}, 0)
    with pytest.raises(garimpo.TrechoIndisponivel):
        midia._momento_pelos_quadros(p, CENA, CAND, "0006")


def test_sem_storyboard_o_corte_e_sorteado(monkeypatch, tmp_path):
    p = _armar(monkeypatch, tmp_path, {}, 1)
    assert midia._momento_pelos_quadros(p, CENA, CAND, "0006") is None


def test_visao_fora_do_ar_o_corte_e_sorteado(monkeypatch, tmp_path):
    p = _armar(monkeypatch, tmp_path, {1: 50.0}, 1)

    def falha(*a, **k):
        raise RuntimeError("sem visão")

    monkeypatch.setattr(openrouter_local.VISAO, "perguntar", falha)
    assert midia._momento_pelos_quadros(p, CENA, CAND, "0006") is None
