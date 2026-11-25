"""A língua que o Radar grava no projeto.json manda na tela (2026-11-20).

Pelo texto a fábrica só reconhecia pt, en, es, ja e ko: dois vídeos de teste em holandês saíram com os textos da tela
pedidos em inglês, e um vídeo em francês ou alemão cairia em português."""
from types import SimpleNamespace

from fabrica import idioma, openrouter_local


def _projeto(tmp_path, texto, dados=None, voz=None):
    (tmp_path / "roteiro.txt").write_text(texto, encoding="utf-8")
    return SimpleNamespace(pasta=tmp_path, dados=dados or {}, perfil={"voz": voz or {}})


HOLANDES = "De ringen van Saturnus verdwijnen langzaam. Het is een van de mooiste dingen die je ooit zult zien. " * 10


def test_a_lingua_declarada_vale_primeiro(tmp_path):
    p = _projeto(tmp_path, HOLANDES, {"lingua": "nl"})
    assert idioma.lingua(p) == "nl"
    assert "holandês" in idioma.regra_da_tela(p)
    assert idioma.locale(p) == "nl-NL"


def test_sem_declarar_cai_na_lingua_da_voz_e_nao_em_portugues(tmp_path):
    p = _projeto(tmp_path, "Le roi a construit le temple. " * 20, voz={"idioma_da_voz": "fr"})
    assert idioma.lingua(p) == "fr"


def test_o_alfabeto_da_lingua_nao_e_apagado_da_tela(tmp_path):
    p = _projeto(tmp_path, "Кольца Сатурна исчезают. " * 20, {"lingua": "ru"})
    assert not openrouter_local._alfabeto_proibido(p).search("Кольца Сатурна")
