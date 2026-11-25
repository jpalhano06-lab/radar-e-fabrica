"""A segunda passada do estudo da Dotti (2026-11-22): as formas novas de animação, o atlas do mapa-múndi, as famílias
que a fábrica acha sozinha na fala, os sons por evento, as palavras funcionais e as transições de luz. Sem rede e sem
modelo."""
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fabrica import animacoes, animacoes_achar, animacoes_formas, animacoes_modelos, animation_ai, lugares  # noqa: E402

T = lambda texto, t: {"texto": texto, "t": t}  # noqa: E731
TEMPOS = [x / 10 for x in range(60)]


# ------------------------------------------------------------------ o atlas


def test_atlas_acha_nas_tres_linguas_e_mede_a_distancia():
    assert lugares.achar("Xangai")["nome"] == "Shanghai"
    assert lugares.achar("Alemanha") is lugares.achar("Germany") is lugares.achar("Alemania")
    km = lugares.distancia_km(lugares.achar("Shanghai"), lugares.achar("Berlin"))
    assert 8300 < km < 8500


@pytest.mark.parametrize("texto,esperado", [
    ("Tesla opened a factory in Shanghai and another in Berlin.", ["Shanghai", "Berlin"]),
    ("Ele foi para a Turquia e depois para o Japão.", ["Turkey", "Japan"]),
    ("El viaje de Madrid a Ciudad de México", ["Madrid", "Mexico City"]),
    ("they moved to China in 1990", ["China"]),
    ("China plates and a roast turkey", []),          # louça e peru não são lugar
    ("Turkey is a bird people eat.", []),              # nome ambíguo sem preposição de lugar
])
def test_lugares_no_texto(texto, esperado):
    assert [l["nome"] for l in lugares.lugares_no_texto(texto)] == esperado


def test_arco_vai_de_um_lugar_ao_outro():
    a, b = lugares.achar("New York"), lugares.achar("London")
    arco = lugares.arco(a, b)
    assert arco[0] == pytest.approx((a["lat"], a["lon"]), abs=0.01)
    assert arco[-1] == pytest.approx((b["lat"], b["lon"]), abs=0.01)
    assert max(la for la, _ in arco) > max(a["lat"], b["lat"])  # o caminho mais curto sobe para o norte


# ------------------------------------------------------------------ as formas


EXEMPLOS = {
    "secao": {"titulo": T("The Showroom Story", 0.4), "numero": 2},
    "nome": {"nome": T("Elon Musk", 0.3), "cargo": T("CEO", 0.8)},
    "data": {"data": T("1984", 0.4), "variante": "canto"},
    "termo": {"termo": T("short selling", 0.3), "explicacao": T("apostar na queda", 1.0)},
    "pergunta": {"pergunta": T("why did nobody notice", 0.3)},
    "impacto": {"palavra": T("Zero", 0.3)},
    "karaoke": {"palavras": [T(w, 0.3 + 0.2 * i) for i, w in enumerate("and nobody saw it coming".split())]},
    "rede": {"centro": T("Tesla", 0.2), "nos": [T("SpaceX", 0.6), T("Twitter", 1.0), T("Neuralink", 1.4)]},
    "ticker": {"manchete": T("Tesla stock falls", 0.3), "itens": [T("Sales drop", 0.8)]},
    "quiz": {"pergunta": T("Which sold more?", 0.2), "opcoes": [T("Model Y", 0.8), T("Corolla", 1.2)],
             "certa": {"indice": 0, "t": 2.0}},
    "teaser": {"titulo": T("The Showroom Story", 0.3)},
    "chamada": {"texto": T("subscribe", 0.3)},
    "carrossel": {"itens": [T("Model S", 0.3), T("Model 3", 0.9)]},
    "foto": {"legenda": T("Gigafactory", 0.6), "variante": "detalhe"},
    "provas": {"variante": "recibo", "itens": [{**T("Jet", 0.4), "valor": "US$ 40 mi"}, T("Yacht", 0.9)],
               "total": T("US$ 160 mi", 1.6)},
    "mapa_mundi": {"lugares": [T("Shanghai", 0.3), T("Berlin", 1.2)], "rota": True},
}


def test_todas_as_formas_novas_estao_no_catalogo():
    assert set(EXEMPLOS) == set(animacoes_formas.MODELOS)
    for nome in EXEMPLOS:
        assert nome in animacoes_modelos.MODELOS and f"- {nome}:" in animacoes_modelos.CATALOGO
        assert nome in animacoes.ESQUEMA["properties"]["modelo"]["enum"]


@pytest.mark.parametrize("modelo", list(EXEMPLOS))
def test_cada_forma_confere_e_desenha(modelo):
    fala = "and nobody saw it coming why did nobody notice short selling zero"
    dados, erros = animacoes_modelos.conferir_dados(modelo, {**EXEMPLOS[modelo], "_lingua": "en"}, 5.0, TEMPOS, fala)
    assert not erros, erros
    partes = animacoes_modelos.partes(modelo, dados, 5.0)
    assert partes["html"].startswith('<div id="fx-area">') and "tl." in partes["js"]


def test_rotulos_saem_na_lingua_do_video_e_caem_no_ingles():
    css, html, js = animacoes_formas.secao({"titulo": T("A virada", 0.2), "numero": 3, "_lingua": "pt"}, 4)
    assert "CAPÍTULO 3" in html
    assert "CHAPTER" in animacoes_formas.secao({"titulo": T("X", 0.2), "_lingua": "xx"}, 4)[1]
    assert animacoes_formas.falta_rotulo("xx") and not animacoes_formas.falta_rotulo("es")


def test_formas_de_canto_nao_escurecem_o_video():
    for modelo in ("nome", "teaser", "chamada", "ticker"):
        dados, _ = animacoes_modelos.conferir_dados(modelo, {**EXEMPLOS[modelo], "_lingua": "en"}, 5.0, TEMPOS, "")
        assert "#veu { visibility: hidden; }" in animacoes_modelos.partes(modelo, dados, 5.0)["css"]


def test_mapa_mundi_acha_o_lugar_e_calcula_a_distancia():
    dados, erros = animacoes_modelos.conferir_dados("mapa_mundi", {**EXEMPLOS["mapa_mundi"], "_lingua": "pt"}, 5.0,
                                                    TEMPOS, "")
    assert not erros and dados["lugares"][0]["lat"] == pytest.approx(31.23)
    assert dados["_distancia"] == "≈ 8.400 km"
    _, erros = animacoes_modelos.conferir_dados("mapa_mundi", {"lugares": [T("Atlantida", 0.2)]}, 5.0, TEMPOS, "")
    assert erros and "atlas" in erros[0]


def test_karaoke_e_impacto_recusam_palavra_inventada():
    _, erros = animacoes_modelos.conferir_dados("impacto", {"palavra": T("Colapso", 0.2)}, 5.0, TEMPOS, "it failed")
    assert erros
    _, erros = animacoes_modelos.conferir_dados("data", {"data": T("mil e novecentos", 0.2)}, 5.0, TEMPOS, "")
    assert erros  # a data vai em algarismos


def test_as_chaves_da_fabrica_nao_contam_como_texto_da_tela():
    textos = animacoes._textos_dos_dados({"legenda": T("Berlin", 0.2), "_imagens": ["assets/fotos/0.jpg"],
                                          "_lingua": "en", "variante": "polaroid"})
    assert textos == ["Berlin"]


# ------------------------------------------------------------------ as famílias achadas na fala


@pytest.mark.parametrize("texto,lingua,esperado", [
    ("It all started in nineteen eighty-four.", "en", "nineteen eighty-four"),
    ("Tudo começou em mil novecentos e trinta e cinco.", "pt", "mil novecentos e trinta e cinco"),
    ("Fundada en dos mil ocho.", "es", "dos mil ocho"),
    ("Founded in 2003.", "en", "2003"),
    ("Custou dois mil reais.", "pt", ""),
    ("He has two thousand fans.", "en", ""),
])
def test_ano(texto, lingua, esperado):
    assert animacoes_achar.ano(texto, lingua) == esperado


def test_termo_nome_pergunta_impacto():
    assert animacoes_achar.termo("a practice known as short selling, which", "en") == "short selling"
    assert animacoes_achar.termo("o que se chama de efeito manada.", "pt") == "efeito manada"
    assert animacoes_achar.nomes("Then General Motors and Elon Musk met.", "en") == ["General Motors", "Elon Musk"]
    assert animacoes_achar.nomes("They opened in New York City.", "en") == []  # lugar vira mapa, não nome
    assert animacoes_achar.pergunta("But who pays for it? Nobody knows.") == "But who pays for it?"
    assert animacoes_achar.impacto("Nobody knows.", "en") == "Nobody knows"
    assert animacoes_achar.impacto("So.", "en") == ""
    assert animacoes_achar.impacto("floor. Then it fell", "en", comeca_frase=False) == ""  # pedaço da frase anterior


def _cena(n, ini, texto, bloco=1, **extra):
    return {"n": n, "ini": ini, "fim": ini + 4, "texto": texto, "bloco": bloco, **extra}


def test_candidatas_uma_por_cena_na_familia_mais_forte():
    mapa = {"blocos": [{"id": 1, "nome": "Abertura"}, {"id": 2, "nome": "The Showroom Story"}]}
    cenas = [_cena(1, 0, "It began in nineteen eighty-four in Detroit."),
             _cena(2, 100, "Walk into a store in Berlin.", bloco=2),
             _cena(3, 110, "Elon Musk said it was easy."),
             _cena(4, 120, "Why did nobody notice?"),
             _cena(5, 130, "Subscribe for more.")]
    achadas = {c["n"]: familia for c, familia, _, _ in animacoes_achar.candidatas(cenas, "en", mapa)}
    assert achadas == {1: "mapa_mundi", 2: "secao", 3: "nome", 4: "pergunta", 5: "chamada"}
    sem = {c["n"]: f for c, f, *_ in animacoes_achar.candidatas(cenas, "en", mapa, desligadas={"secao", "chamada"})}
    assert sem[2] == "mapa_mundi"  # sem a seção, a cena 2 vira o mapa de Berlim
    assert sem[5] == "impacto"     # e "Subscribe for more." sem a chamada é só uma frase curta


def test_secao_no_maximo_uma_a_cada_noventa_segundos():
    mapa = {"blocos": [{"id": i, "nome": f"Parte {i}"} for i in range(1, 6)]}
    cenas = [_cena(i, i * 40.0, "Then it continued", bloco=i + 1) for i in range(5)]
    secoes = [c["ini"] for c, f, *_ in animacoes_achar.candidatas(cenas, "en", mapa) if f == "secao"]
    assert all(b - a >= animacoes_achar.SECAO_A_CADA for a, b in zip(secoes, secoes[1:]))


def test_familia_vale_no_ritmo(monkeypatch):
    monkeypatch.setattr(animacoes, "_ancorar", lambda projeto, item, pela_fala=False: {"ini": item["ini"],
                                                                                      "fim": item["fim"]})
    projeto = SimpleNamespace(config={"animacoes": {}}, perfil={})
    secao = {"id": "a", "c_ini": 1, "ini": 10, "fim": 13, "automatico": True, "familia": "secao"}
    diagrama = {"id": "b", "c_ini": 2, "ini": 14, "fim": 17, "visual": "diagrama"}
    impacto = {"id": "c", "c_ini": 3, "ini": 30, "fim": 32, "automatico": True, "familia": "impacto"}
    numero = {"id": "d", "c_ini": 4, "ini": 33, "fim": 35, "automatico": True, "familia": "numero"}
    ficam = animacoes.espacar(projeto, [secao, diagrama, impacto, numero], [])
    assert [i["id"] for i in ficam] == ["a", "d"]  # a seção ganha do diagrama; o número ganha do impacto


# ------------------------------------------------------------------ sons, palavras e transições


def test_eventos_de_som_por_forma():
    eventos = animacoes_formas.eventos_de_som("chamada", {"texto": T("subscribe", 0.5)})
    assert [s for _, s, _ in eventos] == ["clique", "sino"]
    assert animacoes_formas.eventos_de_som("data", {"data": T("1984", 1.0)})[0][1:] == ("carimbo", "forte")
    assert animacoes_formas.eventos_de_som("frase", {}) == []  # os modelos antigos seguem com um som só
    assert set(animacoes.NIVEL_DO_SOM) == {"forte", "medio", "suave"}


def test_palavras_funcionais_nas_tres_linguas():
    assert animacoes_achar.funcional("with", "en") and animacoes_achar.funcional("desde", "es")
    assert animacoes_achar.funcional("também", "pt")
    assert not animation_ai._inventadas(["sales with growth"], "growth of sales")


def test_transicao_de_luz_entra_no_render():
    from fabrica import render
    projeto = SimpleNamespace(config={}, perfil={"transicao": "queima", "camada": "douradas"})
    cfg = render.configuracao(projeto)
    assert cfg["transicao"] == "queima" and cfg["camada"] == "douradas"
    assert render._com_transicao("null", cfg, 90, 30) == "null"  # a luz não é um fade de cor


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="sem ffmpeg")
@pytest.mark.parametrize("nome", ["carimbo", "maquina", "slam", "clique", "sino", "foto", "ping", "tecla"])
def test_sons_por_evento_sao_feitos(nome, tmp_path, monkeypatch):
    from fabrica import camadas
    monkeypatch.setattr(camadas, "PASTA", tmp_path)
    assert camadas.som(nome).stat().st_size > 1000


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="sem ffmpeg")
def test_transicao_e_laco_novos_sao_feitos(tmp_path, monkeypatch):
    from fabrica import camadas
    monkeypatch.setattr(camadas, "PASTA", tmp_path)
    monkeypatch.setattr(camadas, "SEGUNDOS", 1)
    assert camadas.transicao("derreter").stat().st_size > 1000
    assert camadas.laco("vazando").stat().st_size > 1000
