"""As pagas revezam (2026-11-22): com os gratuitos esgotados, cada chamada começa por uma paga diferente da roda, e
uma irmã no limite do minuto não faz a outra esperar."""
import time

from fabrica import openrouter_local as orl


class Projeto:
    def __init__(self, roda):
        self.config = {"openrouter": {"pagas_juntas": roda, "espera_pela_rapida": 30, "espera_pelo_gratis": 60}}


ROTAS = ["groq:qwen/qwen3.8-27b", "a/paga-1", "b/paga-2", "c/paga-3", "d/reserva"]


def test_cada_chamada_comeca_por_uma_paga_da_roda(monkeypatch):
    monkeypatch.setattr(orl, "_GIRO", [0])
    p = Projeto(["a/paga-1", "b/paga-2", "c/paga-3"])
    primeiras = [orl._revezar(p, ROTAS)[1] for _ in range(6)]
    assert primeiras == ["a/paga-1", "b/paga-2", "c/paga-3"] * 2
    girada = orl._revezar(p, ROTAS)
    assert girada[0] == "groq:qwen/qwen3.8-27b"      # o gratuito sempre na frente
    assert girada[-1] == "d/reserva"                 # a paga fora da roda fica atrás
    assert sorted(girada) == sorted(ROTAS)


def test_sem_roda_a_ordem_fica_como_estava(monkeypatch):
    assert orl._revezar(Projeto([]), ROTAS) == ROTAS
    assert orl._revezar(Projeto(["a/paga-1"]), ROTAS) == ROTAS


def test_irma_no_limite_do_minuto_nao_faz_esperar(monkeypatch):
    p = Projeto(["a/paga-1", "b/paga-2"])
    monkeypatch.setattr(orl, "_FORA_DO_AR", {"a/paga-1": time.time() + 10})
    assert orl._espera_por_melhor(p, ROTAS, "b/paga-2") == (None, None)
    # a reserva fora da roda continua esperando a paga rápida, como antes
    segundos, melhor = orl._espera_por_melhor(p, ROTAS, "d/reserva")
    assert melhor == "a/paga-1" and segundos > 0
