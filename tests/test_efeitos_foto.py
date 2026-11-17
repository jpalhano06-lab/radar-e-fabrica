"""Os efeitos de câmera nas fotos (efeitos_foto.py): a escolha, o assunto do recorte e o desenho, sem rede."""
from pathlib import Path

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


def _pedaco(tmp_path, ordem, ini, fim, bloco=1, texto="fala", animal=None, n=None):
    return {"tipo": "cena", "origem": "foto", "arquivo": _foto(tmp_path, f"{ordem}.jpg"), "ordem": ordem,
            "ini": ini, "fim": fim, "cena": {"n": n or ordem, "ini": ini, "bloco": bloco, "texto": texto,
                                              "animal": animal}}


def _preparar(arquivo):
    return arquivo, True


def test_espacados_e_nunca_dois_iguais_seguidos(tmp_path):
    linha = [_pedaco(tmp_path, i, i * 4.0, i * 4.0 + 4.0, animal="cobra") for i in range(1, 30)]
    esc = e.escolher(linha, tmp_path / "ef", CFG, e.config(type("P", (), {"config": {}, "perfil": {}})()), _preparar)
    feitos = [(p["ini"], esc[p["ordem"]]["efeito"]) for p in linha if esc.get(p["ordem"], {}).get("efeito")]
    assert len(feitos) >= 3
    assert all(b[0] - a[0] >= 15 for a, b in zip(feitos, feitos[1:]))
    assert all(a[1] != b[1] for a, b in zip(feitos, feitos[1:]))
    # sempre a mesma escolha para a mesma linha (o nome dos clipes depende dela)
    assert esc == e.escolher(linha, tmp_path / "ef", CFG, e.config(type("P", (), {"config": {}, "perfil": {}})()), _preparar)


def test_sem_efeito_na_tela_em_pe_nem_desligado(tmp_path):
    linha = [_pedaco(tmp_path, i, i * 4.0, i * 4.0 + 4.0) for i in range(1, 10)]
    assert e.escolher(linha, tmp_path, {**CFG, "vertical": True}, {"ativo": True}, _preparar) == {}
    assert e.escolher(linha, tmp_path, CFG, {"ativo": False}, _preparar) == {}


def test_cena_curta_e_video_ficam_de_fora(tmp_path):
    curta = _pedaco(tmp_path, 1, 0.0, 1.8)
    video = dict(_pedaco(tmp_path, 2, 20.0, 25.0), origem="video")
    assert e.escolher([curta, video], tmp_path, CFG, {"ativo": True, "atravessar": False}, _preparar) == {}


def test_recorte_so_em_cena_de_animal_ou_com_rosto(tmp_path):
    # cena aberta (sem animal e sem rosto): o recorte nem é tentado, e só o recuo pode entrar
    sem_assunto = _pedaco(tmp_path, 1, 0.0, 4.0)
    assert not e.pode_ter_assunto(sem_assunto["cena"], sem_assunto["arquivo"])
    esc = e.escolher([sem_assunto], tmp_path / "ef", CFG, {"ativo": True, "atravessar": False}, _preparar)
    assert esc[1]["efeito"] == "revelar"
    com_animal = _pedaco(tmp_path, 2, 0.0, 4.0, animal="baiacu")
    assert e.pode_ter_assunto(com_animal["cena"], com_animal["arquivo"])


def test_recuo_no_maximo_a_cada_30_segundos(tmp_path):
    linha = [_pedaco(tmp_path, i, i * 4.0, i * 4.0 + 4.0) for i in range(1, 30)]  # sem assunto: só o recuo cabe
    esc = e.escolher(linha, tmp_path / "ef", CFG, {"ativo": True, "atravessar": False}, _preparar)
    tempos = [p["ini"] for p in linha if esc.get(p["ordem"])]
    assert all(b - a >= 30 for a, b in zip(tempos, tempos[1:]))


def test_atravessar_so_na_troca_de_bloco(tmp_path):
    linha = [_pedaco(tmp_path, 1, 0.0, 3.0, bloco=1), _pedaco(tmp_path, 2, 3.0, 6.0, bloco=1),
             _pedaco(tmp_path, 3, 6.0, 9.0, bloco=2)]
    esc = e.escolher(linha, tmp_path / "ef", CFG, {"ativo": True, "intervalo": 999, "intervalo_revelar": 999}, _preparar)
    # o primeiro pedaço ganhou o recuo (primeira escolha); a troca de bloco é entre o 2 e o 3
    assert esc[2].get("sai") and esc[3].get("entra")
    assert not esc.get(1, {}).get("sai")


def test_celular_so_quando_a_fala_cita_e_a_foto_nao_e_tela():
    assert e.pede_celular({"texto": "O vídeo viralizou no TikTok em poucas horas."})
    assert e.pede_celular({"texto": "Ele baixou o aplicativo do banco."})
    assert not e.pede_celular({"texto": "O leão caça à noite."})
    # a foto já é um celular: celular dentro de celular, não
    assert not e.pede_celular({"texto": "postou no Instagram",
                               "conferencia": {"legenda": "O que é: Uma mão segurando um smartphone (certeza alta)."}})


def test_assinatura_vazia_sem_efeito():
    # sem efeito, o nome do clipe não muda: nenhum vídeo antigo renderiza de novo por causa desta mudança
    assert e.assinatura(None) == ""
    assert e.assinatura({}) == ""
    assert "profundidade" in e.assinatura({"efeito": "profundidade"})


def test_cada_efeito_grava_um_clipe(tmp_path):
    foto = _foto(tmp_path)
    m = np.zeros((360, 640), np.uint8)
    cv2.circle(m, (320, 190), 90, 255, -1)
    chave_pasta = tmp_path / "ef"
    for efeito in (*e.EFEITOS, None):
        destino = tmp_path / f"{efeito}.mp4"
        tarefa = {"frames": 12, "movimento": "direita", "efeito_foto": {"efeito": efeito, "entra": efeito is None,
                                                                         "sai": efeito is None}}
        # o recorte vem da máscara pronta, para o teste não depender do GrabCut
        original = e.mascara
        e.mascara = lambda foto, pasta: cv2.resize(m, (420, 236))
        try:
            e.renderizar(tarefa, foto, CFG, chave_pasta, destino)
        finally:
            e.mascara = original
        assert destino.exists() and destino.stat().st_size > 1000, efeito
        quadros = int(cv2.VideoCapture(str(destino)).get(cv2.CAP_PROP_FRAME_COUNT))
        assert quadros == 12, (efeito, quadros)
