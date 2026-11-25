"""Quanto a narração costuma levar, pelas narrações anteriores da mesma voz.

Antes a fábrica só dizia "narrando 12 blocos" e ficava em silêncio até o fim, e a pessoa não sabia se 20 minutos era
normal ou se a fila do provedor tinha pendurado. Agora, antes de gravar, o log diz quanto a voz costuma levar para
aquele tamanho de texto, e avisa uma vez quando a narração passa bem do normal. A medida fica em
narracao_tempos.json, na raiz da fábrica: as últimas 10 narrações de cada provedor e voz, em segundos por mil
caracteres. Nada aqui para a narração.
"""
import json
import statistics
import threading
import time

ARQUIVO = "narracao_tempos.json"
GUARDADAS = 10
MINIMO_DE_MEDIDAS = 2
_trava = threading.Lock()


def _arquivo():
    from .config import RAIZ
    return RAIZ / ARQUIVO


def _ler() -> dict:
    try:
        dados = json.loads(_arquivo().read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def chave(voz) -> str:
    voz = voz or {}
    return f"{voz.get('provedor') or 'genaipro'}:{voz.get('voice_id') or voz.get('voz') or voz.get('nome') or ''}"


def anotar(voz, caracteres, segundos) -> None:
    if caracteres <= 0 or segundos <= 0:
        return
    with _trava:
        dados = _ler()
        lista = (dados.get(chave(voz)) or [])[-(GUARDADAS - 1):]
        lista.append({"por_mil": round(segundos * 1000 / caracteres, 2), "caracteres": int(caracteres),
                      "quando": time.strftime("%Y-%m-%dT%H:%M:%S")})
        dados[chave(voz)] = lista
        try:
            _arquivo().write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass


def previsto(voz, caracteres):
    """(segundos previstos, quantas medidas) ou (None, quantas) com menos de MINIMO_DE_MEDIDAS."""
    lista = _ler().get(chave(voz)) or []
    if len(lista) < MINIMO_DE_MEDIDAS:
        return None, len(lista)
    return statistics.median(m["por_mil"] for m in lista) * caracteres / 1000, len(lista)


def _minutos(segundos) -> str:
    return f"{segundos / 60:.0f} min" if segundos >= 90 else f"{segundos:.0f} s"


class vigiar:
    """Diz a previsão no começo e avisa uma vez quando a narração passa de 1,5 vez o normal (e pelo menos 2 min a
    mais). anotar() guarda a medida desta narração; parar() desliga o aviso."""

    def __init__(self, voz, caracteres, log=print):
        self.voz, self.caracteres, self.log = voz, int(caracteres or 0), log
        self.inicio = time.time()
        self.timer = None
        if self.caracteres <= 0:
            return
        segundos, medidas = previsto(voz, self.caracteres)
        if segundos is None:
            log(f"  narração: ainda sem medida desta voz para prever o tempo ({medidas} de {MINIMO_DE_MEDIDAS})")
            return
        log(f"  narração: costuma levar uns {_minutos(segundos)} para {self.caracteres:,} caracteres "
            f"(pelas {medidas} últimas narrações desta voz)".replace(",", "."))
        limite = max(segundos * 1.5, segundos + 120)
        self.timer = threading.Timer(limite, self._passou, args=(segundos,))
        self.timer.daemon = True
        self.timer.start()

    def _passou(self, segundos):
        self.log(f"  ⚠ narração passou do normal: {_minutos(time.time() - self.inicio)} até agora, costuma levar "
                 f"{_minutos(segundos)}. A fila do provedor pode estar lenta; a fábrica segue esperando.")

    def anotar(self):
        anotar(self.voz, self.caracteres, time.time() - self.inicio)

    def parar(self):
        if self.timer:
            self.timer.cancel()
