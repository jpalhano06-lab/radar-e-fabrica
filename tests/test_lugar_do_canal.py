"""A imagem do vídeo é do país do canal: texto, preço e marca de lá, e o pedido da imagem sem português.

Caso real: 12-new-aldi-rules-coming-this-autumn-in (UK CartWatch, 2026-11-09). Num vídeo para o Reino Unido apareceram
"Manta térmica elétrica" escrito na embalagem (cena 4), preços em $, € e R$ e uma placa "Liebe Kunden" de loja alemã.
Causas: (1) o pedido da imagem levava "The image must clearly show: <mostrar>", e o "mostrar" é escrito em português,
então o modelo escrevia essas palavras no produto (35 de 142 imagens); (2) o pedido nunca dizia o país (só 8 de 142
citavam UK ou £), e o modelo escolhia a moeda; (3) o Jev não sabia o país do vídeo, e foto com texto de outro país
passava (a placa alemã levou nota 86).
Rode com: uv run --no-sync --with pytest python -m pytest tests
Sem rede e sem custo.
"""
from types import SimpleNamespace

from fabrica import corrigir, imagens

UK = {"voz": {"idioma_da_voz": "en"},
      "lugar": {"pais": "the United Kingdom", "moeda": "£ (pounds sterling)"},
      "imagens": {"estilo": "Realistic documentary photo", "evitar": "watermarks"}}

CENA_4 = {"n": 4, "personagem": False, "visual": "video_real", "ia_motivo": "a foto do banco mostrava outra coisa",
          "prompt": "A hand reaching for a packaged heated throw on a low supermarket shelf",
          "sujeito": "heated throw",
          "mostrar": "Manta térmica elétrica (heated throw) em uma prateleira de supermercado"}


def test_o_pedido_da_imagem_nao_leva_o_mostrar_em_portugues():
    prompt = imagens.prompt_final(CENA_4, UK, False)
    assert "Manta" not in prompt and "prateleira" not in prompt
    assert "The image must clearly show: heated throw" in prompt


def test_o_mostrar_continua_servindo_a_conferencia():
    # corrigir usa o_que_mostrar como alvo do julgamento (em português, para o Jev): isso não muda
    assert imagens.o_que_mostrar(CENA_4) == CENA_4["mostrar"]


def test_o_pedido_da_imagem_diz_o_pais_a_moeda_e_o_idioma():
    prompt = imagens.prompt_final({**CENA_4, "ia_motivo": None}, UK, False)
    assert "the United Kingdom" in prompt
    assert "£ (pounds sterling)" in prompt
    assert "English" in prompt


def test_canal_sem_lugar_ganha_so_o_idioma():
    perfil = {"voz": {"idioma_da_voz": "es"}, "imagens": {}}
    prompt = imagens.prompt_final({**CENA_4, "ia_motivo": None}, perfil, False)
    assert "Spanish" in prompt
    assert "Setting:" not in prompt


def test_idioma_desconhecido_nao_inventa_nada():
    assert imagens.lugar_do_canal({"voz": {"idioma_da_voz": "xx"}}) is None


def test_o_jev_recebe_o_pais_do_video_e_a_pergunta_do_lugar(monkeypatch):
    from fabrica import jev_local
    visto = {}

    def decidir(projeto, nome, estado, perguntas, log=print):
        visto["estado"], visto["perguntas"] = estado, perguntas
        return {"combina": {"noul": 0.86}, "sujeito": {"noul": 0.9}, "lugar": {"noul": 0.1}}

    monkeypatch.setattr(jev_local, "decidir", decidir)
    monkeypatch.setattr(corrigir, "_bloco_da_cena_no_mapa", lambda projeto, cena: "")
    monkeypatch.setattr(corrigir, "_pessoa_da_cena", lambda projeto, cena: "")
    projeto = SimpleNamespace(perfil=UK, config={})
    cena = {"n": 1, "texto": "It's Thursday morning and the middle aisle is half picked over.", "tipo": "foto_real",
            "visual": "foto_real"}
    avaliacao = corrigir._julgar_com_jev(projeto, cena, "prateleiras com placa 'Liebe Kunden' em alemão", {}, print)
    assert "the United Kingdom" in visto["estado"]["pais_do_video"]
    assert "lugar" in visto["perguntas"]
    assert avaliacao["lugar"] == 10
    # sujeito certo (prateleiras), mas texto de outro país: a cena é trocada
    assert corrigir.errada(avaliacao)


def test_nota_alta_nao_salva_foto_de_outro_pais():
    assert corrigir.de_outro_pais({"nota": 86, "sujeito": 90, "lugar": 10})
    assert not corrigir.de_outro_pais({"nota": 86, "sujeito": 90, "lugar": 80})
    assert not corrigir.de_outro_pais({"nota": 86, "sujeito": 90})


def test_sem_pais_o_jev_nao_ganha_a_pergunta_do_lugar():
    assert "lugar" not in corrigir._perguntas({"narracao_desta_cena": "x"})
