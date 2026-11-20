"""A cota do dia que acabou fica de lado até a virada do dia, gravada em disco (pedido do usuário em 2026-11-16)."""
import time
from datetime import datetime, timezone

from fabrica import cotas, gemini_local


def _ts(texto):
    return datetime.fromisoformat(texto).replace(tzinfo=timezone.utc).timestamp()


def test_virada_do_dia():
    assert cotas.virada_do_openrouter(_ts("2026-11-16T23:30:00")) == _ts("2026-11-17T00:00:00")
    assert cotas.virada_do_gemini(_ts("2026-11-16T07:59:00")) == _ts("2026-11-16T08:00:00")
    assert cotas.virada_do_gemini(_ts("2026-11-16T08:00:00")) == _ts("2026-11-17T08:00:00")


def test_marcada_sobrevive_a_fabrica_religada():
    cotas.marcar("google/gemma-4-31b-it:free", time.time() + 600)
    cotas.marcar("velha:free", time.time() - 1)  # já voltou: não conta
    assert set(cotas.esgotadas()) == {"google/gemma-4-31b-it:free"}
    assert cotas.ate("google/gemma-4-31b-it:free") > time.time()


def test_gemini_esgotado_em_disco_nao_e_tentado():
    cotas.marcar("gemini:gemini-3.1-flash-lite", time.time() + 600)
    assert gemini_local._esgotado("gemini-3.1-flash-lite")
    assert not gemini_local._esgotado("gemini-3.8-flash")
