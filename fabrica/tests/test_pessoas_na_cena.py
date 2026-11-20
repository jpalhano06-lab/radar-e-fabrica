"""Canal de mercado com gente na tela: frase concreta mostra um comprador fazendo a ação, frase abstrata mostra uma
pessoa comum falando para a câmera.

Caso real (2026-11-09): o vídeo do Aldi da Austrália feito pelo Robô do Dotti (job_f105592b1410408e) segurou 7 min, e o
nosso do UK CartWatch (12-new-aldi-rules-coming-this-autumn-in) 3 min. Nos quadros dele, frase de explicação ("revenue
grew by 4.8%", "It's fighting harder on price") vira uma pessoa falando no carro, no sofá ou de terno; frase concreta
("You walk into ALDI with your own bags") vira a cena com gente. No nosso, a frase abstrata virava prateleira vazia.
Rode com: uv run --no-sync --with pytest python -m pytest tests
Sem rede e sem custo.
"""
from fabrica import cenas, imagens

COM_PESSOAS = {"imagens": {"pessoas": True}, "voz": {"idioma_da_voz": "en"}}
SEM_PESSOAS = {"imagens": {}, "voz": {"idioma_da_voz": "en"}}


def test_planejador_do_canal_com_pessoas_pede_gente_nas_cenas():
    sistema = cenas._sistema(COM_PESSOAS, "roteiro", 4.5, 3.0, 5.0)
    assert "Pessoas na tela" in sistema
    assert "falando para a câmera" in sistema
    assert "fazendo a ação" in sistema


def test_planejador_dos_outros_canais_nao_muda():
    assert "Pessoas na tela" not in cenas._sistema(SEM_PESSOAS, "roteiro", 4.5, 3.0, 5.0)


def test_pedido_da_imagem_pede_gente_comum_e_nao_modelo():
    cena = {"n": 1, "personagem": False, "prompt": "A shopper pushing a trolley into an Aldi store"}
    prompt = imagens.prompt_final(cena, COM_PESSOAS, False)
    assert "ordinary" in prompt and "not models" in prompt
    assert "ordinary" not in imagens.prompt_final(cena, SEM_PESSOAS, False)
