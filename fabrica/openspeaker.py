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
ESPERA_DA_TRANSCRICAO = 5 * 60  # com o áudio pronto, o tempo que ainda se espera pela transcrição
# Quando a fila de transcrição do OpenSpeaker pendura (2026-11-18), a tarefa fica "doing" para sempre e ocupa uma
# das 20 vagas da conta: em pouco tempo a conta inteira para com queue_limit_exceeded e nenhum vídeo narra. Depois
# da primeira tarefa que volta sem transcrição, os blocos seguintes são pedidos sem ela: a tarefa fica pronta assim
# que o áudio sai, libera a vaga e o tempo das palavras é estimado pelas pausas (narracao._palavras_estimadas).
_transcricao_pendurada = False
# 2026-11-19: a fila de transcrição pendurou de novo e, com a fábrica reiniciada, o aviso acima se perdia (estava
# só na memória do processo): a conta voltava a pedir transcrição, as 20 vagas enchiam em minutos e nenhum vídeo
# narrava. Agora o aviso fica em disco por HORAS_SEM_TRANSCRICAO e vale depois do reinício; passado esse prazo a
# fábrica tenta a transcrição de novo, porque o problema é do lado deles e costuma passar.
ARQUIVO_TRANSCRICAO = "openspeaker_transcricao.json"
HORAS_SEM_TRANSCRICAO = 6
VAGAS_DA_CONTA = 20              # tarefas ao mesmo tempo que a conta aceita (queue_limit_exceeded)
ESPERA_POR_VAGA = 2 * 60         # com as vagas cheias, o tempo que se espera por uma antes de desistir da tentativa
# Lembrar que as vagas estavam cheias: a listagem de tarefas (/v1/tasks) devolve 503 "Task polling temporarily busy"
# de vez em quando, e sem esta memória conta_travada() lia o 503, respondia "não sei" e o vídeo voltava a esperar
# vaga por horas em vez de ir para a reserva (2026-11-19).
MEMORIA_DA_FILA_CHEIA = 10 * 60
_vagas_cheias_em = 0.0
IDADE_PARA_SOLTAR = 10 * 60      # só uma tarefa presa há mais que isso é cancelada para soltar a vaga
IDIOMAS = genaipro.IDIOMAS  # a biblioteca é a mesma da ElevenLabs
_trava_velocidade = threading.Lock()
_minhas: set = set()        # tarefas que este processo está esperando: nunca são canceladas para soltar vaga
_trava_minhas = threading.Lock()


class ErroOpenSpeaker(SystemExit):
    """Erro com mensagem em português, que o editor e o terminal mostram como está."""


class FilaCheia(ErroOpenSpeaker):
    """As vagas de tarefa da conta estão todas ocupadas (queue_limit_exceeded)."""


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
            if "queue_limit_exceeded" in (r.text or ""):
                # não é falha passageira de rede: insistir em segundos só gasta tempo. Quem chamou resolve
                # (aproveita uma tarefa igual da fila, solta as vagas presas e espera uma vaga)
                raise FilaCheia(f"As {VAGAS_DA_CONTA} vagas de tarefa da conta do OpenSpeaker estão ocupadas. "
                                f"{_motivo(r)}")
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


# ---------------------------------------------------------------- as vagas da conta

def tarefas() -> list:
    """As tarefas da conta agora, as presas na fila inclusive. Não gasta nada."""
    dados = (_pedir("GET", "/v1/tasks", tentativas=4).json() or {}).get("data")
    return dados if isinstance(dados, list) else []


def _audio_pronto(tarefa: dict) -> str:
    return (tarefa.get("metadata") or {}).get("audio_url") or tarefa.get("output_uri") or ""


def _presa_na_transcricao(tarefa: dict) -> bool:
    """A tarefa cujo áudio já saiu e que só espera a transcrição: ela nunca termina e ocupa uma vaga."""
    if str(tarefa.get("status", "")).lower() not in ("doing", "processing", "pending", "queued"):
        return False
    if not _audio_pronto(tarefa):
        return False
    estado = str((tarefa.get("metadata") or {}).get("transcript_status") or "").lower()
    return estado in ("processing", "pending", "doing", "queued", "")


def _idade(tarefa: dict) -> float:
    """Segundos desde que a tarefa foi criada (um valor alto quando a data não vem, para não impedir o cancelamento)."""
    quando = str(tarefa.get("created_at") or "").replace("Z", "+00:00")
    try:
        from datetime import datetime, timezone
        return (datetime.now(timezone.utc) - datetime.fromisoformat(quando)).total_seconds()
    except ValueError:
        return float("inf")


def cancelar(tarefa_id) -> bool:
    """Tira a tarefa da fila para soltar a vaga. False quando a API não deixa cancelar (nada é perdido por isso).

    A tarefa cancelada já foi cobrada na criação e o áudio dela já foi baixado antes, quando havia áudio.

    Medido em 2026-11-19: a API do OpenSpeaker NÃO tem como cancelar. DELETE /v1/task/{id}, POST /v1/task/{id}/cancel,
    DELETE /v3/task/{id}, /v1/task/{id}/stop, /v1/tasks/cancel e PATCH /v1/task/{id} devolvem todos 404. A tentativa
    fica aqui porque custa um pedido e resolveria na hora se eles abrirem a rota; enquanto não abrirem, a única saída
    é não pendurar tarefa (pedir_transcricao) e esperar a fila deles andar."""
    if not tarefa_id:
        return False
    for metodo, caminho in (("DELETE", f"/v1/task/{tarefa_id}"), ("POST", f"/v1/task/{tarefa_id}/cancel"),
                            ("DELETE", f"/v3/task/{tarefa_id}")):
        try:
            r = httpx.request(metodo, _url() + caminho, headers=_cabecalho(), timeout=30)
        except httpx.HTTPError:
            continue
        if r.status_code < 400:
            return True
    return False


def liberar_vagas(log=print) -> int:
    """Cancela as tarefas presas na transcrição para a conta voltar a aceitar narração. Devolve quantas soltou.

    Só mexe no que está parado há mais de IDADE_PARA_SOLTAR e no que nenhuma narração deste processo está
    esperando: o áudio dessas tarefas não interessa a ninguém, e a vaga interessa a todos os vídeos."""
    try:
        fila = tarefas()
    except (ErroOpenSpeaker, httpx.HTTPError):
        return 0
    with _trava_minhas:
        minhas = set(_minhas)
    presas = [t for t in fila if _presa_na_transcricao(t) and t.get("id") not in minhas
              and _idade(t) > IDADE_PARA_SOLTAR]
    if presas:
        marcar_transcricao_pendurada()
        log(f"    {len(presas)} tarefa(s) do OpenSpeaker estão presas na transcrição e ocupando vaga: soltando")
    soltas = sum(1 for t in presas if cancelar(t.get("id")))
    if presas and not soltas:
        log("    o OpenSpeaker não deixou cancelar nenhuma: esperando as vagas abrirem sozinhas")
    elif soltas:
        log(f"    {soltas} vaga(s) liberada(s) no OpenSpeaker")
    return soltas


def conta_travada(log=print) -> bool:
    """True quando as vagas de tarefa da conta estão todas ocupadas e não há como soltar nenhuma agora.

    É o que manda a narração do vídeo inteiro para a reserva (narracao.narrar): com a conta travada, insistir no
    OpenSpeaker deixa o vídeo parado por horas. Não gasta crédito: só lê a fila e tenta cancelar as presas."""
    if time.time() - _vagas_cheias_em < MEMORIA_DA_FILA_CHEIA:
        return True  # a própria API já recusou por queue_limit_exceeded agora há pouco
    try:
        fila = tarefas()
    except (ErroOpenSpeaker, httpx.HTTPError):
        return False  # sem saber, segue no OpenSpeaker: a falha de leitura não pode trocar a voz do canal
    def ocupadas(lista):
        return [t for t in lista if str(t.get("status", "")).lower() in ("doing", "processing", "pending", "queued")]
    if len(ocupadas(fila)) < VAGAS_DA_CONTA:
        return False
    if liberar_vagas(log):
        try:
            return len(ocupadas(tarefas())) >= VAGAS_DA_CONTA
        except (ErroOpenSpeaker, httpx.HTTPError):
            return False
    return True


def tarefa_igual(corpo: dict) -> dict:
    """Uma tarefa da fila com o mesmo texto e a mesma voz, com o áudio já pronto: ela já foi paga, então é
    aproveitada em vez de criar outra (é o que salva o bloco quando as vagas estão cheias)."""
    try:
        fila = tarefas()
    except (ErroOpenSpeaker, httpx.HTTPError):
        return {}
    for t in fila:
        mesma_voz = str((t.get("metadata") or {}).get("v3", {}).get("raw_voice_id") or "") == corpo["voice_id"]
        if t.get("text") == corpo["text"] and mesma_voz and _audio_pronto(t):
            return t
    return {}


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
        "with_transcript": "true" if pedir_transcricao() else "false",
    }


def pedir_transcricao() -> bool:
    """Se a tarefa deve pedir a transcrição, que é o que mede o tempo de cada palavra.

    Desligada por openspeaker.transcricao: false no config.yaml, e sozinha quando a fila de transcrição pendura
    (o aviso vale por HORAS_SEM_TRANSCRICAO, mesmo depois de a fábrica reiniciar)."""
    if _transcricao_pendurada or _pendurada_em_disco():
        return False
    return (config_geral().get("openspeaker") or {}).get("transcricao", True) is not False


def _arquivo_transcricao():
    from .config import RAIZ
    return RAIZ / ARQUIVO_TRANSCRICAO


def _pendurada_em_disco() -> bool:
    try:
        quando = float(json.loads(_arquivo_transcricao().read_text(encoding="utf-8")).get("epoch") or 0)
    except (OSError, ValueError, AttributeError):
        return False
    return time.time() - quando < HORAS_SEM_TRANSCRICAO * 3600


def marcar_transcricao_pendurada() -> None:
    """Guarda que a fila de transcrição do OpenSpeaker está pendurada, em memória e em disco."""
    global _transcricao_pendurada
    _transcricao_pendurada = True
    try:
        _arquivo_transcricao().write_text(
            json.dumps({"epoch": time.time(), "quando": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "horas": HORAS_SEM_TRANSCRICAO}, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass  # o aviso em memória já vale para este processo


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
        tarefa_id, ja_paga = _criar(corpo, log)
        anotacao.write_text(json.dumps({"id": tarefa_id, "corpo": corpo}, ensure_ascii=False), encoding="utf-8")

    inicio = time.time()
    with _trava_minhas:
        _minhas.add(tarefa_id)
    try:
        tarefa = _esperar(tarefa_id, log=log)
    finally:
        anotar_espera(corpo["voice_id"], time.time() - inicio)
        with _trava_minhas:
            _minhas.discard(tarefa_id)
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
    # o áudio está aqui, mas a tarefa continua "doing" esperando a transcrição que não vem: cancelar solta a vaga
    # da conta, que é o que faltava para os outros blocos e os outros vídeos narrarem (2026-11-19)
    if str(tarefa.get("status", "")).lower() not in ("done", "completed", "success"):
        if cancelar(tarefa_id):
            log("    vaga do OpenSpeaker liberada: o áudio já está aqui e a tarefa saiu da fila")
    return palavras, creditos


def _criar(corpo: dict, log=print) -> tuple:
    """Cria a tarefa e devolve (id, já_paga).

    Com as vagas da conta cheias (queue_limit_exceeded), antes de desistir: aproveita uma tarefa igual que já
    esteja na fila com o áudio pronto (ela já foi paga), solta as vagas presas na transcrição e espera uma vaga
    até ESPERA_POR_VAGA. Antes, as 20 vagas presas faziam a criação errar em 40 segundos e tentar de novo para
    sempre, sem narrar um bloco (pedidos 176 e 177 em 2026-11-19)."""
    limite = time.time() + ESPERA_POR_VAGA
    while True:
        try:
            resposta = _pedir("POST", "/v3/text-to-speech", files=_campos(corpo), timeout=120).json()
        except FilaCheia:
            igual = tarefa_igual(corpo)
            if igual.get("id"):
                log("    as vagas do OpenSpeaker estão cheias: aproveitando a tarefa igual que já está na fila, "
                    "com o áudio pronto e já paga")
                return igual["id"], True
            if not liberar_vagas(log):
                global _vagas_cheias_em
                _vagas_cheias_em = time.time()   # para o próximo vídeo já ir para a reserva (conta_travada)
            if time.time() > limite:
                raise
            log("    esperando uma vaga no OpenSpeaker (30s)")
            time.sleep(30)
            continue
        tarefa_id = resposta.get("task_id")
        if not tarefa_id:
            raise ErroOpenSpeaker(f"O OpenSpeaker não devolveu o número da tarefa. {str(resposta)[:300]}")
        return tarefa_id, False


def _esperar(tarefa_id, limite=ESPERA_MAXIMA, log=print) -> dict:
    """A tarefa pronta. Erro quando o OpenSpeaker falhou ou passou do limite.

    A tarefa fica "doing" até o áudio E a transcrição ficarem prontos. Quando o áudio já está lá e só a
    transcrição demora, a espera acaba em ESPERA_DA_TRANSCRICAO e a tarefa volta sem transcrição: a narração
    segue com o tempo das palavras estimado pelas pausas do áudio (narracao._palavras_estimadas), que é o mesmo
    caminho da Fish. Isso evita o que aconteceu em 2026-11-18: a fila de transcrição do OpenSpeaker parou, o
    áudio de cada bloco ficava pronto em segundos e a criação esperava os 20 minutos do limite para errar e
    tentar de novo, sem nunca entregar um bloco."""
    inicio, pausa = time.time(), 1.5
    while True:
        tarefa = _pedir("GET", f"/v1/task/{tarefa_id}").json() or {}
        estado = str(tarefa.get("status", "")).lower()
        if estado in ("done", "completed", "success"):
            return tarefa
        if estado in ("error", "failed", "cancelled"):
            raise ErroOpenSpeaker(f"O OpenSpeaker não conseguiu gravar o áudio (tarefa {tarefa_id}). "
                                  f"{tarefa.get('error_message') or 'Tente de novo.'}")
        if _audio_pronto(tarefa) and time.time() - inicio > ESPERA_DA_TRANSCRICAO:
            log(f"    o áudio da tarefa {tarefa_id} está pronto, mas a transcrição não saiu em "
                f"{ESPERA_DA_TRANSCRICAO // 60} minutos: seguindo sem ela")
            if not _transcricao_pendurada:
                log(f"    os próximos blocos vão ser pedidos sem transcrição pelas próximas "
                    f"{HORAS_SEM_TRANSCRICAO} horas, para a tarefa não ficar presa na fila do OpenSpeaker "
                    f"(são {VAGAS_DA_CONTA} vagas na conta, e tarefa pendurada não libera a vaga)")
            marcar_transcricao_pendurada()
            return tarefa
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
