"""A limpeza do trecho do garimpo: corte do editor e logo de canal no canto, medidos nos pixels.

Os vídeos são feitos aqui pelo ffmpeg (lavfi), sem rede e sem modelo."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fabrica import garimpo  # noqa: E402
from fabrica.util import duracao_audio  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="sem ffmpeg")

# chiado que muda a cada quadro: o quadro inteiro se mexe, como uma filmagem com câmera andando
CHIADO = "color=c=gray:s=640x360:r=25:d={d},noise=alls=80:allf=t+u"
LOGO = "drawbox=x={x}:y={y}:w=70:h=40:color=red@1:t=fill,drawbox=x={x2}:y={y2}:w=50:h=20:color=white@1:t=fill"


def _video(destino, filtro, d=4.0):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", filtro.format(d=d), "-t", str(d),
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(destino)], check=True)
    return destino


def _com_logo(x, y):
    return CHIADO + "," + LOGO.format(x=x, y=y, x2=x + 10, y2=y + 10)


def test_corte_do_editor_fica_com_o_maior_pedaco(tmp_path):
    arquivo = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=640x360:r=25:d=2.5",
                    "-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=6", "-filter_complex",
                    "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", str(arquivo)], check=True)
    antes = duracao_audio(arquivo)
    feito = garimpo.limpar_trecho(arquivo, 3.0, log=lambda *_: None)
    assert feito["cortes"] >= 1
    assert 2.0 < feito["deslocamento"] < 3.0  # o pedaço vermelho do começo saiu
    assert duracao_audio(arquivo) < antes


def test_pedaco_curto_demais_deixa_o_trecho_como_veio(tmp_path):
    arquivo = tmp_path / "t.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=640x360:r=25:d=2",
                    "-f", "lavfi", "-i", "color=c=blue:s=640x360:r=25:d=2", "-filter_complex",
                    "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", str(arquivo)], check=True)
    antes = arquivo.read_bytes()
    assert garimpo.limpar_trecho(arquivo, 3.0, log=lambda *_: None) == {}
    assert arquivo.read_bytes() == antes


@pytest.mark.parametrize("canto,x,y", [("cima-esq", 12, 12), ("baixo-dir", 558, 308)])
def test_logo_parado_no_canto_e_achado(tmp_path, canto, x, y):
    quadros = garimpo._quadros_cinza(_video(tmp_path / "t.mp4", _com_logo(x, y)))
    logo = garimpo.canto_do_logo(quadros)
    assert logo and logo["canto"] == canto
    # o aperto cobre o logo (82 px de 640 na largura, 52 de 360 na altura) sem passar muito dele
    assert min(82 / 640, 52 / 360) <= logo["aperto"] <= garimpo.APERTO_MAXIMO


def test_sem_logo_e_plano_parado_nao_apertam(tmp_path):
    assert garimpo.canto_do_logo(garimpo._quadros_cinza(_video(tmp_path / "a.mp4", CHIADO))) is None
    # tudo parado: o logo não se separa do cenário, e nada é cortado
    parado = "color=c=gray:s=640x360:r=25:d={d}," + LOGO.format(x=12, y=12, x2=22, y2=22)
    assert garimpo.canto_do_logo(garimpo._quadros_cinza(_video(tmp_path / "b.mp4", parado))) is None


def test_limpar_trecho_tira_o_logo_e_mantem_a_tela_deitada(tmp_path):
    arquivo = _video(tmp_path / "t.mp4", _com_logo(12, 12))
    feito = garimpo.limpar_trecho(arquivo, 3.0, log=lambda *_: None)
    assert feito["logo"] == "cima-esq" and feito["cortes"] == 0
    assert garimpo.canto_do_logo(garimpo._quadros_cinza(arquivo)) is None
    assert not garimpo.em_pe(arquivo)


def test_config_desliga_a_limpeza(tmp_path):
    arquivo = _video(tmp_path / "t.mp4", _com_logo(12, 12))
    assert garimpo.limpar_trecho(arquivo, cfg={"cortar_editor": False, "tirar_logo": False}) == {}


def test_maior_pedaco_para_antes_do_corte():
    inicio, fim = garimpo.maior_pedaco([2.0, 3.0], 10.0)
    assert inicio == 3.0 and fim == 10.0
    inicio, fim = garimpo.maior_pedaco([8.0], 10.0)
    assert inicio == 0.0 and fim < 8.0
