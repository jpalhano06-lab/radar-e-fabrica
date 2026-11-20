"""Uma de cada vez: as etapas que ficam muito mais lentas quando dois vídeos fazem ao mesmo tempo.

Medido em 2026-11-07, nos 74 vídeos desde 17/10 (segundos por cena, a mediana, com e sem outro vídeo na MESMA
etapa ao mesmo tempo):

- Render: juntar e mixar: 1,24 sozinho, 3,47 com outro junto (6 casos). É FFmpeg no processador: dois juntos levam
  quase 3 vezes cada, então um depois do outro termina os dois antes.
- Conferência das completadas: 1,43 sozinha, 4,12 com outra junto (17 casos).
- As outras etapas perdem pouco ou nada (imagens de IA 2,42 e 2,93; busca de acervo 2,88 e 2,87; narração 1,49 e
  2,32): seguem em paralelo, porque um depois do outro levaria o dobro.

Os números são poucos e a fábrica mudou nesse tempo, então o limite fica no config.yaml (vez:), e o tempo de espera
vai para o tempos.json como "Esperando a vez: ...", para medir de novo. 0 desliga o limite da etapa.
Vale só dentro do mesmo servidor (os vídeos que o site e o Radar mandam); a linha de comando é outro processo.
"""
import threading
from contextlib import contextmanager

PADRAO = {"render_juntar": 1, "conferencia_completadas": 1}
_TRAVA = threading.Lock()
_SEMAFOROS: dict[str, threading.BoundedSemaphore] = {}
_MINHAS = threading.local()   # as vagas que ESTE fio está segurando agora, para soltar quando ele fica parado


def _minhas() -> list:
    if not hasattr(_MINHAS, "vagas"):
        _MINHAS.vagas = []
    return _MINHAS.vagas


def _semaforo(nome: str, projeto):
    try:
        n = int(((projeto.config.get("vez") or {}).get(nome, PADRAO.get(nome, 0))) or 0)
    except (TypeError, ValueError, AttributeError):
        n = PADRAO.get(nome, 0)
    if n <= 0:
        return None
    with _TRAVA:
        # criado uma vez com o número da primeira chamada: trocar o semáforo com alguém dentro estragaria a conta
        return _SEMAFOROS.setdefault(nome, threading.BoundedSemaphore(n))


@contextmanager
def na_vez(nome: str, projeto, log=print, rotulo: str = ""):
    """Entra na etapa quando houver vaga. A espera é medida à parte, e a etapa em si continua medida sozinha."""
    s = _semaforo(nome, projeto)
    if s is None:
        yield
        return
    if not s.acquire(blocking=False):
        from . import tempos
        log(f"  {rotulo or nome}: outro vídeo está nesta etapa, esperando a vez")
        with tempos.medir(projeto, f"Esperando a vez: {rotulo or nome}", log=log):
            s.acquire()
    _minhas().append((nome, s))
    try:
        yield
    finally:
        try:
            _minhas().remove((nome, s))
        except ValueError:
            pass
        s.release()


@contextmanager
def solto(log=print, motivo: str = ""):
    """Solta as vagas que este fio segura enquanto ele fica parado de propósito (a pausa do vídeo), e pega de volta
    na saída, esperando a vez como qualquer outro.

    Sem isso, o vídeo pausado DENTRO de uma etapa de vaga única segurava a vaga enquanto dormia, e os outros vídeos
    esperavam a despausa para sempre: em 17/11/2026 o europa-s-ocean-under-the-ice foi pausado dentro da Conferência
    das completadas e travou o british-heart-foundation por 45 min, sem nenhuma chamada de modelo.

    A vaga sai da lista do fio antes de qualquer log: assim a pausa que o próprio log dispara não solta duas vezes."""
    vagas = _minhas()[:]
    if not vagas:
        yield
        return
    del _minhas()[:]
    for _, s in vagas:
        s.release()
    log(f"  {motivo or 'este vídeo parou'}: a vaga de {', '.join(n for n, _ in vagas)} fica livre para outro vídeo")
    try:
        yield
    finally:
        for nome, s in vagas:
            if not s.acquire(blocking=False):
                log(f"  esperando a vez de novo: {nome}")
                s.acquire()
        _minhas().extend(vagas)
