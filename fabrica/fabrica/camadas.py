"""Camadas e sons que a própria fábrica desenha, sem baixar nem copiar nada.

- Camadas de partículas (brasas e poeira): um laço de 6 s feito com numpy, somado à imagem com `blend=screen`, que só
  clareia: o fundo preto do laço some. O movimento é periódico, então o laço fecha sem emenda.
- Sons de animação (pop, passagem e contador): sintetizados pelo FFmpeg.

Tudo fica em efeitos/gerados/ e é feito uma vez por máquina.
"""
import shutil
import subprocess
import threading
from pathlib import Path

import numpy as np

from .util import rodar

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "efeitos" / "gerados"
LARGURA, ALTURA, FPS, SEGUNDOS = 1280, 720, 30, 6
_trava = threading.Lock()  # as cenas renderizam em paralelo, e todas pedem o mesmo arquivo na primeira vez

# nome: quantas partículas, tamanho, cor (B, G, R), voltas que cada uma dá no laço, deriva lateral, brilho
PARTICULAS = {
    "brasas": {"quantas": 90, "tamanho": (1.0, 3.2), "cor": (40, 120, 255), "voltas": (1, 2), "deriva": 26, "brilho": 1.0},
    "poeira": {"quantas": 140, "tamanho": (0.8, 2.4), "cor": (205, 215, 225), "voltas": (1, 1), "deriva": 14, "brilho": 0.42},
    # partículas douradas: poucas, maiores e devagar, para os vídeos de dormir (do estudo da Dotti, 2026-11-22)
    "douradas": {"quantas": 55, "tamanho": (1.6, 3.8), "cor": (70, 190, 255), "voltas": (1, 1), "deriva": 34, "brilho": 0.8},
}
SONS = {
    "pop": "aevalsrc='0.9*sin(2*PI*(520+900*exp(-40*t))*t)*exp(-26*t)':d=0.18:s=48000",
    "passagem": "anoisesrc=d=0.42:c=pink:r=48000:a=0.8,highpass=f=300,lowpass=f=4200,"
                "afade=t=in:d=0.2,afade=t=out:st=0.2:d=0.22",
    "contador": "aevalsrc='0.7*sin(2*PI*1500*t)*exp(-90*mod(t,0.07))':d=0.42:s=48000,afade=t=out:st=0.3:d=0.12",
    # folha de papel: chiado curto e agudo, como uma ficha posta na mesa
    "papel": "anoisesrc=d=0.26:c=white:r=48000:a=0.5,highpass=f=1800,lowpass=f=7000,"
             "afade=t=in:d=0.03,afade=t=out:st=0.06:d=0.2",
    # bipe de terminal: dois toques secos
    "bipe": "aevalsrc='0.45*sin(2*PI*1900*t)*(lt(t,0.05)+gt(t,0.09)*lt(t,0.14))':d=0.18:s=48000",
    # grave: um baque baixo que some devagar
    "grave": "aevalsrc='0.9*sin(2*PI*(46+70*exp(-12*t))*t)*exp(-5*t)':d=0.7:s=48000,afade=t=out:st=0.45:d=0.25",
    # os sons por evento das formas novas (do estudo da Dotti, 2026-11-22): cada momento da animação tem o seu
    # carimbo: o baque surdo da borracha na mesa, com o estalo do papel
    "carimbo": "aevalsrc='0.9*sin(2*PI*(90+160*exp(-30*t))*t)*exp(-22*t)+0.35*(random(0)*2-1)*exp(-60*t)':d=0.3:s=48000",
    # máquina de escrever: oito toques secos e um sino curto no fim
    "maquina": "aevalsrc='0.6*(random(0)*2-1)*exp(-260*mod(t,0.085))*lt(t,0.68)+0.25*sin(2*PI*2600*t)*exp(-14*(t-0.7))"
               "*gt(t,0.7)':d=0.95:s=48000,highpass=f=900",
    # a palavra batida: um golpe grave com ar em volta
    "slam": "aevalsrc='1.0*sin(2*PI*(55+220*exp(-24*t))*t)*exp(-7*t)+0.4*(random(0)*2-1)*exp(-18*t)':d=0.55:s=48000,"
            "lowpass=f=5000",
    # o clique do botão de inscrição
    "clique": "aevalsrc='0.8*(random(0)*2-1)*exp(-900*t)+0.5*sin(2*PI*3200*t)*exp(-400*t)':d=0.06:s=48000",
    # o sino das notificações: duas notas
    "sino": "aevalsrc='0.5*sin(2*PI*1320*t)*exp(-6*t)+0.4*sin(2*PI*1760*(t-0.12))*exp(-6*(t-0.12))*gt(t,0.12)':"
            "d=0.9:s=48000",
    # o obturador da câmera: dois estalos
    "foto": "aevalsrc='0.8*(random(0)*2-1)*(exp(-500*t)+exp(-500*(t-0.07))*gt(t,0.07))':d=0.16:s=48000,highpass=f=1500",
    # o ponto que acende no mapa: um sonar curto
    "ping": "aevalsrc='0.6*sin(2*PI*1180*t)*exp(-9*t)':d=0.5:s=48000",
    # uma tecla
    "tecla": "aevalsrc='0.7*(random(0)*2-1)*exp(-300*t)':d=0.05:s=48000,highpass=f=1200",
}


def _quadro(cfg, sementes, t) -> np.ndarray:
    """Um quadro do laço. t vai de 0 a 1, e t=1 é igual a t=0: cada partícula dá um número inteiro de voltas."""
    x0, y0, voltas, fase, tamanho = sementes
    y = (y0 - voltas * t * ALTURA) % ALTURA
    x = (x0 + cfg["deriva"] * np.sin(2 * np.pi * (t * voltas + fase))) % LARGURA
    pisca = 0.65 + 0.35 * np.sin(2 * np.pi * (3 * t + fase))
    quadro = np.zeros((ALTURA, LARGURA, 3), np.float32)
    grade_y, grade_x = np.ogrid[-8:9, -8:9]
    for i in range(len(x0)):
        cx, cy = int(x[i]), int(y[i])
        forca = np.exp(-(grade_x ** 2 + grade_y ** 2) / (2 * tamanho[i] ** 2)) * pisca[i] * cfg["brilho"]
        a, b = max(cy - 8, 0), min(cy + 9, ALTURA)
        c, d = max(cx - 8, 0), min(cx + 9, LARGURA)
        recorte = forca[a - cy + 8:b - cy + 8, c - cx + 8:d - cx + 8, None]
        quadro[a:b, c:d] += recorte * np.array(cfg["cor"], np.float32)
    return np.clip(quadro, 0, 255).astype(np.uint8)


def laco(nome: str) -> Path:
    """O arquivo do laço, feito na primeira vez."""
    destino = PASTA / f"camada_{nome}.mp4"
    with _trava:
        if not destino.exists():
            if nome == "vazando":
                _gravar(destino, FPS * SEGUNDOS, lambda k, total: _quadro_vazando(k / total))
            else:
                _gravar_laco(nome, destino)
    return destino


def _gravar(destino: Path, total: int, quadro) -> None:
    """Grava `total` quadros (quadro(k, total) -> imagem BGR) num MP4 sem som."""
    PASTA.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp.mp4")
    processo = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{LARGURA}x{ALTURA}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         str(temporario)], stdin=subprocess.PIPE)
    for k in range(total):
        processo.stdin.write(quadro(k, total).tobytes())
    processo.stdin.close()
    if processo.wait():
        raise RuntimeError(f"o FFmpeg não gravou {destino.name}")
    shutil.move(str(temporario), destino)


_GRADE_Y, _GRADE_X = np.mgrid[0:ALTURA, 0:LARGURA].astype(np.float32)


def _quadro_vazando(t) -> np.ndarray:
    """A luz vazando: três manchas grandes e quentes que passeiam devagar pela borda da tela. Periódico em t."""
    quadro = np.zeros((ALTURA, LARGURA, 3), np.float32)
    manchas = (((0.12, 0.2), (0.10, 0.25), 1, (40, 110, 255), 0.55),    # laranja, no canto de cima à esquerda
               ((0.9, 0.75), (0.08, 0.2), 1, (60, 60, 230), 0.45),      # vermelho, embaixo à direita
               ((0.75, 0.1), (0.15, 0.1), 2, (90, 200, 255), 0.35))     # dourado, no alto
    for (cx, cy), (ax, ay), voltas, cor, forca in manchas:
        x = (cx + ax * np.sin(2 * np.pi * voltas * t)) * LARGURA
        y = (cy + ay * np.cos(2 * np.pi * voltas * t)) * ALTURA
        raio = 0.28 * LARGURA
        brilho = np.exp(-((_GRADE_X - x) ** 2 + (_GRADE_Y - y) ** 2) / (2 * raio ** 2)) * forca
        quadro += brilho[..., None] * np.array(cor, np.float32)
    return np.clip(quadro, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------------- transições dos vídeos de dormir
# Do estudo da Dotti (2026-11-22): as transições aprovadas por ela são queima, flash, dissolve com ruído, derreter pela
# luz e superexposição. Aqui cada clipe é renderizado sozinho (sem sobrepor o seguinte), então a transição é uma luz
# que cobre o corte: o clipe termina com a primeira metade dela e o seguinte começa com a segunda, somadas por cima
# (blend screen, que só clareia). No pico, a tela fica clara e o corte some embaixo.
TRANSICOES = ("queima", "superexposicao", "dissolve", "derreter")
METADE = 0.4  # segundos de cada metade da transição


def _ruido_suave(sorteio, escala=6) -> np.ndarray:
    """Um campo de ruído suave de 0 a 1 (soma de ondas com direção e fase sorteadas)."""
    campo = np.zeros((ALTURA, LARGURA), np.float32)
    for k in range(1, 5):
        for _ in range(3):
            angulo, fase = sorteio.uniform(0, 2 * np.pi), sorteio.uniform(0, 2 * np.pi)
            freq = escala * k / LARGURA
            campo += np.sin(2 * np.pi * freq * (_GRADE_X * np.cos(angulo) + _GRADE_Y * np.sin(angulo)) + fase) / k
    campo -= campo.min()
    return campo / max(float(campo.max()), 1e-6)


def _quadro_transicao(nome, p, campos) -> np.ndarray:
    """O quadro da transição com força p (0 a 1, o pico no corte). BGR."""
    branco = np.array((255, 255, 255), np.float32)
    if nome == "queima":
        frente = np.clip((p * 1.35 - campos["suave"]) / 0.1, 0, 1)
        miolo = np.clip((p * 1.35 - campos["suave"] - 0.1) / 0.12, 0, 1)
        borda = np.clip(frente - miolo, 0, 1)
        quadro = borda[..., None] * np.array((30, 130, 255), np.float32) + miolo[..., None] * branco
    elif nome == "superexposicao":
        raio = np.hypot(_GRADE_X / LARGURA - 0.5, _GRADE_Y / ALTURA - 0.5)
        quadro = np.clip(p * 1.7 - raio * 0.9, 0, 1)[..., None] * np.array((235, 245, 255), np.float32)
    elif nome == "dissolve":
        quadro = np.clip((p * 1.25 - campos["grao"]) / 0.05, 0, 1)[..., None] * branco
    else:  # derreter: a luz escorre de cima para baixo, em ondas
        onda = 0.06 * np.sin(_GRADE_X / LARGURA * 2 * np.pi * 5 + campos["suave"] * 3)
        quadro = np.clip((p * 1.45 - _GRADE_Y / ALTURA - onda) / 0.12, 0, 1)[..., None] * np.array((225, 240, 255), np.float32)
    return np.clip(quadro, 0, 255).astype(np.uint8)


def transicao(nome: str) -> Path:
    """O arquivo da transição (2 x METADE segundos, o pico no meio), feito na primeira vez."""
    destino = PASTA / f"transicao_{nome}.mp4"
    with _trava:
        if not destino.exists():
            sorteio = np.random.default_rng(sum(map(ord, nome)))
            campos = {"suave": _ruido_suave(sorteio), "grao": sorteio.uniform(0, 1, (ALTURA, LARGURA)).astype(np.float32)}
            total = int(round(2 * METADE * FPS))

            def quadro(k, total_):
                p = 1 - abs((k + 0.5) / total_ * 2 - 1)  # sobe até o meio e desce
                return _quadro_transicao(nome, p ** 0.8, campos)
            _gravar(destino, total, quadro)
    return destino


def _gravar_laco(nome: str, destino: Path) -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    cfg = PARTICULAS[nome]
    sorteio = np.random.default_rng(sum(map(ord, nome)))
    n = cfg["quantas"]
    sementes = (sorteio.uniform(0, LARGURA, n), sorteio.uniform(0, ALTURA, n),
                sorteio.integers(cfg["voltas"][0], cfg["voltas"][1] + 1, n), sorteio.uniform(0, 1, n),
                sorteio.uniform(*cfg["tamanho"], n))
    temporario = destino.with_suffix(".tmp.mp4")
    processo = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{LARGURA}x{ALTURA}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         str(temporario)], stdin=subprocess.PIPE)
    total = FPS * SEGUNDOS
    for k in range(total):
        processo.stdin.write(_quadro(cfg, sementes, k / total).tobytes())
    processo.stdin.close()
    if processo.wait():
        raise RuntimeError(f"o FFmpeg não gravou a camada {nome}")
    shutil.move(str(temporario), destino)


# Sons gravados de verdade (do estudo da Dotti, 2026-11-22: os efeitos dela são gravações, cada evento com o seu). Vêm
# dos pacotes Impact Sounds, Interface Sounds e UI Audio da Kenney (kenney.nl), licença CC0, baixados em 2026-11-22 com
# a autorização do usuário; a licença de cada pacote fica junto (efeitos/sons_cc0/kenney/*/License.txt). Cada evento tem
# várias versões, e a vez (k) escolhe uma, para o mesmo som não se repetir igual a cada animação. O que não tem gravação
# (passagem, papel, máquina, contador, bipe, grave, foto) segue feito pelo ffmpeg, como reserva também se o arquivo faltar
GRAVADOS_PASTA = RAIZ / "efeitos" / "sons_cc0" / "kenney"
GRAVADOS = {
    "carimbo": ("impact-sounds", "impactSoft_heavy_00{}", 5),
    "slam": ("impact-sounds", "impactPunch_heavy_00{}", 5),
    "clique": ("ui-audio", "click{}", 5, 1),
    "tecla": ("interface-sounds", "click_00{}", 5, 1),
    "sino": ("interface-sounds", "confirmation_00{}", 4, 1),
    "ping": ("interface-sounds", "glass_00{}", 6, 1),
    "pop": ("interface-sounds", "drop_00{}", 3, 2),  # drop_002 a 004: o pluck_001 tinha só 0,1 s
}


def _gravado(nome: str, k: int):
    """O arquivo gravado da k-ésima vez deste evento, ou None."""
    if nome not in GRAVADOS:
        return None
    pacote, molde, quantos, *base = GRAVADOS[nome]
    arquivo = GRAVADOS_PASTA / pacote / (molde.format((k % quantos) + (base[0] if base else 0)) + ".ogg")
    return arquivo if arquivo.exists() else None


def som(nome: str, k: int = 0) -> Path:
    """O arquivo do som de animação, feito na primeira vez: a gravação (em WAV estéreo de 48 kHz, como o render mistura)
    quando o evento tem uma, senão o som feito pelo ffmpeg. k: a vez do evento no vídeo, para variar a gravação."""
    gravado = _gravado(nome, k)
    destino = PASTA / (f"som_{nome}_gravado_{gravado.stem}.wav" if gravado else f"som_{nome}.wav")
    with _trava:
        if not destino.exists():
            PASTA.mkdir(parents=True, exist_ok=True)
            if gravado:
                rodar(["ffmpeg", "-y", "-loglevel", "error", "-i", gravado, "-ar", "48000", "-ac", "2", destino])
            else:
                rodar(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", SONS[nome], "-ac", "2", destino])
    return destino
