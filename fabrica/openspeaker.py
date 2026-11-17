"""Narração pelo OpenSpeaker (ai33.pro), que revende as vozes da ElevenLabs, da Minimax e de outros por créditos.

É o mesmo desenho da GenAIPro: a fábrica cria uma tarefa, espera ela ficar pronta e baixa o mp3. Duas diferenças
que importam:

- a tarefa devolve credit_cost, quanto ela cobrou de verdade. Não é preciso medir o saldo antes e depois como na
  GenAIPro: cada bloco entra no custos_reais.json com o número que a própria API deu;
- o voice_id leva o prefixo do provedor (elevenlabs_, minimax_, clone_, edge_, kokoro_, vbee_, fishaudio_). O
  perfil do canal pode continuar guardando o id cru da ElevenLabs: voz_prefixada() põe o elevenlabs_ na frente.

O tempo de cada palavra vem do with_transcript=true: a tarefa devolve um json com as palavras (preferido) e um
srt. Não há pedido de legenda com um caractere por linha como na GenAIPro, então quando só vier o srt o tempo
dentro de um bloco é repartido pelo tamanho das palavras (genaipro.ler_srt já faz isso).

Preço medido em 17/11/2026 no contador do próprio site: 112 créditos para 100 caracteres e 224 para 200, com voz
da ElevenLabs. Ou seja 1,12 crédito por caractere, contra ~0,99 da GenAIPro; o crédito, porém, custa de 4 a 7
vezes menos (US$ 5,00 a US$ 2,94 por milhão, contra US$ 22,00).

A API não deixa escolher o modelo da ElevenLabs (não existe model_id em /v3/text-to-speech): quem manda é a voz.
"""
import json
import os
import re
import statistics
import threading
import time

import httpx

from . import genaipro
from .config import config_geral

URL_PADRAO = "https://api.ai33.pro"
NOMES_DA_CHAVE = ("OPENSPEAKER_API", "OPENSPEAKER_API_KEY", "AI33_API")
PREFIXOS = ("elevenlabs_", "minimax_", "clone_", "edge_", "kokoro_", "vbee_", "fishaudio_")
PREFIXO_PADRAO = "elevenlabs_"
PROVEDORES_DE_VOZ = ("elevenlabs", "minimax", "clone", "edge", "kokoro", "vbee", "fishaudio")
CREDITOS_POR_CARACTERE = 1.29  # medido na própria API em 17/11/2026 (voz da ElevenLabs):
# a fala custa 1,12 por caractere (330 caracteres = 369 créditos sem transcrição) e a transcrição pedida
# em with_transcript cobra à parte, uns 2,3 créditos por segundo de áudio (os mesmos 330 = 424 com ela).
# 1,29 é o efetivo de um bloco de roteiro, que é como a fábrica sempre narra. Textos curtos saem mais baratos.
VELOCIDADE_MIN, VELOCIDADE_MAX = 0.5, 1.5
ESPERA_MAXIMA = 20 * 60
# Diferente da GenAIPro, aqui a tarefa que demora NÃO ganha uma cópia: a cópia custaria créditos de novo e a fila
# do OpenSpeaker ainda não foi medida. Se a espera estourar, rodar de novo retoma a mesma tarefa, já paga.
ARQUIVO_VELOCIDADE = "openspeaker_vozes.json"
LENTA_A_PARTIR = 5 * 60  # espera típica por tarefa a partir da qual a voz ganha o aviso
IDIOMAS = genaipro.IDIOMAS  # a biblioteca é a mesma da ElevenLabs
_trava_velocidade = threading.Lock()


class ErroOpenSpeaker(SystemExit):
    """Erro com mensagem em português, que o editor e o terminal mostram como está."""


def chave() -> str:
    for nome in NOMES_DA_CHAVE:
        valor = os.environ.get(nome, "").strip().strip('"').strip("'")
        if valor:
            return valor
    raise ErroOpenSpeaker("Falta a chave do OpenSpeaker. Cole em OPENSPEAKER_API no arquivo .env.")


def tem_chave() -> bool:
    return any(os.environ.get(nome, "").strip() for nome in NOMES_DA_CHAVE)


def _url() -> str:
    return ((config_geral().get("openspeaker") or {}).get("url") or URL_PADRAO).rstrip("/")


def _cabecalho() -> dict:
    return {"xi-api-key": chave(), "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (fabrica-de-videos)"}


def _pedir(metodo, caminho, tentativas=4, **kw):
    """Chama a API e repete sozinho quando a falha é passageira (rede, 429 ou 5xx)."""
    erro, espera = "", kw.pop("timeout", 60)
    for tentativa in range(tentativas):
        try:
            r = httpx.request(metodo, _url() + caminho, headers=_cabecalho(), timeout=espera, **kw)
        except httpx.TransportError as e:
            erro = str(e)
        else:
            if r.status_code < 400:
                return r
            if r.status_code in (401, 403):
                raise ErroOpenSpeaker(f"O OpenSpeaker recusou a chave ({r.status_code}). "
                                      "Confira OPENSPEAKER_API no .env.")
            if r.status_code not in (429, 500, 502, 503, 504):
                raise ErroOpenSpeaker(f"O OpenSpeaker recusou o pedido ({r.status_code}). {_motivo(r)}")
            erro = r.text
        time.sleep(4 * (tentativa + 1))
    raise ErroOpenSpeaker(f"O OpenSpeaker falhou depois de {tentativas} tentativas. {erro[:300]}")


def _motivo(r) -> str:
    try:
        corpo = r.json()
    except ValueError:
        return r.text[:300]
    motivo = corpo.get("error") or corpo.get("message") or corpo.get("error_message") or r.text[:300]
    traducoes = {
        "invalid_voice_id": "Essa voz não existe no OpenSpeaker. Rode uv run fabrica vozes TERMO para escolher uma.",
        "insufficient_credits": "Os créditos do OpenSpeaker acabaram. Compre mais em ai33.pro/app/buy-credits.",
    }
    return traducoes.get(str(motivo), str(motivo))


# ---------------------------------------------------------------- conta

def conta() -> dict:
    """Créditos da conta. Não gasta nada."""
    dados = _pedir("GET", "/v1/credits").json() or {}
    creditos = int(dados.get("credits") or 0)
    return {"usuario": "", "creditos": creditos, "pacotes": [{"creditos": creditos, "vence": None}]}


def saude() -> dict:
    """Como está cada provedor de voz agora ("good", "degraded", "overloaded"). Não gasta nada."""
    return (_pedir("GET", "/v1/health-check").json() or {}).get("data") or {}


def vozes(busca=None, idioma=None, genero=None, uso=None, quantidade=30, pagina=0, provedor="elevenlabs") -> list:
    """Vozes da biblioteca, já no formato que a fábrica usa. Não gasta nada.

    A API conta as páginas a partir de 1; a fábrica, como na GenAIPro, a partir de 0."""
    if provedor not in PROVEDORES_DE_VOZ:
        provedor = "elevenlabs"
    parametros = {"provider": provedor, "page": int(pagina) + 1, "page_size": min(int(quantidade), 100)}
    for nome, valor in (("search", busca), ("language", idioma), ("gender", genero)):
        if valor:
            parametros[nome] = valor
    if uso:
        parametros["use_case"] = uso
    dados = _pedir("GET", "/v3/voices", params=parametros).json() or {}
    return [_voz(v) for v in (dados.get("data") or [])]


def _voz(v: dict) -> dict:
    etiquetas = [str(t) for t in (v.get("tags") or [])]
    genero = {"male": "masculina", "female": "feminina", "neutral": "neutra"}.get(
        str(v.get("gender") or "").lower(), str(v.get("gender") or ""))
    return {
        "voice_id": v.get("voice_id"),  # já vem prefixado pela API
        "nome": (v.get("name") or "").strip(),
        "genero": genero,
        "idade": v.get("age") or "",
        "sotaque": v.get("accent") or "",
        "idioma": v.get("language") or "",
        "uso": v.get("use_case") or "",
        "descricao": (v.get("description") or "").strip() or ", ".join(etiquetas),
        "previa": v.get("preview_url") or "",
        "usos_no_ano": 0,  # o OpenSpeaker não informa
    }


# ---------------------------------------------------------------- velocidade de cada voz

def _arquivo_velocidade():
    from .config import RAIZ
    return RAIZ / ARQUIVO_VELOCIDADE


def _velocidades() -> dict:
    try:
        dados = json.loads(_arquivo_velocidade().read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def anotar_espera(voice_id: str, segundos: float) -> None:
    """Guarda quanto a tarefa dessa voz ficou na fila do OpenSpeaker (as 10 últimas de cada voz)."""
    if not voice_id:
        return
    with _trava_velocidade:
        dados = _velocidades()
        v = dados.setdefault(voice_id, {"esperas": []})
        v["esperas"] = (v.get("esperas") or [])[-9:] + [round(segundos)]
        v["quando"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            _arquivo_velocidade().write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass  # a medida é só para o aviso: nunca para a narração


def lentidao(voice_id: str) -> dict:
    """{"lenta": True, "minutos": N, "aviso": "..."} quando a voz costuma passar de 5 minutos por tarefa; {} se não."""
    esperas = (_velocidades().get(voz_prefixada(voice_id) or "") or {}).get("esperas") or []
    if not esperas:
        return {}
    tipica = statistics.median(esperas)
    if tipica < LENTA_A_PARTIR:
        return {}
    minutos = round(tipica / 60)
    return {"lenta": True, "minutos": minutos,
            "aviso": f"Voz lenta no OpenSpeaker: cada bloco tem levado uns {minutos} min ou mais na fila. "
                     "O vídeo pode levar horas só na narração."}


# ---------------------------------------------------------------- narração

def voz_prefixada(voice_id) -> str:
    """O id da voz com o prefixo do provedor, que é o que a API v3 aceita.

    Os perfis dos canais guardam o id cru da ElevenLabs desde a GenAIPro: ele ganha elevenlabs_ na frente."""
    voice_id = str(voice_id or "").strip()
    if not voice_id or voice_id.startswith(PREFIXOS):
        return voice_id
    return PREFIXO_PADRAO + voice_id


def corpo_da_tarefa(texto: str, voz: dict) -> dict:
    voice_id = voz_prefixada(voz.get("voice_id"))
    if not voice_id or "COLE" in voice_id:
        raise ErroOpenSpeaker("Defina voz.voice_id no perfil do canal. "
                              "Rode uv run fabrica vozes TERMO para escolher uma.")
    velocidade = float(voz.get("velocidade") or 1.0)
    return {
        "text": texto,
        "voice_id": voice_id,
        "speed": round(min(max(velocidade, VELOCIDADE_MIN), VELOCIDADE_MAX), 2),
        "with_transcript": "true",
    }


def _campos(corpo: dict) -> dict:
    """O corpo como multipart/form-data, que é o que a API v3 espera (curl -F)."""
    return {nome: (None, str(valor)) for nome, valor in corpo.items()}


def narrar(texto: str, voz: dict, mp3, log=print) -> tuple:
    """Grava o texto em mp3 e devolve ([(palavra, início, fim)], créditos cobrados).

    A tarefa fica anotada em <mp3>.tarefa.json antes da espera: rodar de novo com o mesmo texto e a
    mesma voz retoma a tarefa já paga em vez de criar outra."""
    corpo = corpo_da_tarefa(texto, voz)
    anotacao = mp3.with_name(mp3.name + ".tarefa.json")
    tarefa_id, ja_paga = None, False
    if anotacao.exists():
        try:
            anterior = json.loads(anotacao.read_text(encoding="utf-8"))
            if anterior.get("corpo") == corpo:
                tarefa_id, ja_paga = anterior.get("id"), True
        except (OSError, ValueError):
            pass
    if tarefa_id:
        log("    retomando a tarefa já paga no OpenSpeaker")
    else:
        resposta = _pedir("POST", "/v3/text-to-speech", files=_campos(corpo), timeout=120).json()
        tarefa_id = resposta.get("task_id")
        if not tarefa_id:
            raise ErroOpenSpeaker(f"O OpenSpeaker não devolveu o número da tarefa. {str(resposta)[:300]}")
        anotacao.write_text(json.dumps({"id": tarefa_id, "corpo": corpo}, ensure_ascii=False), encoding="utf-8")

    inicio = time.time()
    try:
        tarefa = _esperar(tarefa_id)
    finally:
        anotar_espera(corpo["voice_id"], time.time() - inicio)
    dados = tarefa.get("metadata") or {}
    audio = dados.get("audio_url") or tarefa.get("output_uri")
    if not audio:
        raise ErroOpenSpeaker(f"O OpenSpeaker terminou a tarefa {tarefa_id} sem áudio. Rode de novo.")
    r = httpx.get(audio, timeout=300, follow_redirects=True)
    r.raise_for_status()
    mp3.write_bytes(r.content)
    palavras = palavras_da_tarefa(tarefa)
    # a tarefa retomada já foi cobrada antes: não entra de novo na conta do vídeo
    creditos = 0.0 if ja_paga else float(tarefa.get("credit_cost") or 0)
    anotacao.unlink(missing_ok=True)
    return palavras, creditos


def _esperar(tarefa_id, limite=ESPERA_MAXIMA) -> dict:
    """A tarefa pronta. Erro quando o OpenSpeaker falhou ou passou do limite."""
    inicio, pausa = time.time(), 1.5
    while True:
        tarefa = _pedir("GET", f"/v1/task/{tarefa_id}").json() or {}
        estado = str(tarefa.get("status", "")).lower()
        if estado in ("done", "completed", "success"):
            return tarefa
        if estado in ("error", "failed", "cancelled"):
            raise ErroOpenSpeaker(f"O OpenSpeaker não conseguiu gravar o áudio (tarefa {tarefa_id}). "
                                  f"{tarefa.get('error_message') or 'Tente de novo.'}")
        if time.time() - inicio > limite:
            raise ErroOpenSpeaker(f"O OpenSpeaker não terminou em {limite // 60} minutos. Rode de novo: a mesma "
                                  "tarefa é retomada, sem pagar outra vez.")
        time.sleep(pausa)
        pausa = min(pausa * 1.3, 8.0)


def palavras_da_tarefa(tarefa: dict) -> list:
    """[(palavra, início, fim)] da transcrição da tarefa: o json quando existe, senão o srt."""
    dados = tarefa.get("metadata") or {}
    if dados.get("json_url"):
        try:
            r = httpx.get(dados["json_url"], timeout=120, follow_redirects=True)
            r.raise_for_status()
            palavras = ler_json_de_palavras(r.json())
            if palavras:
                return palavras
        except (httpx.HTTPError, ValueError):
            pass  # cai para o srt, que sempre vem junto
    if not dados.get("srt_url"):
        return []
    r = httpx.get(dados["srt_url"], timeout=120, follow_redirects=True)
    r.raise_for_status()
    return genaipro.ler_srt(r.content.decode("utf-8", errors="replace"))


def ler_json_de_palavras(dados) -> list:
    """[(palavra, início, fim)] de um json de transcrição, em qualquer das formas que a API costuma usar.

    Aceita uma lista solta, {"words": [...]}, {"segments": [{"words": [...]}]} e os nomes de campo mais comuns
    (word/text/char, start/start_time/from, end/end_time/to). Em segundos; milissegundos viram segundos."""
    lista = dados
    if isinstance(dados, dict):
        lista = dados.get("words") or dados.get("alignment") or dados.get("chars")
        if lista is None and isinstance(dados.get("segments"), list):
            lista = [p for s in dados["segments"] for p in (s.get("words") or [])]
    if not isinstance(lista, list):
        return []
    palavras = []
    for item in lista:
        if not isinstance(item, dict):
            continue
        texto = item.get("word", item.get("text", item.get("char", "")))
        texto = str(texto or "").strip()
        inicio = item.get("start", item.get("start_time", item.get("from")))
        fim = item.get("end", item.get("end_time", item.get("to")))
        if not texto or inicio is None or fim is None:
            continue
        try:
            inicio, fim = float(inicio), float(fim)
        except (TypeError, ValueError):
            continue
        if fim > 10000:  # veio em milissegundos
            inicio, fim = inicio / 1000, fim / 1000
        palavras.append((texto, inicio, fim))
    return palavras


ler_srt = genaipro.ler_srt  # a leitura de SRT é a mesma; fica aqui para quem importar só este módulo
