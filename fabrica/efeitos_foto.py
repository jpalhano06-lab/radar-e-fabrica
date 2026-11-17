"""Efeitos de câmera nas fotos do vídeo: o que sai de um vídeo editado à mão, feito no próprio computador e de graça.

Pedido do usuário em 2026-11-17, de um vídeo de "16 efeitos que o Claude cria" (um pacote vendido para quem grava o
próprio rosto). Dos efeitos de lá, ficaram os que servem a um documentário narrado com fotos e vídeos de banco:

- revelar ("recuo que revela"): a câmera começa num detalhe da foto (o assunto, o rosto) e recua até a foto inteira.
- profundidade ("camadas em profundidade"): o assunto recortado anda na frente e o fundo atrás, mais devagar.
- moldura ("quebra de moldura"): a foto num quadro com borda branca, e o assunto cresce para fora dele.
- rabisco ("rabisco tremido"): um contorno à mão, tremendo, desenha-se em volta do assunto.
- celular ("mockup de celular"): a foto na tela de um celular, quando a fala cita app, site ou rede social.
- atravessar ("zoom que atravessa"): na troca de assunto (bloco), a câmera mergulha no fim de uma foto e sai do
  começo da seguinte.

Ficaram de fora a tela verde (a fábrica bloqueia material de chroma), o zoom digital com "REC", a vertigem, o mundo de
interface e a órbita: são de quem aparece falando, ou de propaganda de software.

Como entra: o render (render._tarefas_da_linha) pede a escolha (escolher) e, para a cena escolhida, o clipe sai daqui
(renderizar), quadro a quadro em numpy e OpenCV, e segue para o mesmo caminho dos outros clipes (título, símbolo,
visual do canal). Poucos e espaçados: um a cada `intervalo` segundos de foto, nunca o mesmo duas vezes seguidas. O
recorte do assunto é o GrabCut do OpenCV (como em recorte.py), conferido pelas contas de acabamento (recorte.limpo);
sem recorte bom, a cena fica com um efeito que não precisa dele. Só na tela deitada. Nunca para o vídeo: falhou, a
cena sai com o movimento lento de sempre.
"""
import hashlib
import json
import math
import random
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np

VERSAO = 3  # suba quando mudar o desenho: os clipes com efeito renderizam de novo (os outros não mudam de nome)
EFEITOS = ("revelar", "profundidade", "moldura", "rabisco", "celular")
COM_RECORTE = ("profundidade", "moldura", "rabisco")
ORDEM = ("profundidade", "rabisco", "revelar", "moldura", "celular")  # a preferência, quando todos cabem
DURACAO_MINIMA = 2.5   # segundos: menos que isso o efeito não dá tempo de acontecer
ATRAVESSAR = 0.4       # segundos do mergulho no fim de uma foto e da saída no começo da seguinte
AMARELO = (63, 210, 255)  # BGR do #FFD23F, a cor de destaque do impacto
_FALA_DE_TELA = re.compile(r"\b(app|apps|aplicativos?|sites?|website|instagram|tiktok|youtube|whatsapp|facebook|"
                           r"twitter|rede social|redes sociais|internet|online|celular|smartphone|iphone|android|"
                           r"google|post|postou|postagem|v[ií]deo viral|viralizou)\b", re.I)
_FOTO_DE_TELA = re.compile(r"\b(celular|smartphone|telefone|phone|tela|screen|monitor|computador|notebook|laptop|"
                           r"tablet|interface|aplicativo|captura)\b", re.I)


def config(projeto) -> dict:
    padrao = {"ativo": True, "intervalo": 15, "intervalo_revelar": 30, "atravessar": True}
    return {**padrao, **(projeto.config.get("efeitos_foto") or {}), **((projeto.perfil.get("efeitos_foto") or {}))}


# ------------------------------------------------------------------------------------------------ a escolha

def _legenda(cena) -> str:
    return str((cena.get("conferencia") or {}).get("legenda") or "")


def pede_celular(cena) -> bool:
    """A fala cita app, site ou rede social, e a foto não é ela mesma um celular ou uma tela (celular dentro de
    celular)."""
    o_que_e = (re.search(r"O que é:\s*([^(\n]+)", _legenda(cena)) or [None, ""])[1]
    return bool(_FALA_DE_TELA.search(str(cena.get("texto") or ""))) and not _FOTO_DE_TELA.search(o_que_e)


def escolher(linha, pasta, cfg_render, cfg, preparar) -> dict:
    """{ordem do pedaço: {"efeito": nome, "entra": bool, "sai": bool}} para os pedaços que ganham efeito.

    linha: os pedaços do render (render._linha_do_tempo). preparar(arquivo) devolve a foto como ela entra na tela e
    se ela preenche a tela (render._foto_na_tela); o recorte só vale para foto que preenche. Sai sempre o mesmo para
    a mesma linha: o nome dos clipes depende disso."""
    if not cfg.get("ativo", True) or cfg_render.get("vertical"):
        return {}
    escolhidos, ultimo_t, ultimo_efeito, usados, ultimo_revelar = {}, -1e9, None, {}, -1e9
    fps = cfg_render.get("fps", 30)

    def foto(p):
        return p.get("tipo") == "cena" and p.get("origem") == "foto" and p["arquivo"].exists()

    intervalo = float(cfg.get("intervalo", 15))
    for p in linha:
        dur = p["fim"] - p["ini"]
        if not foto(p) or dur < DURACAO_MINIMA or p["ini"] - ultimo_t < intervalo:
            continue
        # só a cena inteira (um pedaço cortado pelo personagem não tem o assunto inteiro na tela)
        if abs(p["ini"] - float(p["cena"].get("ini", p["ini"]))) > 0.05:
            continue
        tela, preenche = preparar(p["arquivo"])
        # o recuo é o que cabe em quase toda foto: sem limite, ele era 46 dos 68 efeitos do everything-you-need-to-answer
        possiveis = ["revelar"] if p["ini"] - ultimo_revelar >= float(cfg.get("intervalo_revelar", 30)) else []
        if pede_celular(p["cena"]):
            possiveis.append("celular")
        if preenche and pode_ter_assunto(p["cena"], tela):
            m = mascara(tela, pasta)
            if m is not None and tem_assunto(p["cena"], tela, m):
                possiveis += list(COM_RECORTE)
        if not possiveis:
            continue
        livres = [e for e in possiveis if e != ultimo_efeito] or possiveis
        efeito = min(livres, key=lambda e: (usados.get(e, 0), ORDEM.index(e)))
        escolhidos[p["ordem"]] = {"efeito": efeito}
        usados[efeito] = usados.get(efeito, 0) + 1
        ultimo_t, ultimo_efeito = p["ini"], efeito
        if efeito == "revelar":
            ultimo_revelar = p["ini"]
    if cfg.get("atravessar", True):
        # o zoom que atravessa: na troca de bloco, entre duas fotos que não têm outro efeito
        for a, b in zip(linha, linha[1:]):
            if not (foto(a) and foto(b)):
                continue
            if a["ordem"] in escolhidos or b["ordem"] in escolhidos:
                continue
            bloco_a, bloco_b = a["cena"].get("bloco"), b["cena"].get("bloco")
            if bloco_a is None or bloco_a == bloco_b or round((a["fim"] - a["ini"]) * fps) < 2 * ATRAVESSAR * fps:
                continue
            if round((b["fim"] - b["ini"]) * fps) < 2 * ATRAVESSAR * fps:
                continue
            escolhidos.setdefault(a["ordem"], {"efeito": None})["sai"] = True
            escolhidos.setdefault(b["ordem"], {"efeito": None})["entra"] = True
    return escolhidos


def assinatura(escolha) -> str:
    """O pedaço do nome do clipe: vazio sem efeito, para os outros clipes não mudarem de nome."""
    if not escolha:
        return ""
    return f"|efeito:{escolha.get('efeito')}:{int(bool(escolha.get('entra')))}{int(bool(escolha.get('sai')))}:v{VERSAO}"


# ------------------------------------------------------------------------------------------------ o recorte

LADO = 420
FRACAO_MIN, FRACAO_MAX = 0.08, 0.55


def mascara(foto, pasta):
    """A máscara do assunto da foto (0 a 255, reduzida a LADO px), ou None se o recorte não convence. Guardada em
    pasta, pelo arquivo e pela data: cada foto é recortada uma vez."""
    foto = Path(foto)
    pasta = Path(pasta)
    chave = hashlib.sha1(f"{foto}|{foto.stat().st_mtime_ns}|{VERSAO}".encode()).hexdigest()[:12]
    arquivo, nota = pasta / f"{chave}_mascara.png", pasta / f"{chave}_mascara.json"
    if nota.exists():
        if not json.loads(nota.read_text(encoding="utf-8")).get("ok"):
            return None
        m = cv2.imread(str(arquivo), cv2.IMREAD_GRAYSCALE)
        if m is not None:
            return m
    pasta.mkdir(parents=True, exist_ok=True)
    achados = _rostos(foto)
    m, motivo = _recortar(foto, pasta, achados)
    if m is None and achados:
        # o corpo a partir do rosto não saiu (camisa escura no fundo escuro): o retângulo do meio da foto, e
        # tem_assunto confere se o rosto ficou dentro
        m, motivo = _recortar(foto, pasta)
    if m is not None:
        cv2.imwrite(str(arquivo), m)
    nota.write_text(json.dumps({"ok": m is not None, "motivo": motivo}), encoding="utf-8")
    return m


def _recortar(foto, pasta, rostos_=None):
    """GrabCut na foto reduzida (LADO px): a máscara fica nesse tamanho e é ampliada na hora de desenhar. Com rostos
    (frações da foto), o retângulo de partida é o corpo de quem aparece: do alto da cabeça a uns quatro rostos abaixo."""
    from PIL import Image

    from . import recorte

    try:
        with Image.open(foto) as im:
            im.draft("RGB", (LADO, LADO))  # o JPEG já sai reduzido do disco: a foto de 6000 px levava segundos
            im = im.convert("RGB")
            im.thumbnail((LADO, LADO))
            pequena = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    except Exception:  # noqa: BLE001
        return None, "foto não abre"
    a, l_ = pequena.shape[:2]
    m = np.zeros((a, l_), np.uint8)
    rect = (int(l_ * 0.12), int(a * 0.08), int(l_ * 0.76), int(a * 0.88))
    if rostos_:
        x0 = min(x - w * 1.3 for x, y, w, h in rostos_)
        x1 = max(x + w * 2.3 for x, y, w, h in rostos_)
        y0 = min(y - h * 0.5 for x, y, w, h in rostos_)
        y1 = max(y + h * 5.0 for x, y, w, h in rostos_)
        x0, y0, x1, y1 = max(0.01, x0), max(0.01, y0), min(0.99, x1), min(0.99, y1)
        rect = (int(x0 * l_), int(y0 * a), max(8, int((x1 - x0) * l_)), max(8, int((y1 - y0) * a)))
    try:
        cv2.grabCut(pequena, m, rect, np.zeros((1, 65)), np.zeros((1, 65)), 3, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None, "grabcut falhou"
    assunto = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    nucleo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    assunto = cv2.morphologyEx(cv2.morphologyEx(assunto, cv2.MORPH_OPEN, nucleo), cv2.MORPH_CLOSE, nucleo, iterations=2)
    n, rotulos, estat, _ = cv2.connectedComponentsWithStats(assunto, 8)
    if n <= 1:
        return None, "nenhum assunto"
    areas = estat[1:, cv2.CC_STAT_AREA]
    k = int(np.argmax(areas)) + 1
    # com rosto, o maior pedaço basta (as faíscas e os reflexos em volta saem); sem rosto, o assunto tem de ser um só
    if areas.max() / areas.sum() < (0.65 if rostos_ else 0.85):
        return None, "assunto em pedaços"
    assunto = (rotulos == k).astype(np.uint8) * 255
    contornos, _ = cv2.findContours(assunto, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assunto = cv2.drawContours(np.zeros_like(assunto), contornos, -1, 255, cv2.FILLED)
    fracao = float((assunto > 0).mean())
    if not FRACAO_MIN <= fracao <= FRACAO_MAX:
        return None, f"assunto ocupa {fracao:.0%} da foto"
    beirada = np.concatenate([assunto[0], assunto[:, 0], assunto[:, -1]])  # embaixo pode encostar (o chão)
    if float((beirada > 0).mean()) > 0.15:
        return None, "assunto colado na borda"
    # as contas de acabamento do recorte da colagem: sem fundo grudado e sem pontas
    teste = Path(pasta) / f"_teste_{hashlib.sha1(str(foto).encode()).hexdigest()[:8]}.png"
    try:
        cv2.imwrite(str(teste), np.dstack([pequena, assunto]))
        if not recorte.limpo(teste):
            return None, "recorte sujo"
    finally:
        teste.unlink(missing_ok=True)
    return assunto, "ok"


MAX_ROSTOS = 2  # foto de grupo fica fora: o recorte pegava o céu da caverna junto com as pessoas (ouro-da-serra, 183)


ROSTO_MINIMO = 0.06  # da largura da foto: gente menor que isso (pessoas ao longe) não se recorta


def _rostos(foto) -> list:
    """Os rostos grandes o bastante para recortar quem aparece."""
    from . import rostos

    try:
        return [r for r in rostos.rostos(Path(foto)) if r[2] >= ROSTO_MINIMO]
    except Exception:  # noqa: BLE001
        return []


def pode_ter_assunto(cena, foto) -> bool:
    """Antes do recorte (uns segundos por foto): só cena de animal (o campo animal do agente) ou foto com rosto. Em
    cena aberta o GrabCut pega qualquer coisa (o céu de uma caverna, uma fileira de casas), e o contorno em volta
    disso parece engano."""
    return bool(cena.get("animal")) or 1 <= len(_rostos(foto)) <= MAX_ROSTOS


def tem_assunto(cena, foto, m) -> bool:
    """O recorte é do assunto da cena: cena de animal, ou foto com rosto e todo rosto dentro do recorte."""
    if cena.get("animal"):
        return True
    achados = _rostos(foto)
    if not 1 <= len(achados) <= MAX_ROSTOS:
        return False
    a, l_ = m.shape[:2]
    for x, y, w, h in achados:
        if m[min(a - 1, int((y + h / 2) * a)), min(l_ - 1, int((x + w / 2) * l_))] < 128:
            return False
    return True


# ------------------------------------------------------------------------------------------------ o desenho

def _suave(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def _sai(p):  # desacelera no fim
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def _tela(foto, W, H):
    """A foto preenchendo a tela, no dobro da resolução (o zoom não perde nitidez)."""
    imagem = cv2.imread(str(foto), cv2.IMREAD_COLOR)
    alto, largo = imagem.shape[:2]
    escala = max(2 * W / largo, 2 * H / alto)
    imagem = cv2.resize(imagem, (math.ceil(largo * escala), math.ceil(alto * escala)), interpolation=cv2.INTER_AREA
                        if escala < 1 else cv2.INTER_CUBIC)
    y0, x0 = (imagem.shape[0] - 2 * H) // 2, (imagem.shape[1] - 2 * W) // 2
    return imagem[y0:y0 + 2 * H, x0:x0 + 2 * W], (x0, y0, escala)


def _no_lugar(img, s, ax, ay, tx, ty, W, H, borda=cv2.BORDER_REFLECT):
    """img (no dobro da tela) escalada por s em volta do ponto (ax, ay) da tela e posta em (tx, ty) da tela."""
    M = np.float32([[s / 2, 0, tx - s * ax], [0, s / 2, ty - s * ay]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=borda)


def _misturar(base, cima, alfa):
    """cima sobre base com a transparência alfa (0 a 255). O blendLinear do OpenCV: em numpy cada mistura de uma
    tela inteira levava dezenas de milissegundos."""
    peso = alfa.astype(np.float32) * (1 / 255)
    return cv2.blendLinear(cima, base, peso, 1 - peso)


def _centro_do_assunto(m2):
    """O centro do assunto, na tela (a máscara está no dobro)."""
    ys, xs = np.nonzero(m2 > 128)
    return float(xs.mean()) / 2, float(ys.min() + (ys.max() - ys.min()) * 0.4) / 2


def _movimento_base(movimento, p, W, H, zoom=1.12):
    """O movimento lento de sempre (render._filtro_foto): (escala, ponto da tela que fica no centro)."""
    if movimento == "aproximar":
        return 1 + (zoom - 1) * p, W / 2, H / 2
    if movimento == "afastar":
        return zoom - (zoom - 1) * p, W / 2, H / 2
    folga = W / 2 - W / (2 * zoom)
    if movimento == "direita":
        return zoom, W / 2 - folga + 2 * folga * p, H / 2
    return zoom, W / 2 + folga - 2 * folga * p, H / 2


def renderizar(tarefa, foto, cfg_render, pasta, destino) -> Path:
    """Grava em destino o clipe da cena com o efeito (sem som). foto: a foto como ela entra na tela."""
    W, H = cfg_render.get("largura", 1920), cfg_render.get("altura", 1080)
    fps = cfg_render.get("fps", 30)
    frames = int(tarefa["frames"])
    escolha = tarefa.get("efeito_foto") or {}
    efeito = escolha.get("efeito")
    tela, _ = _tela(foto, W, H)
    m2 = None
    if efeito in COM_RECORTE:
        m = mascara(foto, pasta)
        if m is None:
            efeito = "revelar"
        else:
            m2, _ = _tela_da_mascara(m, foto, W, H)
    desenho = DESENHOS.get(efeito) or _so_movimento
    tarefa = {**tarefa, "_zoom": float(cfg_render.get("zoom_maximo", 1.12))}
    destino = Path(destino)
    comando = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
               "-pix_fmt", "yuv420p", "-an", str(destino)]
    processo = subprocess.Popen(comando, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        contexto = desenho(tela, m2, W, H, frames, fps, tarefa)
        for i in range(frames):
            quadro = contexto(i)
            quadro = _atravessar(quadro, i, frames, fps, escolha, W, H)
            processo.stdin.write(np.ascontiguousarray(quadro).tobytes())
        processo.stdin.close()
        erro = processo.stderr.read().decode("utf-8", "replace")
        if processo.wait() != 0:
            raise RuntimeError(f"o FFmpeg não gravou o efeito: {erro[-300:]}")
    except BaseException:
        processo.kill()
        destino.unlink(missing_ok=True)
        raise
    return destino


def _tela_da_mascara(m, foto, W, H):
    """A máscara (pequena) ampliada e cortada exatamente como a foto em _tela."""
    from PIL import Image

    with Image.open(foto) as im:
        largo, alto = im.size
    escala = max(2 * W / largo, 2 * H / alto)
    m = cv2.resize(m, (math.ceil(largo * escala), math.ceil(alto * escala)), interpolation=cv2.INTER_LINEAR)
    m = cv2.GaussianBlur(m, (0, 0), 2)
    y0, x0 = (m.shape[0] - 2 * H) // 2, (m.shape[1] - 2 * W) // 2
    return m[y0:y0 + 2 * H, x0:x0 + 2 * W], None


def _atravessar(quadro, i, frames, fps, escolha, W, H):
    """O zoom que atravessa: a câmera mergulha no centro nos últimos ATRAVESSAR segundos (sai) e sai de dentro da
    foto nos primeiros (entra), com o desfoque de movimento."""
    n = max(2, int(ATRAVESSAR * fps))
    p = None
    if escolha.get("sai") and i >= frames - n:
        p = (i - (frames - n)) / (n - 1)
        s = 1 + 1.6 * p ** 2.2
    elif escolha.get("entra") and i < n:
        p = 1 - i / (n - 1)
        s = 1 + 1.0 * _suave(p) ** 1.5
    if p is None:
        return quadro
    M = np.float32([[s, 0, W / 2 - s * W / 2], [0, s, H / 2 - s * H / 2]])
    quadro = cv2.warpAffine(quadro, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    raio = int(2 + 22 * p) | 1
    borrado = cv2.GaussianBlur(quadro, (raio, raio), 0)
    return cv2.addWeighted(quadro, 1 - 0.7 * p, borrado, 0.7 * p, 0)


def _so_movimento(tela, m2, W, H, frames, fps, tarefa):
    movimento = tarefa.get("movimento", "aproximar")

    def quadro(i):
        s, cx, cy = _movimento_base(movimento, i / max(frames - 1, 1), W, H, tarefa.get("_zoom", 1.12))
        return _no_lugar(tela, s, cx, cy, W / 2, H / 2, W, H)
    return quadro


def _revelar(tela, m2, W, H, frames, fps, tarefa):
    """Começa no detalhe (o assunto, se o recorte achou; senão um pouco acima do meio) e recua até a foto inteira."""
    alvo = _centro_do_assunto(m2) if m2 is not None else (W / 2, H * 0.42)
    perto = 1.75

    def quadro(i):
        p = i / max(frames - 1, 1)
        q = _sai(p / 0.75)
        s = perto + (1.0 - perto) * q + 0.03 * max(0.0, p - 0.75) / 0.25
        cx = alvo[0] + (W / 2 - alvo[0]) * q
        cy = alvo[1] + (H / 2 - alvo[1]) * q
        # o centro nunca deixa a borda da foto entrar na tela
        cx = min(max(cx, W / (2 * s)), W - W / (2 * s))
        cy = min(max(cy, H / (2 * s)), H - H / (2 * s))
        return _no_lugar(tela, s, cx, cy, W / 2, H / 2, W, H)
    return quadro


def _profundidade(tela, m2, W, H, frames, fps, tarefa):
    """O fundo (com o assunto apagado) anda devagar para um lado; o assunto, na frente, cresce e anda para o outro."""
    pequena = cv2.resize(tela, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    buraco = cv2.dilate(cv2.resize(m2, (W // 2, H // 2)), np.ones((15, 15), np.uint8))
    fundo = cv2.inpaint(pequena, (buraco > 60).astype(np.uint8) * 255, 9, cv2.INPAINT_TELEA)
    fundo = cv2.GaussianBlur(cv2.resize(fundo, (2 * W, 2 * H), interpolation=cv2.INTER_CUBIC), (0, 0), 3)
    ys, xs = np.nonzero(m2 > 128)
    ax, ay = float(xs.mean()) / 2, float(ys.max()) / 2  # o pé do assunto
    lado = 1 if ax < W / 2 else -1

    def quadro(i):
        p = _suave(i / max(frames - 1, 1))
        base = _no_lugar(fundo, 1.06 + 0.05 * p, W / 2, H / 2, W / 2 + lado * 0.012 * W * p, H / 2, W, H)
        s = 1.06 + 0.12 * p
        frente = _no_lugar(tela, s, ax, ay, ax - lado * 0.018 * W * p, ay + 0.01 * H * (1 - p), W, H)
        alfa = _no_lugar(m2, s, ax, ay, ax - lado * 0.018 * W * p, ay + 0.01 * H * (1 - p), W, H, cv2.BORDER_CONSTANT)
        return _misturar(base, frente, alfa)
    return quadro


def _moldura(tela, m2, W, H, frames, fps, tarefa):
    """A foto num quadro de borda branca sobre a própria foto desfocada; depois o assunto cresce e sai do quadro."""
    fundo = cv2.GaussianBlur(cv2.resize(tela, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 6)
    fundo = (cv2.resize(fundo, (2 * W, 2 * H), interpolation=cv2.INTER_CUBIC) * 0.42).astype(np.uint8)
    ys, xs = np.nonzero(m2 > 128)
    escala_q = 0.70
    cx_q, cy_q = W / 2, H * 0.53
    pe = (float(xs.mean()) / 2, float(ys.max()) / 2)
    borda = 12
    x0, y0 = int(cx_q - W * escala_q / 2), int(cy_q - H * escala_q / 2)
    x1, y1 = int(cx_q + W * escala_q / 2), int(cy_q + H * escala_q / 2)
    quadro_mascara = np.zeros((H, W), np.uint8)
    cv2.rectangle(quadro_mascara, (x0, y0), (x1, y1), 255, -1)
    contorno = np.zeros((H, W), np.uint8)
    cv2.rectangle(contorno, (x0 - borda, y0 - borda), (x1 + borda, y1 + borda), 255, -1)
    sombra = cv2.GaussianBlur(contorno, (0, 0), 28)
    # o fundo, a sombra e a borda branca não mexem: feitos uma vez (por quadro, o clipe levava 70 s)
    parado = _no_lugar(fundo, 1.0, W / 2, H / 2, W / 2, H / 2, W, H)
    parado = _misturar(parado, np.zeros_like(parado), (sombra * 0.6).astype(np.uint8))
    parado[contorno > 0] = (245, 245, 245)

    def quadro(i):
        p = i / max(frames - 1, 1)
        z = 1.0 + 0.04 * p
        base = parado.copy()
        dentro = _no_lugar(tela, escala_q * z, W / 2, H / 2, cx_q, cy_q, W, H)
        base = _misturar(base, dentro, quadro_mascara)
        # o assunto: começa no lugar dele dentro do quadro e cresce a partir do pé, passando por cima da borda
        q = _sai((p - 0.22) / 0.4)
        s = escala_q * z * (1 + 0.22 * q)
        px = cx_q + (pe[0] - W / 2) * escala_q * z
        py = cy_q + (pe[1] - H / 2) * escala_q * z
        frente = _no_lugar(tela, s, pe[0], pe[1], px, py, W, H)
        alfa = _no_lugar(m2, s, pe[0], pe[1], px, py, W, H, cv2.BORDER_CONSTANT)
        if q <= 0:
            alfa = cv2.bitwise_and(alfa, quadro_mascara)
        return _misturar(base, frente, alfa)
    return quadro


def _rabisco(tela, m2, W, H, frames, fps, tarefa):
    """O movimento lento de sempre e, por cima, um contorno à mão que se desenha em volta do assunto e treme (o traço
    é redesenhado com outro tremor a cada 3 quadros, como animação feita à mão)."""
    m = cv2.resize(m2, (W, H), interpolation=cv2.INTER_LINEAR)
    m = cv2.dilate((m > 128).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contorno = max(contornos, key=cv2.contourArea)[:, 0, :].astype(np.float32)
    passo = max(1, len(contorno) // 220)
    pontos = cv2.approxPolyDP(np.ascontiguousarray(contorno[::passo]).reshape(-1, 1, 2), 3, True)[:, 0, :]
    # o laço passa um pouco do começo, como quem circula com a caneta
    pontos = np.vstack([pontos, pontos[: max(2, len(pontos) // 8)]])
    movimento = tarefa.get("movimento", "aproximar")
    t0, t1 = 0.12, 0.62

    def quadro(i):
        p = i / max(frames - 1, 1)
        s, cx, cy = _movimento_base(movimento, p, W, H, zoom=1.06)
        base = _no_lugar(tela, s, cx, cy, W / 2, H / 2, W, H)
        feito = _sai((p - t0) / (t1 - t0))
        if feito <= 0:
            return base
        sorteio = np.random.default_rng(i // 3)
        n = max(2, int(len(pontos) * feito))
        trecho = pontos[:n] + sorteio.normal(0, 2.2, (n, 2))
        na_tela = np.stack([(trecho[:, 0] - cx) * s + W / 2, (trecho[:, 1] - cy) * s + H / 2], 1)
        linha = np.round(na_tela * 4).astype(np.int32).reshape(-1, 1, 2)
        sombra = base.copy()
        cv2.polylines(sombra, [linha + 8], False, (0, 0, 0), 12, cv2.LINE_AA, shift=2)
        base = cv2.addWeighted(base, 0.6, sombra, 0.4, 0)
        cv2.polylines(base, [linha], False, AMARELO, 9, cv2.LINE_AA, shift=2)
        segunda = np.round((na_tela + sorteio.normal(0, 3.0, na_tela.shape)) * 4).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(base, [segunda], False, AMARELO, 3, cv2.LINE_AA, shift=2)
        return base
    return quadro


def _celular(tela, m2, W, H, frames, fps, tarefa):
    """A foto na tela de um celular que sobe do pé da tela, sobre a própria foto desfocada e escura."""
    fundo = cv2.GaussianBlur(cv2.resize(tela, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (0, 0), 5)
    fundo = (cv2.resize(fundo, (W, H), interpolation=cv2.INTER_CUBIC) * 0.38).astype(np.uint8)
    alt, larg = int(H * 0.86), int(H * 0.86 * 0.49)
    raio, aro = 58, 16
    # a tela do celular: o meio da foto, em pé, no formato da tela
    tela_l, tela_a = larg - 2 * aro, alt - 2 * aro
    fatia = int(2 * H * tela_l / tela_a)
    meio = tela[:, (2 * W - fatia) // 2:(2 * W - fatia) // 2 + fatia]
    conteudo = cv2.resize(meio, (tela_l, tela_a), interpolation=cv2.INTER_AREA)
    corpo = np.zeros((alt, larg), np.uint8)
    _retangulo_redondo(corpo, 0, 0, larg - 1, alt - 1, raio, 255)
    vidro = np.zeros((alt, larg), np.uint8)
    _retangulo_redondo(vidro, aro, aro, larg - 1 - aro, alt - 1 - aro, raio - aro, 255)
    sombra = cv2.GaussianBlur(np.pad(corpo, 60), (0, 0), 30)

    def quadro(i):
        p = i / max(frames - 1, 1)
        q = _sai(p / 0.35)
        x = (W - larg) // 2
        y = int((H - alt) / 2 + 30 + (1 - q) * H * 0.75)
        z = 1.0 + 0.05 * p
        img = fundo.copy()
        # a sombra e o corpo escuro
        _colar(img, np.zeros((alt + 120, larg + 120, 3), np.uint8), (sombra * 0.75).astype(np.uint8), x - 60, y - 30)
        _colar(img, np.full((alt, larg, 3), 18, np.uint8), corpo, x, y)
        dentro = cv2.resize(conteudo, None, fx=z, fy=z, interpolation=cv2.INTER_LINEAR)
        dy, dx = (dentro.shape[0] - conteudo.shape[0]) // 2, (dentro.shape[1] - conteudo.shape[1]) // 2
        dentro = dentro[dy:dy + conteudo.shape[0], dx:dx + conteudo.shape[1]]
        tela_cel = np.zeros((alt, larg, 3), np.uint8)
        tela_cel[aro:alt - aro, aro:larg - aro] = dentro
        cv2.rectangle(tela_cel, (larg // 2 - 60, aro + 14), (larg // 2 + 60, aro + 44), (0, 0, 0), -1)
        cv2.circle(tela_cel, (larg // 2 - 60, aro + 29), 15, (0, 0, 0), -1)
        cv2.circle(tela_cel, (larg // 2 + 60, aro + 29), 15, (0, 0, 0), -1)
        _colar(img, tela_cel, vidro, x, y)
        return img
    return quadro


def _retangulo_redondo(img, x0, y0, x1, y1, r, cor):
    cv2.rectangle(img, (x0 + r, y0), (x1 - r, y1), cor, -1)
    cv2.rectangle(img, (x0, y0 + r), (x1, y1 - r), cor, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(img, (cx, cy), r, cor, -1, cv2.LINE_AA)


def _colar(base, cima, alfa, x, y):
    """Cola cima em base na posição (x, y), com a transparência alfa, cortando o que sai da tela."""
    H, W = base.shape[:2]
    h, w = alfa.shape[:2]
    ax0, ay0 = max(0, -x), max(0, -y)
    bx0, by0 = max(0, x), max(0, y)
    bx1, by1 = min(W, x + w), min(H, y + h)
    if bx1 <= bx0 or by1 <= by0:
        return
    pedaco = base[by0:by1, bx0:bx1]
    base[by0:by1, bx0:bx1] = _misturar(pedaco, cima[ay0:ay0 + by1 - by0, ax0:ax0 + bx1 - bx0],
                                       alfa[ay0:ay0 + by1 - by0, ax0:ax0 + bx1 - bx0])


DESENHOS = {"revelar": _revelar, "profundidade": _profundidade, "moldura": _moldura, "rabisco": _rabisco,
            "celular": _celular}
