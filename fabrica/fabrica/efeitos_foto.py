"""O rabisco tremido nas fotos do vídeo: um contorno amarelo à mão que se desenha em volta da pessoa e treme.

Pedido do usuário em 2026-11-17, de um vídeo de "16 efeitos que o Claude cria". Seis efeitos foram feitos e testados
(recuo que revela, camadas em profundidade, quebra de moldura, rabisco, celular e zoom que atravessa); o usuário
aprovou só o rabisco ("único que eu aprovo é o rabisco, o resto pode remover"). Os outros saíram: não trazer de volta
sem ele pedir.

Só em foto com uma ou duas pessoas, achadas pelo detector de rostos da fábrica (rostos.py, YuNet, no próprio
computador): ele é confiável, e o contorno é desenhado em volta de quem ele achou. O contorno segue a silhueta (o
GrabCut do OpenCV a partir do rosto, como em recorte.py) quando o recorte convence pelas contas e tem todo rosto
dentro; senão, é um laço à mão em volta da cabeça e dos ombros. Animal ficou de fora: sem detector, o GrabCut pegava
o fundo (na cena 9 do teste-animacao-1min, a água em vez da água-viva), e conferir cada recorte com a visão gratuita
levava de 5 a 8 minutos por vídeo e parava quando os gratuitos batiam no limite.

Como entra: o render (render._tarefas_da_linha) pede a escolha (escolher) e, para a cena escolhida, o clipe sai daqui
(renderizar), quadro a quadro em numpy e OpenCV, e segue para o mesmo caminho dos outros clipes (título, símbolo,
visual do canal). Pouco e espaçado: no máximo um a cada `intervalo` segundos. Só na tela deitada. Nunca para o vídeo:
falhou, a cena sai com o movimento lento de sempre.
"""
import hashlib
import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

VERSAO = 10  # suba quando mudar o desenho: os clipes com rabisco renderizam de novo (os outros não mudam de nome)
EFEITO = "rabisco"
DURACAO_MINIMA = 2.5   # segundos: menos que isso o contorno não dá tempo de se desenhar
AMARELO = (63, 210, 255)  # BGR do #FFD23F, a cor de destaque do impacto
MAX_ROSTOS = 2  # foto de grupo fica fora: o recorte pegava o céu da caverna junto com as pessoas (ouro-da-serra, 183)
ROSTO_MINIMO = 0.06  # da largura da foto: gente menor que isso (pessoas ao longe) não ganha rabisco


def config(projeto) -> dict:
    padrao = {"ativo": True, "intervalo": 30}
    return {**padrao, **(projeto.config.get("efeitos_foto") or {}), **((projeto.perfil.get("efeitos_foto") or {}))}


# ------------------------------------------------------------------------------------------------ a escolha

CONFIANCA = 0.88  # do YuNet. O rostos.py aceita 0,7 (para o corte da foto, um falso rosto só desloca o corte); para o
# laço em volta, medido em 7 fotos: rostos de verdade de 0,89 a 0,92, falsos (mãos segurando uma tampa, uma taça de
# vinho) de 0,74 a 0,82
_CACHE_ROSTOS = {}


def _rostos(foto) -> list:
    """Os rostos certos e grandes o bastante para o rabisco, inteiros dentro da foto, em frações da foto:
    [(x, y, largura, altura)]. Detecção própria, mais exigente que a do rostos.py."""
    from PIL import Image

    from . import rostos

    foto = Path(foto)
    try:
        chave = (str(foto), foto.stat().st_mtime_ns)
    except OSError:
        return []
    if chave in _CACHE_ROSTOS:
        return _CACHE_ROSTOS[chave]
    achados = []
    if not rostos.rostos(foto):  # o detector normal, já guardado pela foto: sem ninguém, nem roda o exigente
        _CACHE_ROSTOS[chave] = achados
        return achados
    try:
        with Image.open(foto) as im:
            im.draft("RGB", (960, 960))
            im = im.convert("RGB")
            im.thumbnail((960, 960))
            matriz = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
        a, l_ = matriz.shape[:2]
        detector = cv2.FaceDetectorYN.create(rostos.MODELO, "", (l_, a), CONFIANCA, 0.3, 5000)
        _, brutos = detector.detect(matriz)
        for r in (brutos if brutos is not None else []):
            x, y, w, h = float(r[0]) / l_, float(r[1]) / a, float(r[2]) / l_, float(r[3]) / a
            # o rosto inteiro dentro da foto: cabeça cortada na borda não ganha laço
            if w >= ROSTO_MINIMO and x >= 0.02 and y >= 0.02 and x + w <= 0.98 and y + h <= 0.98:
                achados.append((x, y, w, h))
    except Exception:  # noqa: BLE001 - sem detector, sem rabisco
        achados = []
    _CACHE_ROSTOS[chave] = achados
    return achados


def tem_pessoa(foto) -> bool:
    """Uma ou duas pessoas grandes o bastante na foto."""
    return 1 <= len(_rostos(foto)) <= MAX_ROSTOS


def escolher(linha, pasta, cfg_render, cfg, preparar) -> dict:
    """{ordem do pedaço: {"efeito": "rabisco"}} para os pedaços que ganham o rabisco.

    linha: os pedaços do render (render._linha_do_tempo). preparar(arquivo) devolve a foto como ela entra na tela e
    se ela preenche a tela (render._foto_na_tela); o rabisco só vale para foto que preenche. Sai sempre o mesmo para
    a mesma linha: o nome dos clipes depende disso."""
    if not cfg.get("ativo", True) or cfg_render.get("vertical"):
        return {}
    escolhidos, ultimo_t = {}, -1e9
    intervalo = float(cfg.get("intervalo", 30))
    for p in linha:
        if p.get("tipo") != "cena" or p.get("origem") != "foto" or not p["arquivo"].exists():
            continue
        if p["fim"] - p["ini"] < DURACAO_MINIMA or p["ini"] - ultimo_t < intervalo:
            continue
        # só a cena inteira (um pedaço cortado pelo personagem não tem a pessoa inteira na tela)
        if abs(p["ini"] - float(p["cena"].get("ini", p["ini"]))) > 0.05:
            continue
        try:
            tela, preenche = preparar(p["arquivo"])
            if not preenche or not tem_pessoa(tela):
                continue
        except Exception:  # noqa: BLE001 - na dúvida, sem rabisco
            continue
        escolhidos[p["ordem"]] = {"efeito": EFEITO}
        ultimo_t = p["ini"]
    return escolhidos


def assinatura(escolha) -> str:
    """O pedaço do nome do clipe: vazio sem efeito, para os outros clipes não mudarem de nome."""
    if not escolha or escolha.get("efeito") != EFEITO:
        return ""
    return f"|efeito:{EFEITO}:v{VERSAO}"


# ------------------------------------------------------------------------------------------------ o contorno

LADO = 560
FRACAO_MIN, FRACAO_MAX = 0.06, 0.45


def mascara(foto, pasta):
    """A silhueta da pessoa (0 a 255, reduzida a LADO px), ou None se o recorte não convence. Guardada em pasta, pelo
    arquivo e pela data: cada foto é recortada uma vez."""
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
    m, motivo = None, "sem rosto"
    # primeiro o corpo a partir do rosto; não saindo, o retângulo do meio da foto (o homem das faíscas do
    # ouro-da-serra-gaucha, camisa escura no fundo escuro, só saiu assim). Nos dois, todo rosto dentro do recorte
    for jeito in ((achados,), ()) if achados else ():
        m, motivo = _recortar(foto, pasta, *jeito)
        if m is not None and not _rostos_dentro(m, achados):
            m, motivo = None, "o recorte deixou um rosto de fora"
        if m is not None:
            break
    if m is not None:
        cv2.imwrite(str(arquivo), m)
    nota.write_text(json.dumps({"ok": m is not None, "motivo": motivo}, ensure_ascii=False), encoding="utf-8")
    return m


def _rostos_dentro(m, achados) -> bool:
    a, l_ = m.shape[:2]
    return all(m[min(a - 1, int((y + h / 2) * a)), min(l_ - 1, int((x + w / 2) * l_))] >= 128
               for x, y, w, h in achados)


def _recortar(foto, pasta, rostos_=None):
    """GrabCut na foto reduzida (LADO px), partindo do corpo de quem aparece (do alto da cabeça a uns quatro rostos
    abaixo) ou, sem rostos_, do retângulo do meio da foto. A máscara fica nesse tamanho e é ampliada na hora de
    desenhar."""
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
    rect = (int(l_ * 0.12), int(a * 0.08), int(l_ * 0.76), int(a * 0.88))
    if rostos_:
        x0 = min(x - w * 1.3 for x, y, w, h in rostos_)
        x1 = max(x + w * 2.3 for x, y, w, h in rostos_)
        y0 = min(y - h * 0.5 for x, y, w, h in rostos_)
        y1 = max(y + h * 5.0 for x, y, w, h in rostos_)
        x0, y0, x1, y1 = max(0.01, x0), max(0.01, y0), min(0.99, x1), min(0.99, y1)
        rect = (int(x0 * l_), int(y0 * a), max(8, int((x1 - x0) * l_)), max(8, int((y1 - y0) * a)))
    m = np.zeros((a, l_), np.uint8)
    try:
        cv2.grabCut(pequena, m, rect, np.zeros((1, 65)), np.zeros((1, 65)), 5, cv2.GC_INIT_WITH_RECT)
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
    if areas.max() / areas.sum() < 0.65:  # o maior pedaço basta (as faíscas e os reflexos em volta saem)
        return None, "assunto em pedaços"
    assunto = (rotulos == k).astype(np.uint8) * 255
    contornos, _ = cv2.findContours(assunto, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    assunto = cv2.drawContours(np.zeros_like(assunto), contornos, -1, 255, cv2.FILLED)
    fracao = float((assunto > 0).mean())
    if not FRACAO_MIN <= fracao <= FRACAO_MAX:
        return None, f"assunto ocupa {fracao:.0%} da foto"
    # uma faixa de 3% dos lados (a cabeça pode encostar em cima e o corpo embaixo)
    faixa = max(2, int(min(a, l_) * 0.03))
    beirada = np.concatenate([assunto[:, :faixa].ravel(), assunto[:, -faixa:].ravel()])
    if float((beirada > 0).mean()) > 0.15:
        return None, "assunto colado na borda"
    # as contas de acabamento do recorte da colagem: sem fundo grudado e sem pontas
    teste = Path(pasta) / f"_teste_{hashlib.sha1(str(foto).encode()).hexdigest()[:8]}.png"
    try:
        Path(pasta).mkdir(parents=True, exist_ok=True)
        # sem o arquivo, recorte.limpo lia "nada grudado" e aprovava tudo: sem conferir, não passa
        if not cv2.imwrite(str(teste), np.dstack([pequena, assunto])) or not recorte.limpo(teste):
            return None, "recorte sujo"
    finally:
        teste.unlink(missing_ok=True)
    return assunto, "ok"


def laco(foto, W, H):
    """Sem silhueta boa: o laço em volta da cabeça e dos ombros de cada pessoa, na tela (W x H), como máscara."""
    from PIL import Image

    with Image.open(foto) as im:
        largo, alto = im.size
    escala = max(W / largo, H / alto)
    dx, dy = (largo * escala - W) / 2, (alto * escala - H) / 2
    m = np.zeros((H, W), np.uint8)
    for x, y, w, h in _rostos(foto):
        cx = (x + w / 2) * largo * escala - dx
        cy = (y + h * 0.85) * alto * escala - dy  # um pouco abaixo do rosto: cabeça e ombros
        eixo_x, eixo_y = w * largo * escala * 1.25, h * alto * escala * 1.35
        cv2.ellipse(m, (int(cx), int(cy)), (int(eixo_x), int(eixo_y)), 0, 0, 360, 255, -1)
    return m


# ------------------------------------------------------------------------------------------------ o desenho

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
    return imagem[y0:y0 + 2 * H, x0:x0 + 2 * W]


def _mascara_na_tela(m, foto, W, H):
    """A máscara (pequena) ampliada e cortada exatamente como a foto em _tela, já no tamanho da tela (W x H)."""
    from PIL import Image

    with Image.open(foto) as im:
        largo, alto = im.size
    escala = max(W / largo, H / alto)
    m = cv2.resize(m, (math.ceil(largo * escala), math.ceil(alto * escala)), interpolation=cv2.INTER_LINEAR)
    y0, x0 = (m.shape[0] - H) // 2, (m.shape[1] - W) // 2
    return m[y0:y0 + H, x0:x0 + W]


def _no_lugar(img, s, ax, ay, tx, ty, W, H):
    """img (no dobro da tela) escalada por s em volta do ponto (ax, ay) da tela e posta em (tx, ty) da tela."""
    M = np.float32([[s / 2, 0, tx - s * ax], [0, s / 2, ty - s * ay]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


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
    """Grava em destino o clipe da cena com o rabisco (sem som). foto: a foto como ela entra na tela. Sem pessoa na
    foto, o clipe sai só com o movimento lento."""
    W, H = cfg_render.get("largura", 1920), cfg_render.get("altura", 1080)
    fps = cfg_render.get("fps", 30)
    frames = int(tarefa["frames"])
    tela = _tela(foto, W, H)
    movimento = tarefa.get("movimento", "aproximar")
    contorno = None
    if (tarefa.get("efeito_foto") or {}).get("efeito") == EFEITO and tem_pessoa(foto):
        m = mascara(foto, pasta)
        contorno = _mascara_na_tela(m, foto, W, H) if m is not None else laco(foto, W, H)
    if contorno is not None and contorno.any():
        desenho = _rabisco(tela, contorno, W, H, frames, movimento)
    else:
        zoom = float(cfg_render.get("zoom_maximo", 1.12))

        def desenho(i):
            s, cx, cy = _movimento_base(movimento, i / max(frames - 1, 1), W, H, zoom)
            return _no_lugar(tela, s, cx, cy, W / 2, H / 2, W, H)
    destino = Path(destino)
    comando = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
               "-pix_fmt", "yuv420p", "-an", str(destino)]
    processo = subprocess.Popen(comando, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(frames):
            processo.stdin.write(np.ascontiguousarray(desenho(i)).tobytes())
        processo.stdin.close()
        erro = processo.stderr.read().decode("utf-8", "replace")
        if processo.wait() != 0:
            raise RuntimeError(f"o FFmpeg não gravou o rabisco: {erro[-300:]}")
    except BaseException:
        processo.kill()
        destino.unlink(missing_ok=True)
        raise
    return destino


def _rabisco(tela, m, W, H, frames, movimento):
    """O movimento lento de sempre e, por cima, um contorno à mão que se desenha em volta da máscara (W x H) e treme
    (o traço é redesenhado com outro tremor a cada 3 quadros, como animação feita à mão)."""
    m = cv2.dilate((m > 128).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contorno = max(contornos, key=cv2.contourArea)[:, 0, :].astype(np.float32)
    passo = max(1, len(contorno) // 220)
    pontos = cv2.approxPolyDP(np.ascontiguousarray(contorno[::passo]).reshape(-1, 1, 2), 3, True)[:, 0, :]
    # o laço passa um pouco do começo, como quem circula com a caneta
    pontos = np.vstack([pontos, pontos[: max(2, len(pontos) // 8)]])
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
