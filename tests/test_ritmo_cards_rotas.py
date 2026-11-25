"""Do estudo da Dotti (2026-11-22): ritmo das animações, cards de número, previsão da narração, outra rota do
garimpo e o som e a trilha de cada tema. Sem rede e sem modelo."""
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fabrica import animacoes, garimpo, previsao_narracao, trilha  # noqa: E402


def _projeto(**animacoes_cfg):
    return SimpleNamespace(config={"animacoes": animacoes_cfg}, perfil={}, offline=False, dados={})


# ------------------------------------------------------------------ cards de número


@pytest.mark.parametrize("texto,lingua,esperado", [
    ("Apple can take a cut, often up to thirty percent. Think", "en", "thirty percent"),
    ("More than two point three five billion active", "en", "two point three five billion"),
    ("In fiscal two thousand twenty-five, revenue topped four hundred billion", "en", "four hundred billion"),
    ("earned around one hundred billion dollars,", "en", "one hundred billion dollars"),
    ("caiu trinta por cento em dois anos", "pt", "trinta por cento"),
    ("custou dez mil reais", "pt", "dez mil reais"),
    ("costó tres millones de dólares", "es", "tres millones"),
])
def test_numero_que_pesa_vira_card(texto, lingua, esperado):
    assert animacoes.numero_que_pesa(texto, lingua) == esperado


@pytest.mark.parametrize("texto,lingua", [
    ("and hopes you come back in six years.", "en"),       # número pequeno, sem grandeza
    ("tinha dois cachorros", "pt"),
    ("Em mil novecentos e trinta e cinco, uma", "pt"),      # ano
    ("Ford and General Motors sell millions of trucks", "en"),  # grandeza sozinha
    ("In twenty twenty, Tesla joined the S and P five hundred.", "en"),  # nome de índice
    ("十億ドル", "ja"),                                       # língua sem card automático
])
def test_numero_que_nao_vira_card(texto, lingua):
    assert animacoes.numero_que_pesa(texto, lingua) == ""


# ------------------------------------------------------------------ ritmo


def _item(ini, fim, visual="texto_tela", automatico=False):
    return {"id": f"m{int(ini * 10):06d}", "c_ini": int(ini * 10), "ini": ini, "fim": fim, "visual": visual,
            **({"automatico": True} if automatico else {})}


@pytest.fixture
def tempo_do_item(monkeypatch):
    monkeypatch.setattr(animacoes, "_ancorar", lambda projeto, item, pela_fala=False: {"ini": item["ini"],
                                                                                      "fim": item["fim"]})


def test_espacar_deixa_cinco_segundos_livres(tempo_do_item):
    novos = [_item(10, 14), _item(16, 19), _item(19.5, 22), _item(30, 33)]
    ficam = animacoes.espacar(_projeto(), novos, [])
    assert [i["ini"] for i in ficam] == [10, 19.5, 30]


def test_espacar_respeita_o_que_ja_existe_e_a_familia_mais_forte(tempo_do_item):
    fixo = _item(0, 4)
    card = _item(20, 23, automatico=True)
    mapa = _item(24, 27, visual="mapa")
    ficam = animacoes.espacar(_projeto(), [card, mapa, _item(6, 8)], [fixo])
    assert [i["ini"] for i in ficam] == [24]  # o 6 cola no fixo; o mapa ganha do card ao lado dele


def test_espacar_no_maximo_seis_por_minuto(tempo_do_item):
    novos = [_item(t, t + 1) for t in range(0, 60, 7)]  # 9 no mesmo minuto, com 6 s livres entre elas
    ficam = animacoes.espacar(_projeto(), novos, [])
    assert len(ficam) == 6


def test_espacar_desliga_com_zero(tempo_do_item):
    novos = [_item(0, 4), _item(4.5, 6)]
    assert len(animacoes.espacar(_projeto(intervalo_minimo=0, por_minuto=0), novos, [])) == 2


# ------------------------------------------------------------------ previsão da narração


def test_previsao_precisa_de_medida_e_depois_avisa(tmp_path, monkeypatch):
    import fabrica.config
    monkeypatch.setattr(fabrica.config, "RAIZ", tmp_path)
    voz = {"provedor": "openspeaker", "voice_id": "v1"}
    linhas = []
    previsao_narracao.vigiar(voz, 10000, linhas.append).parar()
    assert "ainda sem medida" in linhas[-1]
    previsao_narracao.anotar(voz, 10000, 600)
    previsao_narracao.anotar(voz, 20000, 1400)
    segundos, medidas = previsao_narracao.previsto(voz, 10000)
    assert medidas == 2 and segundos == pytest.approx(650)
    vigia = previsao_narracao.vigiar(voz, 10000, linhas.append)
    assert "costuma levar uns 11 min" in linhas[-1]
    vigia.parar()
    assert previsao_narracao.previsto({"provedor": "genaipro", "voice_id": "outra"}, 100)[0] is None


def test_aviso_quando_passa_do_normal(tmp_path, monkeypatch):
    import fabrica.config
    monkeypatch.setattr(fabrica.config, "RAIZ", tmp_path)
    voz = {"provedor": "fish", "voice_id": "v"}
    for _ in range(2):
        previsao_narracao.anotar(voz, 1000, 0.001)
    monkeypatch.setattr(previsao_narracao.threading, "Timer",
                        lambda t, f, args=(): SimpleNamespace(daemon=True, start=lambda: f(*args), cancel=lambda: None))
    linhas = []
    previsao_narracao.vigiar(voz, 1000, linhas.append)
    assert any("passou do normal" in l for l in linhas)


# ------------------------------------------------------------------ outra rota do garimpo


def test_video_que_nao_toca_fora_tenta_outros_clientes(tmp_path, monkeypatch):
    chamadas = []

    def rodar(comando, prazo):
        chamadas.append(comando)
        if len(chamadas) == 1:
            return 1, "ERROR: [youtube] x: Playback on other websites has been disabled by the video owner", ""
        return 0, "", "Canal\n"
    monkeypatch.setattr(garimpo, "_rodar_com_prazo", rodar)
    codigo, _, saida = garimpo._baixar_por_rotas({"id": "x", "arquivo": "u", "yt_duracao": 300}, tmp_path / "t.mp4",
                                                 10, 20, None, 60, log=lambda *_: None)
    assert codigo == 0 and len(chamadas) == 2
    assert "youtube:player_client=" + garimpo.OUTROS_CLIENTES in chamadas[1]


def test_outra_rota_falhando_baixa_inteiro_e_corta_aqui(tmp_path, monkeypatch):
    chamadas, cortes = [], []

    def rodar(comando, prazo):
        chamadas.append(comando)
        if "--download-sections" in comando:
            return 1, "ERROR: ffmpeg exited with code 1", ""
        saida = Path(comando[comando.index("-o") + 1].replace("%(ext)s", "mp4"))
        saida.write_bytes(b"x")
        return 0, "", "Canal\n"
    monkeypatch.setattr(garimpo, "_rodar_com_prazo", rodar)
    monkeypatch.setattr(garimpo, "_cortar_aqui", lambda inteiro, destino, ini, fim: cortes.append((ini, fim)))
    codigo, _, _ = garimpo._baixar_por_rotas({"id": "x", "arquivo": "u", "yt_duracao": 300}, tmp_path / "t.mp4",
                                             10, 20, None, 60, log=lambda *_: None)
    assert codigo == 0 and cortes == [(10, 20)] and len(chamadas) == 3
    assert not list(tmp_path.glob("*.inteiro.*"))  # o vídeo inteiro não fica no disco


@pytest.mark.parametrize("erro", ["ERROR: [youtube] x: Private video. Sign in if you've been granted access",
                                  "ERROR: [youtube] x: Video unavailable. This video has been removed by the uploader",
                                  "ERROR: Sign in to confirm you're not a bot"])
def test_sem_rota_nao_insiste(tmp_path, monkeypatch, erro):
    chamadas = []
    monkeypatch.setattr(garimpo, "_rodar_com_prazo", lambda c, p: (chamadas.append(c), (1, erro, ""))[1])
    codigo, _, _ = garimpo._baixar_por_rotas({"id": "x", "arquivo": "u", "yt_duracao": 300}, tmp_path / "t.mp4",
                                             10, 20, None, 60, log=lambda *_: None)
    assert codigo == 1 and len(chamadas) == 1


def test_video_longo_nao_vem_inteiro(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(garimpo, "_rodar_com_prazo",
                        lambda c, p: (chamadas.append(c), (1, "ERROR: Requested format is not available", ""))[1])
    garimpo._baixar_por_rotas({"id": "x", "arquivo": "u", "yt_duracao": 3600}, tmp_path / "t.mp4", 10, 20, None, 60,
                              log=lambda *_: None)
    assert len(chamadas) == 2


# ------------------------------------------------------------------ tema: som e trilha


def test_tema_investigacao_som_e_clima():
    projeto = _projeto(estilo={"tema": "investigacao"})
    assert animacoes.tema(projeto) == "investigacao"
    estilo = animacoes._estilo(projeto)
    assert estilo["destaque"] == animacoes.TEMAS["investigacao"]["destaque"] and "desenho" in estilo
    assert animacoes.SOM_DO_TEMA["investigacao"] == "papel"
    assert trilha._clima_do_tema(projeto) == "misterio"
    assert animacoes.tema(_projeto(estilo={"tema": "nao-existe"})) == ""


def test_trilha_sem_modelo_parte_do_clima_do_tema():
    bloco = {"id": 1, "ini": 0.0, "fim": 30.0}
    assert trilha._secao_valida({}, bloco, None, "tensao")["clima"] == "tensao"
    assert trilha._secao_valida({}, bloco, None)["clima"] == "misterio"
    assert "tensao" in trilha._pedido([{"id": 1, "ini": 0, "fim": 30, "nome": "", "textos": ["oi"]}], "tensao")


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="sem ffmpeg")
@pytest.mark.parametrize("nome", ["papel", "bipe", "grave"])
def test_sons_novos_sao_feitos(nome, tmp_path, monkeypatch):
    from fabrica import camadas
    monkeypatch.setattr(camadas, "PASTA", tmp_path)
    arquivo = camadas.som(nome)
    assert arquivo.exists() and arquivo.stat().st_size > 1000
