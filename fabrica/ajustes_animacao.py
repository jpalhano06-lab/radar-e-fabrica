"""Os ajustes das animações que a pessoa escolhe antes do vídeo (a página Animações do Radar, pedido do usuário em
2026-11-07): o estilo, as cores, o fundo, as letras e quais animações podem entrar.

Valem por canal (`animation_ai` no perfil) ou só num vídeo (`animation_ai_override` no projeto.json, que `Projeto` põe
por cima do perfil). Sem ajuste nenhum, tudo sai como sempre saiu: nada aqui muda a assinatura de um clipe já gravado.

Fica de fora de propósito: quantas animações entram e os 40 s sem animação no começo, que são regras da fábrica."""
import base64
import copy
import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from .config import RAIZ, config_geral

PASTA_FONTES = Path(__file__).parent / "recursos" / "fontes"

# só fontes de licença livre (OFL), com o arquivo da licença na pasta. Nunca fontes do Windows, que não podem ir para
# os amigos. Cada arquivo diz os pesos que atende: a fonte sem peso variável não fica fina num título grosso
FONTES = {
    "Inter": {"descricao": "Moderna e limpa", "arquivos": [("Inter.ttf", "100 900")]},
    "Playfair Display": {"descricao": "Serifada, de revista", "arquivos": [("PlayfairDisplay.ttf", "400 900")]},
    "Poppins": {"descricao": "Redonda e amigável", "arquivos": [("Poppins-Regular.ttf", "100 400"),
                                                                ("Poppins-Medium.ttf", "500"),
                                                                ("Poppins-Bold.ttf", "600 900")]},
}
FONTE_TEXTO, FONTE_TITULO = "Inter", "Playfair Display"
CORES = ("fundo", "txt", "acc", "acc2")
NOME_DAS_CORES = {"fundo": "Fundo", "txt": "Texto", "acc": "Destaque", "acc2": "Segundo destaque"}
FUNDOS = {"foto": "A foto da cena atrás da animação", "cor": "Só a cor do fundo, sem foto atrás"}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

TEMAS_INFO = {
    "impacto": ("Impacto", "Foto atrás, letra gigante e a cena se montando peça por peça"),
    "apple": ("Apple", "Creme, cartões brancos e destaque azul, elegante"),
    "editorial": ("Editorial", "Papel claro, de revista"),
    "noite": ("Noite", "Azul-escuro com dourado, sóbrio"),
    "misterio": ("Mistério", "Preto com vermelho, para suspense"),
    "cinema": ("Cinema", "Filme quente, com grão e luz que vaza"),
    "neon": ("Neon", "Tela de ficção científica, ciano e magenta"),
    "riso": ("Impressão", "Papel com grão e duas tintas fora de registro"),
    "blueprint": ("Planta azul", "Papel milimetrado, de engenharia"),
}
TIPOS_INFO = {
    "numero": "Número grande", "porcentagem": "Porcentagem", "medidor": "Medidor de ponteiro", "proporcao": "Proporção",
    "barras": "Barras", "grafico_linha": "Gráfico de linha", "frase": "Frase de destaque", "pergunta": "Pergunta",
    "fato": "Fato curioso", "palavra_chave": "Palavra-chave", "citacao": "Citação", "definicao": "Definição",
    "manchete": "Manchete de jornal", "documento": "Documento", "lista": "Lista", "destaques": "Destaques",
    "checklist": "Checklist", "cartoes": "Cartões", "pilha_cartoes": "Pilha de cartões", "ranking": "Ranking",
    "passos": "Passo a passo", "comparar": "Comparação", "antes_depois": "Antes e depois",
    "deslizar": "Antes e depois com régua", "causa_efeito": "Causa e consequência", "linha_do_tempo": "Linha do tempo",
    "revelacao": "Título que se revela",
}
# o que cada animação desligada tira da camada por cima das fotos (animacoes.py), que tem modelos próprios
_CAMADA = {"frase": ("frase",), "numero": ("numero",), "comparar": ("contraste",), "lista": ("lista",),
           "linha_do_tempo": ("linha_do_tempo",), "cartoes": ("radial",), "causa_efeito": ("fluxo",),
           "passos": ("fluxo",)}


class AjusteInvalido(ValueError):
    pass


def tipos_do_estilo(tema: str) -> list:
    """As animações que existem neste estilo (o motor do impacto não tem barras nem gráfico de linha, por exemplo)."""
    from . import animation_ai as a

    impacto = a.TEMAS.get(tema, {}).get("_motor") == "impacto"
    return [t for t in a.COMO_MOTION if not impacto or t in a.TIPOS_IMPACTO]


def limpar(ajustes) -> dict:
    """Confere o que veio de fora e devolve sempre o conjunto inteiro: um estilo novo por cima de um canal com cores
    próprias não pode herdar as cores do outro. Levanta AjusteInvalido com o motivo."""
    from . import animation_ai as a

    if not isinstance(ajustes, dict):
        raise AjusteInvalido("Os ajustes das animações vieram em formato errado.")
    tema = str(ajustes.get("tema") or "impacto")
    if tema not in a.TEMAS:
        raise AjusteInvalido(f"O estilo '{tema}' não existe.")
    cores = {}
    for chave, valor in (ajustes.get("cores") or {}).items():
        if chave not in CORES:
            raise AjusteInvalido(f"A cor '{chave}' não existe.")
        if valor:
            if not _HEX.match(str(valor)):
                raise AjusteInvalido(f"A cor de {NOME_DAS_CORES[chave]} tem de ser como #FFD23F.")
            cores[chave] = str(valor).upper()
    fontes = {}
    for chave, valor in (ajustes.get("fontes") or {}).items():
        if chave not in ("texto", "titulo"):
            raise AjusteInvalido(f"A letra '{chave}' não existe.")
        if valor:
            if valor not in FONTES:
                raise AjusteInvalido(f"A letra '{valor}' não está na lista.")
            fontes[chave] = valor
    fundo = str(ajustes.get("fundo") or "foto")
    if fundo not in FUNDOS:
        raise AjusteInvalido(f"O fundo '{fundo}' não existe.")
    fora = sorted({str(t) for t in ajustes.get("tipos_fora") or []})
    desconhecidos = [t for t in fora if t not in a.CATALOGO]
    if desconhecidos:
        raise AjusteInvalido(f"Animação desconhecida: {desconhecidos[0]}.")
    ativo = ajustes.get("ativo", True) is not False
    if ativo and not [t for t in tipos_do_estilo(tema) if t in a.DE_COMPLEMENTO and t not in fora]:
        raise AjusteInvalido("Deixe ao menos uma animação ligada, ou escolha 'Sem animações'.")
    return {"ativo": ativo, "tema": tema, "cores": cores, "fontes": fontes, "fundo": fundo, "tipos_fora": fora}


# ------------------------------------------------------------------------------------------------ cores

def _rgb(cor):
    return tuple(int(cor[i:i + 2], 16) for i in (1, 3, 5))


def _mistura(a, b, parte) -> str:
    """A cor `a` com `parte` (0 a 1) da cor `b`."""
    return "#" + "".join(f"{round(x + (y - x) * parte):02X}" for x, y in zip(_rgb(a), _rgb(b)))


def luminancia(cor) -> float:
    canais = [c / 255 for c in _rgb(cor)]
    canais = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * canais[0] + 0.7152 * canais[1] + 0.0722 * canais[2]


def contraste(a, b) -> float:
    claro, escuro = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def aplicar(base: dict, cfg: dict) -> dict:
    """O tema com os ajustes por cima. Trocar o fundo ou o texto leva junto os tons que saem deles: os cartões de um
    tema escuro continuariam escuros num fundo claro, com o texto novo ilegível em cima."""
    pedidas = cfg.get("cores") or {}
    saida = {**base, **pedidas}
    fundo, txt = saida.get("fundo"), saida.get("txt")
    if ("fundo" in pedidas or "txt" in pedidas) and all(_HEX.match(str(c or "")) for c in (fundo, txt)):
        for chave, cor, parte in (("txt2", txt, .15), ("mut", txt, .3), ("painel", fundo, .08), ("painel2", fundo, .14),
                                  ("linha", fundo, .22)):
            if chave in base and chave not in pedidas:
                saida[chave] = _mistura(txt, fundo, parte) if cor == txt else _mistura(fundo, txt, parte)
    if "acc" in pedidas and "tinta" in base and "tinta" not in pedidas and _HEX.match(str(pedidas["acc"])):
        saida["tinta"] = "#111111" if luminancia(pedidas["acc"]) > 0.3 else "#FFFFFF"
    fontes = cfg.get("fontes") or {}
    for chave in ("texto", "titulo"):
        if fontes.get(chave) in FONTES:
            saida[f"_fonte_{chave}"] = fontes[chave]
    return saida


def modelos_fora(cfg: dict) -> set:
    """Os modelos da camada de animação (animacoes.py) que a pessoa desligou, pelos nomes da página."""
    fora = set(cfg.get("tipos_fora") or [])
    return {m for tipo, modelos in _CAMADA.items() if tipo in fora for m in modelos
            if all(t in fora for t, ms in _CAMADA.items() if m in ms)}


# ------------------------------------------------------------------------------------------------ letras

def _faces(familia: str, fonte: str, base: str) -> str:
    return "\n".join(f'      @font-face {{ font-family: "{familia}"; src: url("{base}{arquivo}"); font-weight: {pesos}; }}'
                     for arquivo, pesos in FONTES[fonte]["arquivos"])


def css_das_fontes(cores: dict, base: str = "assets/fontes/") -> str:
    """As duas famílias que os motores usam: "Texto" (a letra principal) e "Titulo" (a do destaque)."""
    return (_faces("Titulo", cores.get("_fonte_titulo") or FONTE_TITULO, base) + "\n"
            + _faces("Texto", cores.get("_fonte_texto") or FONTE_TEXTO, base))


def copiar_fontes(pasta, cores: dict) -> None:
    """Põe na pasta do clipe as letras escolhidas (animacoes._preparar_pasta já pôs as duas de sempre)."""
    destino = Path(pasta) / "assets" / "fontes"
    destino.mkdir(parents=True, exist_ok=True)
    for chave in ("_fonte_titulo", "_fonte_texto"):
        for arquivo, _ in FONTES.get(cores.get(chave), {}).get("arquivos", []):
            if not (destino / arquivo).exists():
                shutil.copy2(PASTA_FONTES / arquivo, destino / arquivo)


def arquivo_de_fonte(nome: str):
    """O caminho de uma fonte da lista, para a prévia; None para qualquer outro nome."""
    validos = {a for f in FONTES.values() for a, _ in f["arquivos"]}
    return PASTA_FONTES / nome if nome in validos else None


# ------------------------------------------------------------------------------------------------ o catálogo da página

def catalogo() -> dict:
    from . import animation_ai as a

    temas = []
    for chave, (nome, descricao) in TEMAS_INFO.items():
        if chave in a.TEMAS:
            temas.append({"id": chave, "nome": nome, "descricao": descricao,
                          "cores": {c: a.TEMAS[chave].get(c) for c in CORES}, "tipos": tipos_do_estilo(chave)})
    tipos = [{"id": t, "nome": TIPOS_INFO.get(t, t), "para": a.CATALOGO[t][0], "complemento": t in a.DE_COMPLEMENTO}
             for t in a.COMO_MOTION]
    return {"temas": temas, "tipos": tipos, "padrao": limpar({}),
            "fontes": [{"id": n, "descricao": f["descricao"]} for n, f in FONTES.items()],
            "fontes_padrao": {"texto": FONTE_TEXTO, "titulo": FONTE_TITULO},
            "fundos": [{"id": k, "nome": v} for k, v in FUNDOS.items()],
            "cores": [{"id": c, "nome": NOME_DAS_CORES[c]} for c in CORES]}


# ------------------------------------------------------------------------------------------------ a prévia

def _foto_de_exemplo(ceu, sol, morro, frente) -> str:
    """Uma paisagem desenhada, para a prévia mostrar onde a foto entra sem depender de foto de banco."""
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><defs><linearGradient id="c" x1="0" y1="0" '
           f'x2="0" y2="1"><stop offset="0" stop-color="{ceu}"/><stop offset="1" stop-color="{sol}"/></linearGradient>'
           f'</defs><rect width="1280" height="720" fill="url(#c)"/><circle cx="930" cy="250" r="90" fill="{sol}"/>'
           f'<path d="M0 470 L260 280 L470 430 L720 230 L1010 450 L1280 330 V720 H0Z" fill="{morro}"/>'
           f'<path d="M0 590 C300 500 560 650 840 560 S1180 520 1280 590 V720 H0Z" fill="{frente}"/></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


_FOTOS = [_foto_de_exemplo("#2E5E86", "#F2C879", "#3F6B5C", "#1F3B33"),
          _foto_de_exemplo("#5B3A73", "#F08A5D", "#6B3F5B", "#2C1F3A"),
          _foto_de_exemplo("#7FB3C8", "#F6EAC2", "#7C8F5A", "#4C5F36"),
          _foto_de_exemplo("#3B3F58", "#C7A17A", "#59503F", "#2B2822")]


def _exemplo(tipo: str, limpo: dict, dur: float) -> dict:
    from . import animation_ai as a

    dados, _ = a.resolver_tempos(tipo, copy.deepcopy(a.EXEMPLOS[tipo]), [], dur)
    if limpo["fundo"] == "foto":
        dados["fundo"] = _FOTOS[0]
    lista = [it for it in dados.get("itens") or [] if isinstance(it, dict)]
    if tipo in a.COM_FOTO_IMPACTO or tipo in a.COM_FOTO:
        for i, it in enumerate(lista):
            it["foto"] = _FOTOS[(i + 1) % len(_FOTOS)]
    for i, lado in enumerate(("esq", "dir", "antes", "depois")):
        if isinstance(dados.get(lado), dict):
            dados[lado]["foto"] = _FOTOS[(i + 1) % len(_FOTOS)]
    return dados


def previa(ajustes, tipo: str = "", parado: float | None = None) -> str:
    """A página da animação, tocando em volta (ou parada num segundo), sem gravar nada e sem gastar. O mesmo desenho
    que a gravação usa (montar_html), com uma foto de exemplo no lugar da foto da cena."""
    from . import animation_ai as a

    limpo = limpar(ajustes)
    disponiveis = tipos_do_estilo(limpo["tema"])
    tipo = tipo if tipo in disponiveis and tipo in a.EXEMPLOS else "numero"
    dur = 6.0
    cores = aplicar(a.TEMAS[limpo["tema"]], limpo)
    html = a.montar_html(tipo, _exemplo(tipo, limpo, dur), dur, cores, "Seu canal", 0)
    html = html.replace('url("assets/fontes/', 'url("/api/animacoes/fonte/')
    # window.quadro, não tl.seek: no motor.js o desenho vem do onUpdate da linha do tempo, que o seek não dispara
    comando = (f"const irPara = () => window.quadro({float(parado):.2f}); irPara();"
               "if (document.fonts && document.fonts.ready) document.fonts.ready.then(irPara);"
               if parado is not None else
               'tl.eventCallback("onComplete", () => setTimeout(() => tl.restart(), 700)); tl.play(0);')
    return html.replace("</body>", f"<script>(() => {{ const tl = window.__timelines.main; {comando} }})();</script>\n"
                                   "  </body>")


# ------------------------------------------------------------------------------------------------ a conferência

_PARA_CONFERIR = ("numero", "lista", "comparar", "frase", "linha_do_tempo", "cartoes", "passos", "citacao")
PASTA_CONFERENCIA = RAIZ / "projetos" / "_conferencia_animacoes"  # sem projeto.json: nenhuma lista de projetos a mostra


def _em_palavras(erro: str) -> str:
    """O erro do HyperFrames no português da página: a pessoa não sabe o que é contrast_aa_failure."""
    trecho = re.search(r'\("(.+?)"\)', erro)
    onde = f' em "{trecho.group(1)}"' if trecho else ""
    if "contrast" in erro:
        medida = re.search(r"Contrast is ([\d.]+)", erro)
        return f"Texto difícil de ler{onde}" + (f" (contraste {medida.group(1)}, o mínimo é 3)." if medida else ".")
    if "overflow" in erro:
        return f"Texto saindo do espaço{onde}. Tente uma letra mais estreita."
    if "overlap" in erro:
        return f"Textos um por cima do outro{onde}."
    return erro[:200]


def conferir(ajustes, quantos: int = 4) -> dict:
    """Passa estes ajustes pela mesma conferência da gravação (`hyperframes check`): a cor ou a letra que deixa o texto
    ilegível ou fora da tela reprova, e na produção essa cena voltaria para a foto sem ninguém ver. Grátis."""
    from . import animacoes, animation_ai as a

    limpo = limpar(ajustes)
    if not limpo["ativo"]:
        return {"ok": True, "conferidas": [], "problemas": []}
    if not animacoes.node_pronto():
        raise RuntimeError("Falta o Node.js 22 ou mais na fábrica para conferir.")
    tipos = [t for t in tipos_do_estilo(limpo["tema"]) if t not in limpo["tipos_fora"] and t in a.EXEMPLOS]
    escolhidas = ([t for t in _PARA_CONFERIR if t in tipos] + [t for t in tipos if t not in _PARA_CONFERIR])[:quantos]
    cores = aplicar(a.TEMAS[limpo["tema"]], limpo)
    falso = SimpleNamespace(config=config_geral(), perfil={}, offline=False)
    pasta_base = PASTA_CONFERENCIA / re.sub(r"\W+", "", json.dumps(limpo, sort_keys=True))[-60:]
    shutil.rmtree(pasta_base, ignore_errors=True)

    def um(tipo):
        pasta = pasta_base / tipo
        pasta.mkdir(parents=True, exist_ok=True)
        animacoes._preparar_pasta(pasta)
        copiar_fontes(pasta, cores)
        (pasta / "index.html").write_text(a.montar_html(tipo, _exemplo(tipo, limpo, 6.0), 6.0, cores, "", 0),
                                          encoding="utf-8")
        return tipo, animacoes._conferir(falso, pasta, clipe=True)

    try:
        with ThreadPoolExecutor(3) as executor:
            feitos = list(executor.map(um, escolhidas))
    finally:
        shutil.rmtree(pasta_base, ignore_errors=True)
    problemas = [{"tipo": t, "nome": TIPOS_INFO.get(t, t), "erro": _em_palavras(erros[0])} for t, erros in feitos if erros]
    return {"ok": not problemas, "conferidas": [TIPOS_INFO.get(t, t) for t, _ in feitos], "problemas": problemas}
