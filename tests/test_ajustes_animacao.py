"""Os ajustes das animações que a pessoa escolhe na página Animações do Radar (fabrica/ajustes_animacao.py). Sem rede."""
from types import SimpleNamespace

import pytest

from fabrica import ajustes_animacao as x
from fabrica import animacoes, animation_ai as a
from fabrica import api


def projeto(animation_ai=None, config=None, tmp=None):
    return SimpleNamespace(config=config or {}, perfil={"animation_ai": animation_ai} if animation_ai else {},
                           offline=False, pasta=tmp)


def test_limpar_devolve_o_conjunto_inteiro():
    # um estilo novo por cima de um canal com cores próprias não pode herdar as cores do outro
    assert x.limpar({"tema": "neon"}) == {"ativo": True, "tema": "neon", "cores": {}, "fontes": {}, "fundo": "foto",
                                          "tipos_fora": []}


@pytest.mark.parametrize("ruim", [
    {"tema": "nao-existe"}, {"cores": {"acc": "vermelho"}}, {"cores": {"acc": "#FFF"}},
    {"cores": {"acc": "#000000;background:url(x)"}}, {"cores": {"painel": "#000000"}},
    {"fontes": {"texto": "Comic Sans"}}, {"fontes": {"outra": "Inter"}}, {"fundo": "video"},
    {"tipos_fora": ["nao-existe"]}, "texto",
])
def test_limpar_recusa_o_que_nao_existe(ruim):
    with pytest.raises(x.AjusteInvalido):
        x.limpar(ruim)


def test_nao_deixa_desligar_todas_sem_dizer_sem_animacoes():
    with pytest.raises(x.AjusteInvalido):
        x.limpar({"tema": "apple", "tipos_fora": list(a.DE_COMPLEMENTO)})
    assert x.limpar({"ativo": False, "tipos_fora": list(a.DE_COMPLEMENTO)})["ativo"] is False


def test_sem_ajuste_o_tema_fica_igual():
    # a assinatura de um clipe já gravado sai das cores: sem ajuste, nada pode mudar nem ganhar chave nova
    for nome, base in a.TEMAS.items():
        assert x.aplicar(base, {"tema": nome}) == base
        assert a.tema(projeto({"tema": nome})) == base


def test_trocar_o_fundo_leva_junto_os_tons_que_saem_dele():
    cores = x.aplicar(a.TEMAS["noite"], {"cores": {"fundo": "#F2F2F2", "txt": "#111111"}})
    assert cores["painel"] != a.TEMAS["noite"]["painel"]
    assert x.contraste(cores["txt2"], cores["fundo"]) > 4.5
    assert x.contraste(cores["txt"], cores["painel"]) > 4.5


def test_a_cor_do_destaque_escolhe_a_tinta_legivel():
    claro = x.aplicar(a.TEMAS["noite"], {"cores": {"acc": "#FFE600"}})
    escuro = x.aplicar(a.TEMAS["noite"], {"cores": {"acc": "#101040"}})
    assert x.contraste(claro["tinta"], "#FFE600") > 4.5
    assert x.contraste(escuro["tinta"], "#101040") > 4.5


def test_animacao_desligada_nao_chega_ao_modelo():
    p = projeto({"tema": "apple", "tipos_fora": ["lista", "barras"]})
    tipos = a.tipos_do_tema(p)
    assert "lista" not in tipos and "barras" not in tipos and "numero" in tipos
    assert "lista" not in a.tipos_do_tema(p, a.COMO_MOTION)
    assert "- lista:" not in a.instrucoes({"lista"}) and "- numero:" in a.instrucoes({"lista"})


def test_sem_ajuste_os_tipos_seguem_os_de_sempre():
    assert a.tipos_do_tema(projeto({"tema": "apple"})) == a.DE_COMPLEMENTO
    assert a.tipos_do_tema(projeto({"tema": "impacto"})) == [t for t in a.DE_COMPLEMENTO if t in a.TIPOS_IMPACTO]


def test_lista_vazia_nao_vira_o_catalogo_inteiro(tmp_path):
    # tudo o que caberia foi desligado: não pergunta ao modelo, e não devolve o catálogo inteiro por engano
    p = projeto({"tema": "apple", "tipos_fora": list(a.DE_COMPLEMENTO)}, tmp=tmp_path)
    assert a.tipos_do_tema(p) == []
    assert a.decidir(p, [{"id": 1, "fala": "x", "extras": []}], print, []) == {}


def test_a_camada_segue_os_ajustes():
    p = projeto({"cores": {"acc": "#112233", "txt": "#445566"}, "fontes": {"texto": "Poppins"}})
    estilo = animacoes._estilo(p)
    assert estilo["destaque"] == "#112233" and estilo["texto"] == "#445566" and estilo["_fonte_texto"] == "Poppins"
    pagina = animacoes._montar_html({"css": "", "html": "", "js": ""}, 3, 1920, 1080, estilo)
    assert "Poppins-Bold.ttf" in pagina and "--_fonte" not in pagina
    assert animacoes._estilo(projeto()) == animacoes.ESTILO_PADRAO


def test_sem_animacoes_desliga_as_duas():
    p = projeto({"ativo": False}, config={"animacoes": {"ativo": True}, "animation_ai": {"ativo": True}})
    assert animacoes.config(p)["ativo"] is False
    assert a.ligado(p) is False


def test_modelo_da_camada_so_sai_com_todos_os_nomes_dele_fora():
    assert x.modelos_fora({"tipos_fora": ["passos"]}) == set()   # o fluxo também serve à causa e consequência
    assert x.modelos_fora({"tipos_fora": ["passos", "causa_efeito", "lista"]}) == {"fluxo", "lista"}


def test_letras_de_sempre_sem_escolha():
    css = x.css_das_fontes({})
    assert 'font-family: "Titulo"; src: url("assets/fontes/PlayfairDisplay.ttf"); font-weight: 400 900;' in css
    assert 'font-family: "Texto"; src: url("assets/fontes/Inter.ttf"); font-weight: 100 900;' in css


def test_toda_letra_tem_arquivo_e_licenca():
    for nome, fonte in x.FONTES.items():
        for arquivo, _ in fonte["arquivos"]:
            assert (x.PASTA_FONTES / arquivo).exists(), arquivo
        assert (x.PASTA_FONTES / f"OFL-{nome.replace(' ', '')}.txt").exists(), nome


def test_copia_so_a_letra_escolhida(tmp_path):
    x.copiar_fontes(tmp_path, {"_fonte_texto": "Poppins"})
    assert sorted(f.name for f in (tmp_path / "assets" / "fontes").iterdir()) == ["Poppins-Bold.ttf", "Poppins-Medium.ttf",
                                                                                  "Poppins-Regular.ttf"]


@pytest.mark.parametrize("nome", ["../../.env", "..\\.env", "OFL-Inter.txt", "nada.ttf"])
def test_rota_da_letra_so_entrega_as_da_lista(nome):
    assert x.arquivo_de_fonte(nome) is None


def test_previa_toca_ou_para_e_usa_o_endereco_da_letra():
    tocando = x.previa({"tema": "neon", "fontes": {"texto": "Poppins"}}, "lista")
    assert "tl.play(0)" in tocando and "/api/animacoes/fonte/Poppins-Bold.ttf" in tocando
    assert 'url("assets/' not in tocando
    assert "window.quadro(4.20)" in x.previa({"tema": "apple"}, "numero", 4.2)


def test_previa_de_animacao_que_o_estilo_nao_tem_cai_no_numero():
    assert '"tipo": "numero"' in x.previa({"tema": "impacto"}, "barras")


def test_fundo_so_cor_nao_leva_foto_de_exemplo():
    assert "fundo" not in x._exemplo("numero", x.limpar({"tema": "apple", "fundo": "cor"}), 6.0)
    assert x._exemplo("numero", x.limpar({"tema": "apple"}), 6.0)["fundo"].startswith("data:image/svg")


def test_catalogo_so_oferece_o_que_o_estilo_tem():
    cat = x.catalogo()
    impacto = next(t for t in cat["temas"] if t["id"] == "impacto")
    assert "barras" not in impacto["tipos"] and "numero" in impacto["tipos"]
    assert {t["id"] for t in cat["temas"]} == set(a.TEMAS)      # estilo novo sem nome na página reprova aqui
    assert all(t in x.TIPOS_INFO for t in a.COMO_MOTION)        # animação nova sem nome também
    assert all(t in a.EXEMPLOS for t in a.COMO_MOTION)          # e sem exemplo não teria prévia


def test_erro_da_conferencia_em_palavras():
    erro = 'contrast_aa_failure em 0.33s no div ("Seu canal"): Contrast is 2.04:1; WCAG AA requires 3:1.'
    assert x._em_palavras(erro) == 'Texto difícil de ler em "Seu canal" (contraste 2.04, o mínimo é 3).'


# --------------------------------------------------------------------------------------- o canal e o projeto

@pytest.fixture
def perfis(tmp_path, monkeypatch):
    (tmp_path / "perfis").mkdir()
    monkeypatch.setattr(api, "RAIZ", tmp_path)
    return tmp_path / "perfis"


def test_salvar_no_canal_guarda_o_resto(perfis):
    arquivo = perfis / "canal-teste.yaml"
    arquivo.write_text('# cabeçalho do canal\nbase: documentario.yaml\nnome: "Teste"\nvoz:\n  voice_id: abc\n', encoding="utf-8")
    api.animacoes_do_canal_salvar(api.AnimacaoDoCanalPayload(perfil="canal-teste", ajustes={"tema": "neon"}))
    texto = arquivo.read_text(encoding="utf-8")
    assert texto.startswith("# cabeçalho do canal\n")
    assert "voice_id: abc" in texto and "tema: neon" in texto
    assert api.animacoes_do_canal("canal-teste")["ajustes"]["tema"] == "neon"


def test_perfil_de_base_nao_recebe_ajuste_de_um_canal(perfis):
    (perfis / "documentario.yaml").write_text("nome: x\n", encoding="utf-8")
    with pytest.raises(api.HTTPException):
        api.animacoes_do_canal_salvar(api.AnimacaoDoCanalPayload(perfil="documentario", ajustes={"tema": "neon"}))
    assert (perfis / "documentario.yaml").read_text(encoding="utf-8") == "nome: x\n"


def test_o_ajuste_do_video_vale_por_cima_do_canal(tmp_path, monkeypatch):
    import json

    from fabrica import projeto as modulo

    monkeypatch.setattr(modulo, "PROJETOS", tmp_path)
    perfil = tmp_path / "perfil.yaml"
    perfil.write_text("animation_ai:\n  tema: cinema\n  canal: Meu canal\n", encoding="utf-8")
    pasta = tmp_path / "video"
    pasta.mkdir()
    (pasta / "projeto.json").write_text(json.dumps({"nome": "video", "perfil": str(perfil), "offline": False,
                                                    "animation_ai_override": x.limpar({"tema": "neon"})}), encoding="utf-8")
    p = modulo.Projeto("video")
    cfg = a.config(p)
    assert cfg["tema"] == "neon"
    assert cfg["canal"] == "Meu canal"   # o que o vídeo não mexe segue vindo do canal
