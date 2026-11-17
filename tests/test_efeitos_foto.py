"""O rabisco nas fotos (efeitos_foto.py): a escolha, o contorno e o desenho, sem rede."""
import cv2
import numpy as np

from fabrica import efeitos_foto as e

CFG = {"largura": 320, "altura": 180, "fps": 10}


def _foto(tmp_path, nome="foto.jpg"):
    """Um círculo claro (o assunto) sobre um fundo escuro com textura."""
    img = np.random.default_rng(1).integers(20, 60, (360, 640, 3), dtype=np.uint8)
    cv2.circle(img, (320, 190), 90, (60, 170, 230), -1)
    arquivo = tmp_path / nome
    cv2.imwrite(str(arquivo), img)
    return arquivo


def _pedaco(tmp_path, ordem, ini, fim):
    return {"tipo": "cena", "origem": "foto", "arquivo": _foto(tmp_path, f"{ordem}.jpg"), "ordem": ordem,
            "ini": ini, "fim": fim, "cena": {"n": ordem, "ini": ini, "bloco": 1, "texto": "fala"}}


def _preparar(arquivo):
    return arquivo, True


def _com_pessoa(funcao, rostos=((0.45, 0.3, 0.1, 0.18),)):
    """Roda funcao com um rosto achado em toda foto, para o teste não depender do detector."""
    original = e._rostos
    e._rostos = lambda foto: list(rostos)
    try:
        return funcao()
    finally:
        e._rostos = original


def test_so_o_rabisco_e_espacado(tmp_path):
    linha = [_pedaco(tmp_path, i, i * 4.0, i * 4.0 + 4.0) for i in range(1, 30)]
    esc = _com_pessoa(lambda: e.escolher(linha, tmp_path / "ef", CFG, {"ativo": True, "intervalo": 30}, _preparar))
    tempos = [p["ini"] for p in linha if p["ordem"] in esc]
    assert len(tempos) >= 2
    assert all(v == {"efeito": "rabisco"} for v in esc.values())
    assert all(b - a >= 30 for a, b in zip(tempos, tempos[1:]))
    # sempre a mesma escolha para a mesma linha (o nome dos clipes depende dela)
    assert esc == _com_pessoa(lambda: e.escolher(linha, tmp_path / "ef", CFG, {"ativo": True, "intervalo": 30},
                                                  _preparar))


def test_sem_rabisco_na_tela_em_pe_nem_desligado(tmp_path):
    linha = [_pedaco(tmp_path, i, i * 4.0, i * 4.0 + 4.0) for i in range(1, 10)]
    assert _com_pessoa(lambda: e.escolher(linha, tmp_path, {**CFG, "vertical": True}, {"ativo": True}, _preparar)) == {}
    assert _com_pessoa(lambda: e.escolher(linha, tmp_path, CFG, {"ativo": False}, _preparar)) == {}


def test_cena_curta_e_video_ficam_de_fora(tmp_path):
    curta = _pedaco(tmp_path, 1, 0.0, 1.8)
    video = dict(_pedaco(tmp_path, 2, 40.0, 45.0), origem="video")
    assert _com_pessoa(lambda: e.escolher([curta, video], tmp_path, CFG, {"ativo": True}, _preparar)) == {}


def test_so_em_foto_com_uma_ou_duas_pessoas(tmp_path):
    # sem pessoa (paisagem, animal, comida) não há rabisco: o recorte de animal pegava o fundo (a água no lugar da
    # água-viva, cena 9 do teste-animacao-1min)
    linha = [_pedaco(tmp_path, 1, 0.0, 4.0)]
    assert _com_pessoa(lambda: e.escolher(linha, tmp_path, CFG, {"ativo": True}, _preparar), rostos=()) == {}
    tres = [(0.1, 0.3, 0.08, 0.15), (0.4, 0.3, 0.08, 0.15), (0.7, 0.3, 0.08, 0.15)]
    assert _com_pessoa(lambda: e.escolher(linha, tmp_path, CFG, {"ativo": True}, _preparar), rostos=tres) == {}
    assert _com_pessoa(lambda: e.escolher(linha, tmp_path, CFG, {"ativo": True}, _preparar)) == {1: {"efeito": "rabisco"}}


def test_foto_sem_rosto_nao_tem_pessoa(tmp_path):
    # o detector de verdade, numa imagem sem ninguém
    assert not e.tem_pessoa(_foto(tmp_path))


def test_os_outros_efeitos_sairam():
    # pedido do usuário em 2026-11-17: "único que eu aprovo é o rabisco, o resto pode remover"
    for nome in ("_revelar", "_profundidade", "_moldura", "_celular", "_atravessar", "pede_celular"):
        assert not hasattr(e, nome), nome


def test_assinatura_vazia_sem_rabisco():
    # sem rabisco, o nome do clipe não muda: nenhum vídeo antigo renderiza de novo
    assert e.assinatura(None) == ""
    assert e.assinatura({}) == ""
    assert e.assinatura({"efeito": "moldura"}) == ""  # escolha antiga de um efeito que saiu
    assert "rabisco" in e.assinatura({"efeito": "rabisco"})


def test_laco_em_volta_do_rosto(tmp_path):
    foto = _foto(tmp_path)
    m = _com_pessoa(lambda: e.laco(foto, 320, 180))
    ys, xs = np.nonzero(m)
    assert len(xs) and 130 < xs.mean() < 190  # em volta do rosto, no meio da foto


def test_o_rabisco_grava_um_clipe(tmp_path):
    foto = _foto(tmp_path)
    for efeito in ("rabisco", None):
        destino = tmp_path / f"{efeito}.mp4"
        tarefa = {"frames": 12, "movimento": "direita", "efeito_foto": {"efeito": efeito}}
        _com_pessoa(lambda: e.renderizar(tarefa, foto, CFG, tmp_path / "ef", destino))
        assert destino.exists() and destino.stat().st_size > 1000, efeito
        assert int(cv2.VideoCapture(str(destino)).get(cv2.CAP_PROP_FRAME_COUNT)) == 12
