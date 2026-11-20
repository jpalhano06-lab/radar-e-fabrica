"""As cotas diárias grátis que acabaram, gravadas em disco até a hora em que elas voltam.

Pedido do usuário em 2026-11-16: API grátis que esgotou a cota do dia não pode ser tentada de novo no mesmo dia. Antes
o Gemini e os modelos :free do OpenRouter ficavam de lado só na memória, por 1 hora, e a fábrica religada esquecia
tudo e voltava a bater neles a cada cena (no 15-cheap-poundland, centenas de "o Gemini não descreveu" seguidos).

Cada rota fica de lado até a virada do dia dela: o Gemini grátis volta à meia-noite do Pacífico (08:00 UTC, a conta do
horário de inverno; no de verão sobra uma hora a mais, que é melhor que tentar cedo), o OpenRouter :free à meia-noite UTC.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone

from .config import RAIZ

ARQUIVO = RAIZ / "cotas_esgotadas.json"
_trava = threading.Lock()


def proxima_virada(hora_utc: int, agora: float | None = None) -> float:
    """O próximo instante (time.time) em que o relógio UTC passa por hora_utc:00."""
    atual = datetime.fromtimestamp(time.time() if agora is None else agora, timezone.utc)
    virada = atual.replace(hour=hora_utc, minute=0, second=0, microsecond=0)
    if virada <= atual:
        virada += timedelta(days=1)
    return virada.timestamp()


def virada_do_gemini(agora: float | None = None) -> float:
    return proxima_virada(8, agora)


def virada_do_openrouter(agora: float | None = None) -> float:
    return proxima_virada(0, agora)


def _ler() -> dict:
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    agora = time.time()
    return {k: float(v) for k, v in dados.items() if isinstance(v, (int, float)) and v > agora}


def esgotadas() -> dict:
    """{rota: até quando} das cotas do dia que ainda não voltaram."""
    with _trava:
        return _ler()


def ate(rota: str) -> float:
    return esgotadas().get(rota, 0.0)


def marcar(rota: str, ate_quando: float) -> None:
    """Grava a rota como esgotada até ate_quando. Falha de disco não para a chamada: fica só na memória de quem chamou."""
    with _trava:
        dados = _ler()
        dados[rota] = max(dados.get(rota, 0.0), float(ate_quando))
        try:
            temporario = ARQUIVO.with_suffix(".tmp")
            temporario.write_text(json.dumps(dados, indent=1), encoding="utf-8")
            temporario.replace(ARQUIVO)
        except OSError:
            pass
