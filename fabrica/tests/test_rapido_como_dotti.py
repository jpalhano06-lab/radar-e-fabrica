"""As 5 mudanças para entregar rápido como o robô da Dotti (2026-11-22): a cadeia paga primeiro, o juiz uma vez só,
o prazo da busca pelo rendimento, as animações em paralelo e o 403 do YouTube sem baixar o vídeo inteiro. Sem rede."""
import sys
import time
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fabrica import garimpo, midia, openrouter_local  # noqa: E402
from fabrica.config import config_geral  # noqa: E402


def _cadeia(gratis_primeiro, pagas=("google/gemini-3.1-flash-lite", "google/gemma-4-26b-a4b-it")):
    principais = ["google/gemini-3.1-flash-lite", "google/gemma-4-26b-a4b-it", "gemini:gemini-3.1-flash-lite",
                  "groq:qwen/qwen3.8-27b", "google/gemma-4-31b-it:free"]
    return SimpleNamespace(config={"openrouter": {"principais": principais, "pagas_juntas": list(pagas),
                                                  "gratis_primeiro": gratis_primeiro}})


def test_pagas_primeiro_e_gratis_de_reserva():
    projeto = _cadeia(False)
    for _ in range(2):
        rotas = openrouter_local._revezar(projeto, openrouter_local.principais(projeto))
        assert set(rotas[:2]) == {"google/gemini-3.1-flash-lite", "google/gemma-4-26b-a4b-it"}
        assert rotas[2:] == ["gemini:gemini-3.1-flash-lite", "groq:qwen/qwen3.8-27b", "google/gemma-4-31b-it:free"]


def test_jeito_antigo_ainda_poe_os_gratis_na_frente():
    projeto = _cadeia(True)
    rotas = openrouter_local._revezar(projeto, openrouter_local.principais(projeto))
    assert rotas[:2] == ["groq:qwen/qwen3.8-27b", "google/gemma-4-31b-it:free"]


def test_config_da_fabrica_comeca_pela_paga_rapida():
    cfg = config_geral()
    projeto = SimpleNamespace(config=cfg)
    assert openrouter_local.gratis_primeiro(projeto) is False
    assert not openrouter_local.gratuita(openrouter_local.principais(projeto)[0])
    assert not openrouter_local.gratuita(openrouter_local.visao(projeto)[0])
    assert cfg["animacoes"]["paralelo"] >= 4


def test_403_do_youtube_nao_baixa_o_video_inteiro(tmp_path, monkeypatch):
    chamadas = []
    erro = "ERROR: unable to download video data: HTTP Error 403: Forbidden"
    monkeypatch.setattr(garimpo, "_rodar_com_prazo", lambda c, p: (chamadas.append(c), (1, erro, ""))[1])
    codigo, _, _ = garimpo._baixar_por_rotas({"id": "x", "arquivo": "u", "yt_duracao": 300}, tmp_path / "t.mp4",
                                             10, 20, None, 60, log=lambda *_: None)
    assert codigo == 1 and len(chamadas) == 2  # o caminho de sempre e a outra rota; o vídeo inteiro não
    assert not any("--download-sections" not in c for c in chamadas)


def _futuro(pronto):
    f = Future()
    if pronto:
        f.set_result([])
    return f


def test_busca_para_pelo_rendimento(monkeypatch):
    projeto = SimpleNamespace(config={"midia": {"rendimento_depois_de_min": 1, "rendimento_limite_s": 60,
                                                "prazo_da_busca_min": 0}}, offline=False)
    monkeypatch.setattr(midia, "busca_rapida", lambda p, c: c["ini"] >= 300)
    # 2 lotes prontos em 120 s (1 por minuto) e 8 por fazer: levariam 8 min, acima do limite de 60 s
    futuros = [_futuro(True), _futuro(True)] + [_futuro(False) for _ in range(8)]
    lotes = [[{"n": 1, "ini": 0}], [{"n": 2, "ini": 0}]] + [[{"n": 10 + k, "ini": 400}] for k in range(8)]
    avisos = []
    _, cancelados = midia._aplicar_com_prazo(futuros, lotes, lambda r: None, projeto, time.time() - 120, avisos.append)
    assert cancelados == {10 + k for k in range(8)}
    assert "no ritmo de agora" in avisos[0]


def test_busca_no_ritmo_bom_segue(monkeypatch):
    projeto = SimpleNamespace(config={"midia": {"rendimento_depois_de_min": 1, "rendimento_limite_s": 600,
                                                "prazo_da_busca_min": 0}}, offline=False)
    monkeypatch.setattr(midia, "busca_rapida", lambda p, c: True)
    futuros = [_futuro(True) for _ in range(5)]
    lotes = [[{"n": k, "ini": 400}] for k in range(5)]
    _, cancelados = midia._aplicar_com_prazo(futuros, lotes, lambda r: None, projeto, time.time() - 120, print)
    assert cancelados == set()
