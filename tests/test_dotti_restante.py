"""O que faltava da Dotti na última conferência (2026-11-22): a música própria de cada tema, os capítulos nas tags e o
atlas maior, em mais línguas. Sem rede e sem modelo."""
import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fabrica import lugares, publicacao, trilha  # noqa: E402


def _secao():
    return trilha._secao_valida({"clima": "tensao", "intensidade": 3, "pulso": False, "andamento": 100},
                                {"id": 1, "ini": 0, "fim": 6}, None)


def test_cada_tema_tem_a_sua_musica():
    for tema, m in trilha.MUSICA_DO_TEMA.items():
        s = trilha.com_musica_do_tema(tema, [_secao(), _secao()])
        assert {x["tonalidade"] for x in s} == {m["tonalidade"]}  # o mesmo tom no vídeo inteiro
        assert all(m["andamento"][0] <= x["andamento"] <= m["andamento"][1] for x in s)
        assert s[0]["timbre"] in trilha.TIMBRES and s[0]["tonalidade"] in trilha.NOTAS
    assert trilha.com_musica_do_tema("", [_secao()]) == [_secao()]  # sem tema, a partitura fica como veio
    assert trilha.com_musica_do_tema("terror", [_secao()])[0]["pulso"] is True


@pytest.mark.parametrize("tema", ["terror", "hacker", "investigacao", "cinema"])
def test_o_timbre_do_tema_toca(tema):
    s = trilha.com_musica_do_tema(tema, [_secao()])[0]
    tocado = trilha._tocar_secao(np, s, 0.0, random.Random(1))
    canal = np.asarray(tocado[0] if isinstance(tocado, tuple) else tocado)
    assert canal.size and float(np.abs(canal).max()) > 0.05


def test_capitulos_entram_nas_tags_sem_os_genericos():
    tags = publicacao.tags_com_capitulos(["tesla", "elon musk"],
                                         ["Introdução", "The Showroom Story", "Elon Musk", "O império, construído"])
    assert tags == ["tesla", "elon musk", "the showroom story", "o império construído"]
    longas = publicacao.tags_com_capitulos(["x" * 470], ["um capítulo comprido"])
    assert sum(len(t) + 1 for t in longas) < publicacao.TAGS_MAXIMO


@pytest.mark.parametrize("nome,esperado", [("Allemagne", "Germany"), ("München", "Munich"), ("Firenze", "Florence"),
                                           ("Cracóvia", "Kraków"), ("Cataratas do Iguaçu", "Iguazu Falls"),
                                           ("Torre Eiffel", "Eiffel Tower"), ("Mar Vermelho", "Red Sea")])
def test_atlas_em_mais_linguas(nome, esperado):
    assert lugares.achar(nome)["nome"] == esperado


def test_atlas_maior_e_sem_palavra_comum_virando_lugar():
    assert len(lugares.LUGARES) >= 800
    assert lugares.lugares_no_texto("Nice try, but no.") == []
    assert lugares.lugares_no_texto("Natal é a melhor época do ano.") == []
    assert [l["nome"] for l in lugares.lugares_no_texto("Ele voltou para Natal.")] == ["Natal"]


# ------------------------------------------------------------------ os sons gravados (Kenney, CC0)


def test_sons_gravados_existem_com_a_licenca():
    from fabrica import camadas
    for nome in camadas.GRAVADOS:
        assert camadas._gravado(nome, 0) is not None, nome
    for pacote in {g[0] for g in camadas.GRAVADOS.values()}:
        assert "CC0" in (camadas.GRAVADOS_PASTA / pacote / "License.txt").read_text(encoding="utf-8", errors="ignore")


def test_gravado_varia_e_cai_no_ffmpeg_sem_arquivo(tmp_path, monkeypatch):
    from fabrica import camadas
    assert camadas._gravado("carimbo", 0) != camadas._gravado("carimbo", 1)
    assert camadas._gravado("carimbo", 5) == camadas._gravado("carimbo", 0)  # volta ao começo depois da última
    assert camadas._gravado("papel", 0) is None  # sem gravação: o som feito pelo ffmpeg
    monkeypatch.setattr(camadas, "GRAVADOS_PASTA", tmp_path / "nada")
    assert camadas._gravado("carimbo", 0) is None


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="sem ffmpeg")
def test_som_gravado_vira_wav(tmp_path, monkeypatch):
    from fabrica import camadas
    monkeypatch.setattr(camadas, "PASTA", tmp_path)
    arquivo = camadas.som("sino", 2)
    assert "gravado" in arquivo.name and arquivo.suffix == ".wav" and arquivo.stat().st_size > 1000
