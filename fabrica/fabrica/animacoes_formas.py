"""As formas de animação que vieram do estudo da Dotti (2026-11-22), feitas do zero aqui, no mesmo jeito dos modelos de
animacoes_modelos.py: o modelo de linguagem só escolhe a forma e preenche textos curtos com o segundo de cada um, e o
design é sempre o mesmo, nas cores do tema do vídeo.

Formas: secao (título de capítulo), nome (tarja com o nome de quem ou do que a fala cita), data (o ano carimbado ou no
canto), termo (a palavra técnica digitada), pergunta, impacto (palavra gigante), karaoke (a frase com a palavra da vez
acesa), rede (ligações entre pessoas e coisas), ticker (faixa de notícias), quiz, teaser (o que vem a seguir),
chamada (inscreva-se), carrossel (várias fotos), foto (a foto do assunto em destaque), provas (quadro de provas em 4
variantes) e mapa_mundi (o lugar no mundo, com a rota e a distância de verdade, pelo atlas de lugares.py).

Nenhum texto fica fixo no desenho: os rótulos que não vêm da narração ("CAPÍTULO", "A SEGUIR", "INSCREVA-SE") saem
de ROTULOS, na língua do vídeo; a língua que falta cai no inglês, e a fábrica avisa no log.

As formas sem véu (nome, data no canto, ticker, teaser, chamada) não escurecem o vídeo: ficam num canto, por cima da
imagem, como uma tarja de telejornal.
"""
import json
import math
import re

from . import lugares as _lugares
from .animacoes_modelos import _entra, _tam, esc  # importe animacoes_modelos (ou animacoes) antes deste

SEM_VEU = "#veu { visibility: hidden; }\n"

ROTULOS = {
    "capitulo": {"en": "CHAPTER", "pt": "CAPÍTULO", "es": "CAPÍTULO", "fr": "CHAPITRE", "de": "KAPITEL",
                 "it": "CAPITOLO", "nl": "HOOFDSTUK", "pl": "ROZDZIAŁ", "sv": "KAPITEL", "da": "KAPITEL",
                 "no": "KAPITTEL", "fi": "LUKU", "tr": "BÖLÜM", "ru": "ГЛАВА", "ja": "第章", "ko": "장",
                 "zh": "章", "ar": "الفصل", "hi": "अध्याय", "id": "BAB", "ro": "CAPITOLUL", "cs": "KAPITOLA",
                 "hu": "FEJEZET", "el": "ΚΕΦΑΛΑΙΟ", "uk": "РОЗДІЛ", "vi": "CHƯƠNG", "th": "บทที่"},
    "a_seguir": {"en": "UP NEXT", "pt": "A SEGUIR", "es": "A CONTINUACIÓN", "fr": "À SUIVRE", "de": "ALS NÄCHSTES",
                 "it": "PROSSIMAMENTE", "nl": "HIERNA", "pl": "ZA CHWILĘ", "sv": "HÄRNÄST", "da": "NÆSTE",
                 "no": "NESTE", "fi": "SEURAAVAKSI", "tr": "SIRADA", "ru": "ДАЛЕЕ", "ja": "次は", "ko": "다음",
                 "zh": "接下来", "ar": "التالي", "hi": "आगे", "id": "SELANJUTNYA", "ro": "URMEAZĂ", "cs": "DÁLE",
                 "hu": "KÖVETKEZIK", "el": "ΣΤΗ ΣΥΝΕΧΕΙΑ", "uk": "ДАЛІ", "vi": "TIẾP THEO", "th": "ถัดไป"},
    "inscreva": {"en": "SUBSCRIBE", "pt": "INSCREVA-SE", "es": "SUSCRÍBETE", "fr": "ABONNEZ-VOUS", "de": "ABONNIEREN",
                 "it": "ISCRIVITI", "nl": "ABONNEREN", "pl": "SUBSKRYBUJ", "sv": "PRENUMERERA", "da": "ABONNÉR",
                 "no": "ABONNER", "fi": "TILAA", "tr": "ABONE OL", "ru": "ПОДПИСАТЬСЯ", "ja": "チャンネル登録",
                 "ko": "구독", "zh": "订阅", "ar": "اشترك", "hi": "सब्सक्राइब", "id": "SUBSCRIBE", "ro": "ABONEAZĂ-TE",
                 "cs": "ODEBÍRAT", "hu": "FELIRATKOZÁS", "el": "ΕΓΓΡΑΦΗ", "uk": "ПІДПИСАТИСЯ", "vi": "ĐĂNG KÝ",
                 "th": "ติดตาม"},
    "inscrito": {"en": "SUBSCRIBED", "pt": "INSCRITO", "es": "SUSCRITO", "fr": "ABONNÉ", "de": "ABONNIERT",
                 "it": "ISCRITTO", "nl": "GEABONNEERD", "pl": "SUBSKRYBUJESZ", "sv": "PRENUMERERAR", "da": "ABONNERER",
                 "no": "ABONNERER", "fi": "TILATTU", "tr": "ABONE OLUNDU", "ru": "ВЫ ПОДПИСАНЫ", "ja": "登録済み",
                 "ko": "구독중", "zh": "已订阅", "ar": "مشترك", "hi": "सब्सक्राइब्ड", "id": "SUBSCRIBED",
                 "ro": "ABONAT", "cs": "ODEBÍRÁTE", "hu": "FELIRATKOZVA", "el": "ΕΓΓΡΑΦΗΚΑΤΕ", "uk": "ВИ ПІДПИСАНІ",
                 "vi": "ĐÃ ĐĂNG KÝ", "th": "ติดตามแล้ว"},
    "urgente": {"en": "BREAKING", "pt": "URGENTE", "es": "ÚLTIMA HORA", "fr": "URGENT", "de": "EILMELDUNG",
                "it": "ULTIM'ORA", "nl": "BREAKING", "pl": "PILNE", "sv": "JUST NU", "da": "BREAKING",
                "no": "SISTE NYTT", "fi": "TUOREIMMAT", "tr": "SON DAKİKA", "ru": "СРОЧНО", "ja": "速報",
                "ko": "속보", "zh": "突发", "ar": "عاجل", "hi": "ब्रेकिंग", "id": "TERKINI", "ro": "ULTIMA ORĂ",
                "cs": "AKTUÁLNĚ", "hu": "FRISS", "el": "ΕΚΤΑΚΤΟ", "uk": "ТЕРМІНОВО", "vi": "NÓNG", "th": "ด่วน"},
    "prova": {"en": "EVIDENCE", "pt": "PROVA", "es": "PRUEBA", "fr": "PREUVE", "de": "BEWEIS", "it": "PROVA",
              "nl": "BEWIJS", "pl": "DOWÓD", "sv": "BEVIS", "da": "BEVIS", "no": "BEVIS", "fi": "TODISTE",
              "tr": "KANIT", "ru": "УЛИКА", "ja": "証拠", "ko": "증거", "zh": "证据", "ar": "دليل", "hi": "सबूत",
              "id": "BUKTI", "ro": "PROBĂ", "cs": "DŮKAZ", "hu": "BIZONYÍTÉK", "el": "ΤΕΚΜΗΡΙΟ", "uk": "ДОКАЗ",
              "vi": "BẰNG CHỨNG", "th": "หลักฐาน"},
    "total": {"en": "TOTAL", "pt": "TOTAL", "es": "TOTAL", "fr": "TOTAL", "de": "GESAMT", "it": "TOTALE",
              "nl": "TOTAAL", "pl": "RAZEM", "sv": "TOTALT", "da": "I ALT", "no": "TOTALT", "fi": "YHTEENSÄ",
              "tr": "TOPLAM", "ru": "ИТОГО", "ja": "合計", "ko": "합계", "zh": "合计", "ar": "المجموع",
              "hi": "कुल", "id": "TOTAL", "ro": "TOTAL", "cs": "CELKEM", "hu": "ÖSSZESEN", "el": "ΣΥΝΟΛΟ",
              "uk": "РАЗОМ", "vi": "TỔNG", "th": "รวม"},
}


def rotulo(chave: str, lingua: str) -> str:
    textos = ROTULOS[chave]
    return textos.get(str(lingua or "")[:2].lower()) or textos["en"]


def falta_rotulo(lingua: str) -> bool:
    """A língua do vídeo não tem os rótulos fixos: eles saem em inglês (a fábrica avisa no log)."""
    return str(lingua or "")[:2].lower() not in ROTULOS["capitulo"]


def _t(x):
    return float((x or {}).get("t") or 0.0)


def _palavras_html(texto, prefixo, classe):
    return "".join(f'<span id="{prefixo}{i}" class="{classe}">{esc(p)}</span>'
                   for i, p in enumerate(str(texto).split()))


# ------------------------------------------------------------------------------------------------ seção

def secao(d, dur):
    """O título do capítulo: o número pequeno, um traço que corre a tela e o título subindo palavra a palavra."""
    titulo = d["titulo"]["texto"]
    px = _tam(titulo, [(14, 128), (24, 104), (36, 84), (999, 68)])
    numero = d.get("numero")
    rot = esc(rotulo("capitulo", d.get("_lingua")) + (f" {numero}" if numero else ""))
    css = f"""
#s-caixa {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center;
           align-items: center; gap: 34px; text-align: center; }}
#s-traco {{ width: 1100px; }}
#s-titulo {{ font-family: "Titulo", serif; font-weight: 700; font-size: {px}px; line-height: 1.08; color: var(--texto);
            max-width: 1560px; display: flex; flex-wrap: wrap; justify-content: center; column-gap: 0.26em; }}
.s-p {{ display: inline-block; }}
"""
    html = (f'<div id="s-caixa"><div id="s-rotulo" class="rotulo">{rot}</div><div id="s-traco" class="traco"></div>'
            f'<div id="s-titulo">{_palavras_html(titulo, "s-p", "s-p")}</div></div>')
    t = _t(d["titulo"])
    js = [_entra("#s-rotulo", max(t - 0.25, 0), "{opacity: 0, y: -18}", 0.4),
          f'tl.fromTo("#s-traco", {{scaleX: 0}}, {{scaleX: 1, duration: 0.8, ease: "power3.inOut"}}, {max(t - 0.1, 0):.2f});']
    js += [_entra(f"#s-p{i}", t + 0.12 * i, "{opacity: 0, y: 40}", 0.5) for i in range(len(titulo.split()))]
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ nome (tarja)

def nome(d, dur):
    """A tarja do nome, embaixo à esquerda, acima da legenda: barra na cor de destaque, o nome e, se houver, o que
    ele é. variante "credito": uma linha discreta, centralizada."""
    n = d["nome"]["texto"]
    cargo = (d.get("cargo") or {}).get("texto", "")
    if d.get("variante") == "credito":
        css = SEM_VEU + """
#n2-linha { position: absolute; left: 0; right: 0; bottom: 30px; text-align: center; font-family: "Texto", sans-serif;
            font-size: 40px; font-weight: 500; color: var(--texto); text-shadow: 0 2px 12px rgba(0, 0, 0, 0.85); }
#n2-linha b { color: var(--destaque); font-weight: 700; }
"""
        html = f'<div id="n2-linha"><b>{esc(n)}</b>{" · " + esc(cargo) if cargo else ""}</div>'
        return css, html, _entra("#n2-linha", _t(d["nome"]), "{opacity: 0, y: 12}", 0.5, "power2.out")
    px = _tam(n, [(16, 66), (26, 54), (999, 44)])
    css = SEM_VEU + f"""
#n-tarja {{ position: absolute; left: 0; bottom: 20px; display: flex; align-items: stretch; gap: 0; }}
#n-barra {{ width: 12px; background: var(--destaque); transform-origin: bottom center; }}
#n-corpo {{ background: var(--painel); padding: 22px 38px 24px 30px; overflow: hidden; max-width: 1300px; }}
#n-nome {{ font-family: "Titulo", serif; font-weight: 700; font-size: {px}px; line-height: 1.05; color: var(--texto); }}
#n-cargo {{ margin-top: 8px; font-family: "Texto", sans-serif; font-weight: 600; font-size: 30px; letter-spacing: 0.12em;
           text-transform: uppercase; color: var(--destaque); }}
"""
    html = (f'<div id="n-tarja"><div id="n-barra"></div><div id="n-corpo"><div id="n-nome">{esc(n)}</div>'
            + (f'<div id="n-cargo">{esc(cargo)}</div>' if cargo else "") + "</div></div>")
    t = _t(d["nome"])
    js = [f'tl.fromTo("#n-barra", {{scaleY: 0}}, {{scaleY: 1, duration: 0.3, ease: "power2.out"}}, {max(t - 0.15, 0):.2f});',
          f'tl.fromTo("#n-corpo", {{clipPath: "inset(0 100% 0 0)"}}, {{clipPath: "inset(0 0% 0 0)", duration: 0.5, '
          f'ease: "power3.out"}}, {t:.2f});',
          _entra("#n-nome", t + 0.1, "{opacity: 0, x: -20}", 0.4)]
    if cargo:
        js.append(_entra("#n-cargo", _t(d["cargo"]) or t + 0.3, "{opacity: 0, x: -14}", 0.4))
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ data

def data(d, dur):
    """O ano (ou a data) da fala. "carimbo": no meio, batido como um carimbo; "canto": pequeno, no alto à esquerda,
    sem escurecer o vídeo."""
    texto = d["data"]["texto"]
    t = _t(d["data"])
    legenda = (d.get("legenda") or {}).get("texto", "")
    if d.get("variante") == "canto":
        css = SEM_VEU + """
#d-canto { position: absolute; left: 0; top: 0; padding: 18px 30px; background: var(--painel);
           border-left: 8px solid var(--destaque); }
#d-ano { font-family: "Titulo", serif; font-weight: 700; font-size: 72px; line-height: 1; color: var(--texto); }
#d-leg { margin-top: 6px; font-family: "Texto", sans-serif; font-weight: 600; font-size: 26px; letter-spacing: 0.14em;
         text-transform: uppercase; color: var(--secundaria); max-width: 520px; }
"""
        html = (f'<div id="d-canto"><div id="d-ano">{esc(texto)}</div>'
                + (f'<div id="d-leg">{esc(legenda)}</div>' if legenda else "") + "</div>")
        js = [_entra("#d-canto", t, "{opacity: 0, x: -40}", 0.45)]
        if legenda:
            js.append(_entra("#d-leg", _t(d["legenda"]) or t + 0.3, "{opacity: 0}", 0.3))
        return css, html, "\n".join(js)
    px = _tam(texto, [(4, 230), (10, 150), (999, 110)])
    css = f"""
#d-caixa {{ width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;
           gap: 30px; }}
#d-selo {{ border: 10px solid var(--destaque); border-radius: 14px; padding: 6px 52px; transform: rotate(-6deg);
          font-family: "Titulo", serif; font-weight: 800; font-size: {px}px; line-height: 1.05; color: var(--destaque);
          letter-spacing: 0.04em; }}
#d-leg {{ max-width: 1300px; text-align: center; }}
"""
    html = (f'<div id="d-caixa"><div id="d-selo">{esc(texto)}</div>'
            + (f'<div id="d-leg" class="apoio">{esc(legenda)}</div>' if legenda else "") + "</div>")
    js = [f'tl.fromTo("#d-selo", {{opacity: 0, scale: 1.9, rotation: -14}}, {{opacity: 1, scale: 1, rotation: -6, '
          f'duration: 0.32, ease: "power4.in"}}, {max(t - 0.2, 0):.2f});',
          f'tl.fromTo("#d-selo", {{x: -6}}, {{x: 0, duration: 0.25, ease: "elastic.out(1, 0.3)"}}, {t + 0.12:.2f});']
    if legenda:
        js.append(_entra("#d-leg", _t(d["legenda"]) or t + 0.4, "{opacity: 0, y: 16}", 0.4))
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ termo

def termo(d, dur):
    """A palavra técnica digitada letra por letra, com cursor, e o que ela quer dizer embaixo."""
    palavra = d["termo"]["texto"]
    px = _tam(palavra, [(10, 136), (18, 108), (28, 84), (999, 66)])
    explica = (d.get("explicacao") or {}).get("texto", "")
    css = f"""
#t-caixa {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; gap: 30px; }}
#t-linha {{ display: flex; align-items: flex-end; font-family: "Titulo", serif; font-weight: 700; font-size: {px}px;
           line-height: 1.1; color: var(--texto); }}
.t-l {{ display: inline-block; white-space: pre; }}
#t-cursor {{ display: inline-block; width: 0.08em; height: 0.95em; margin-left: 0.06em; background: var(--destaque); }}
#t-traco {{ width: 420px; }}
#t-exp {{ max-width: 1400px; }}
"""
    letras = "".join(f'<span id="t-l{i}" class="t-l">{esc(c)}</span>' for i, c in enumerate(palavra))
    html = (f'<div id="t-caixa"><div class="rotulo" id="t-rot">{esc((d.get("rotulo") or {}).get("texto", ""))}</div>'
            f'<div id="t-linha">{letras}<span id="t-cursor"></span></div><div id="t-traco" class="traco"></div>'
            + (f'<div id="t-exp" class="apoio">{esc(explica)}</div>' if explica else "") + "</div>")
    t = _t(d["termo"])
    passo = min(0.06, 0.9 / max(len(palavra), 1))
    js = [f'tl.set(".t-l", {{opacity: 0}}, 0);', _entra("#t-cursor", max(t - 0.2, 0), "{opacity: 0}", 0.1)]
    if d.get("rotulo"):
        js.append(_entra("#t-rot", _t(d["rotulo"]), "{opacity: 0, x: -20}", 0.35))
    js += [f'tl.set("#t-l{i}", {{opacity: 1}}, {t + passo * i:.3f});' for i in range(len(palavra))]
    fim_digitar = t + passo * len(palavra)
    js.append(f'tl.fromTo("#t-traco", {{scaleX: 0}}, {{scaleX: 1, duration: 0.5, ease: "power2.inOut"}}, {fim_digitar:.2f});')
    js.append(f'tl.to("#t-cursor", {{opacity: 0, duration: 0.1, repeat: 5, yoyo: true}}, {fim_digitar:.2f});')
    if explica:
        js.append(_entra("#t-exp", max(_t(d["explicacao"]), fim_digitar + 0.1), "{opacity: 0, y: 18}", 0.45))
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ pergunta

def pergunta(d, dur):
    """A pergunta da fala, com um ponto de interrogação enorme na cor de destaque e um sublinhado que se desenha."""
    texto = d["pergunta"]["texto"].rstrip("?？¿ ").lstrip("¿")
    px = _tam(texto, [(30, 92), (55, 76), (85, 64), (999, 54)])
    abre = "¿" if d.get("_lingua", "")[:2] == "es" else ""
    css = f"""
#p-caixa {{ width: 100%; height: 100%; display: flex; align-items: center; gap: 60px; }}
#p-sinal {{ font-family: "Titulo", serif; font-weight: 800; font-size: 440px; line-height: 0.8; color: var(--destaque); }}
#p-texto {{ font-family: "Titulo", serif; font-weight: 700; font-size: {px}px; line-height: 1.12; color: var(--texto);
           max-width: 1260px; }}
#p-sub {{ width: 640px; margin-top: 26px; }}
"""
    html = (f'<div id="p-caixa"><div id="p-sinal">?</div><div><div id="p-texto">{esc(abre + texto)}?</div>'
            f'<div id="p-sub" class="traco"></div></div></div>')
    t = _t(d["pergunta"])
    js = [f'tl.fromTo("#p-sinal", {{opacity: 0, scale: 0.4, rotation: -20}}, {{opacity: 1, scale: 1, rotation: 0, '
          f'duration: 0.55, ease: "back.out(2)"}}, {max(t - 0.15, 0):.2f});',
          _entra("#p-texto", t, "{opacity: 0, x: 40}", 0.5),
          f'tl.fromTo("#p-sub", {{scaleX: 0}}, {{scaleX: 1, duration: 0.6, ease: "power2.inOut"}}, {t + 0.5:.2f});']
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ impacto

def impacto(d, dur):
    """Uma a três palavras gigantes, batidas na tela no segundo da fala, com um tremor curto."""
    texto = d["palavra"]["texto"]
    px = _tam(texto, [(6, 300), (11, 220), (18, 160), (999, 120)])
    css = f"""
#i-caixa {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }}
#i-palavra {{ font-family: "Titulo", serif; font-weight: 900; font-size: {px}px; line-height: 1; color: var(--texto);
             text-transform: uppercase; letter-spacing: 0.02em; text-align: center; max-width: 1650px; }}
#i-palavra b {{ color: var(--destaque); font-weight: 900; }}
"""
    destaque = (d.get("destaque") or "").strip().lower()
    partes = [f"<b>{esc(p)}</b>" if destaque and p.lower().strip(".,!") == destaque else esc(p) for p in texto.split()]
    html = f'<div id="i-caixa"><div id="i-palavra">{" ".join(partes)}</div></div>'
    t = _t(d["palavra"])
    js = [f'tl.fromTo("#i-palavra", {{opacity: 0, scale: 2.4}}, {{opacity: 1, scale: 1, duration: 0.28, '
          f'ease: "power4.in"}}, {max(t - 0.2, 0):.2f});',
          f'tl.fromTo("#i-caixa", {{x: -14, y: 8}}, {{x: 0, y: 0, duration: 0.4, ease: "elastic.out(1.2, 0.25)"}}, '
          f'{t + 0.08:.2f});']
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ karaokê

def karaoke(d, dur):
    """A frase inteira na tela, apagada, e cada palavra acendendo no segundo em que é falada."""
    palavras = d["palavras"]
    total = sum(len(p["texto"]) + 1 for p in palavras)
    px = _tam("x" * total, [(30, 96), (55, 80), (85, 66), (999, 56)])
    css = f"""
#k-caixa {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }}
#k-linha {{ display: flex; flex-wrap: wrap; justify-content: center; column-gap: 0.3em; row-gap: 0.12em;
           max-width: 1560px; font-family: "Titulo", serif; font-weight: 700; font-size: {px}px; line-height: 1.12;
           color: var(--texto); text-align: center; }}
.k-p {{ display: inline-block; opacity: 0.28; }}
"""
    html = '<div id="k-caixa"><div id="k-linha">' + "".join(
        f'<span id="k-p{i}" class="k-p">{esc(p["texto"])}</span>' for i, p in enumerate(palavras)) + "</div></div>"
    js = [_entra("#k-linha", max(_t(palavras[0]) - 0.3, 0), "{opacity: 0, y: 20}", 0.35)]
    for i, p in enumerate(palavras):
        cor = "var(--destaque)" if p.get("destaque") else "var(--texto)"
        js.append(f'tl.to("#k-p{i}", {{opacity: 1, color: "{cor}", scale: 1.06, duration: 0.12, ease: "power1.out"}}, '
                  f'{_t(p):.2f});')
        js.append(f'tl.to("#k-p{i}", {{scale: 1, duration: 0.25, ease: "power1.out"}}, {_t(p) + 0.12:.2f});')
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ rede

def rede(d, dur):
    """Pessoas e coisas ligadas: os nós num círculo (com o centro, se houver) e as linhas que se desenham quando a
    fala liga um ao outro."""
    nos = d["nos"]
    centro = d.get("centro")
    cx, cy, rx, ry = 850, 360, 610, 270
    pos = []
    for i in range(len(nos)):
        a = -math.pi / 2 + 2 * math.pi * i / len(nos)
        pos.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    ligacoes = d.get("ligacoes") or []
    if not ligacoes:
        ligacoes = ([{"de": -1, "para": i} for i in range(len(nos))] if centro
                    else [{"de": i, "para": i + 1} for i in range(len(nos) - 1)])
    css = """
#r-area { position: relative; width: 1700px; height: 760px; }
#r-linhas { position: absolute; left: 0; top: 0; width: 1700px; height: 760px; }
.r-l { fill: none; stroke: var(--destaque); stroke-width: 4; stroke-linecap: round; opacity: 0.85; }
.r-no { position: absolute; width: 360px; margin-left: -180px; margin-top: -40px; text-align: center; padding: 16px 18px;
        font-family: "Texto", sans-serif; font-weight: 700; font-size: 34px; line-height: 1.15; color: var(--texto); }
#r-centro { position: absolute; left: 650px; top: 300px; width: 400px; text-align: center; padding: 22px;
            font-family: "Titulo", serif; font-weight: 700; font-size: 52px; color: var(--destaque); }
"""

    def ponto(i):
        return (cx, cy) if i == -1 else pos[i]
    linhas, js = [], []
    for k, lig in enumerate(ligacoes):
        a, b = int(lig.get("de", 0)), int(lig.get("para", 0))
        if not (-1 <= a < len(nos) and -1 <= b < len(nos)) or a == b or (-1 in (a, b) and not centro):
            continue
        (x1, y1), (x2, y2) = ponto(a), ponto(b)
        comp = math.hypot(x2 - x1, y2 - y1)
        linhas.append(f'<line id="r-l{k}" class="r-l" x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                      f'stroke-dasharray="{comp:.0f}" stroke-dashoffset="{comp:.0f}" />')
        quando = max(_t(nos[b]) if b >= 0 else _t(centro), _t(nos[a]) if a >= 0 else _t(centro)) + 0.15
        js.append(f'tl.to("#r-l{k}", {{strokeDashoffset: 0, duration: 0.5, ease: "power2.out"}}, {quando:.2f});')
    caixas = "".join(f'<div id="r-n{i}" class="r-no cartao" style="left: {x:.0f}px; top: {y:.0f}px;">{esc(n["texto"])}</div>'
                     for i, (n, (x, y)) in enumerate(zip(nos, pos)))
    meio = f'<div id="r-centro" class="cartao">{esc(centro["texto"])}</div>' if centro else ""
    html = f'<div id="r-area"><svg id="r-linhas" viewBox="0 0 1700 760">{"".join(linhas)}</svg>{meio}{caixas}</div>'
    if centro:
        js.insert(0, _entra("#r-centro", _t(centro), "{opacity: 0, scale: 0.6}", 0.45, "back.out(1.8)"))
    js += [_entra(f"#r-n{i}", _t(n), "{opacity: 0, scale: 0.7}", 0.4, "back.out(1.8)") for i, n in enumerate(nos)]
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ ticker

def ticker(d, dur):
    """A faixa de notícias no alto da tela: a manchete fixa e os itens correndo da direita para a esquerda."""
    itens = d.get("itens") or []
    manchete = d["manchete"]["texto"]
    css = SEM_VEU + """
#tk-faixa { position: absolute; left: -110px; right: -110px; top: 0; height: 92px; display: flex; align-items: stretch;
            background: var(--painel); border-bottom: 4px solid var(--destaque); overflow: hidden; }
#tk-selo { flex: none; display: flex; align-items: center; padding: 0 30px 0 140px; background: var(--alerta, var(--destaque));
           font-family: "Texto", sans-serif; font-weight: 800; font-size: 32px; letter-spacing: 0.14em; color: #111; }
#tk-manchete { flex: none; display: flex; align-items: center; padding: 0 34px; font-family: "Titulo", serif;
               font-weight: 700; font-size: 44px; color: var(--texto); max-width: 900px; white-space: nowrap;
               overflow: hidden; text-overflow: ellipsis; }
#tk-pista { position: relative; flex: 1; overflow: hidden; }
#tk-rolo { position: absolute; left: 0; top: 0; height: 92px; display: flex; align-items: center; gap: 70px;
           white-space: nowrap; font-family: "Texto", sans-serif; font-weight: 600; font-size: 36px; color: var(--texto); }
.tk-i::before { content: "■"; color: var(--destaque); margin-right: 22px; font-size: 22px; vertical-align: middle; }
"""
    rolo = "".join(f'<span id="tk-i{i}" class="tk-i" data-layout-allow-occlusion>{esc(x["texto"])}</span>' for i, x in enumerate(itens))
    html = (f'<div id="tk-faixa"><div id="tk-selo">{esc(rotulo("urgente", d.get("_lingua")))}</div>'
            f'<div id="tk-manchete">{esc(manchete)}</div><div id="tk-pista"><div id="tk-rolo">{rolo}</div></div></div>')
    t = _t(d["manchete"])
    js = [f'tl.fromTo("#tk-faixa", {{y: -110}}, {{y: 0, duration: 0.45, ease: "power3.out"}}, {max(t - 0.2, 0):.2f});',
          _entra("#tk-manchete", t, "{opacity: 0}", 0.3)]
    if itens:
        js.append(f'tl.fromTo("#tk-rolo", {{x: 900}}, {{x: -{300 + 420 * len(itens)}, duration: {max(dur - t, 2):.2f}, '
                  f'ease: "none"}}, {t + 0.2:.2f});')
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ quiz

def quiz(d, dur):
    """A pergunta com 2 a 4 alternativas que entram uma a uma; a certa acende quando a fala diz a resposta."""
    opcoes = d["opcoes"]
    certa = d.get("certa") or {}
    css = """
#q-caixa { width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; gap: 34px; }
#q-perg { font-family: "Titulo", serif; font-weight: 700; font-size: 66px; line-height: 1.12; color: var(--texto);
          max-width: 1600px; }
#q-ops { display: grid; grid-template-columns: 1fr 1fr; gap: 22px 30px; }
.q-op { display: flex; align-items: center; gap: 24px; padding: 20px 26px; font-family: "Texto", sans-serif;
        font-weight: 600; font-size: 40px; color: var(--texto); }
.q-letra { flex: none; width: 62px; height: 62px; border-radius: 50%; border: 3px solid var(--destaque);
           display: flex; align-items: center; justify-content: center; font-weight: 800; color: var(--destaque); }
"""
    ops = "".join(f'<div id="q-o{i}" class="q-op cartao"><span class="q-letra">{"ABCD"[i]}</span>'
                  f'<span>{esc(o["texto"])}</span></div>' for i, o in enumerate(opcoes))
    html = f'<div id="q-caixa"><div id="q-perg">{esc(d["pergunta"]["texto"])}</div><div id="q-ops">{ops}</div></div>'
    js = [_entra("#q-perg", _t(d["pergunta"]), "{opacity: 0, y: -20}", 0.45)]
    js += [_entra(f"#q-o{i}", _t(o), "{opacity: 0, x: -30}", 0.35) for i, o in enumerate(opcoes)]
    idx = certa.get("indice")
    if isinstance(idx, int) and 0 <= idx < len(opcoes):
        quando = _t(certa)
        for i in range(len(opcoes)):
            if i == idx:
                js.append(f'tl.to("#q-o{i}", {{borderColor: "var(--destaque)", scale: 1.04, duration: 0.3}}, {quando:.2f});')
                js.append(f'tl.to("#q-o{i} .q-letra", {{backgroundColor: "var(--destaque)", color: "#111", '
                          f'duration: 0.3}}, {quando:.2f});')
            else:
                js.append(f'tl.to("#q-o{i}", {{opacity: 0.35, duration: 0.3}}, {quando:.2f});')
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ teaser

def teaser(d, dur):
    """O que vem a seguir, num cartão no alto à direita, sem escurecer o vídeo."""
    css = SEM_VEU + """
#te-card { position: absolute; right: 0; top: 0; width: 640px; padding: 24px 30px; background: var(--painel);
           border-top: 6px solid var(--destaque); }
#te-rot { font-family: "Texto", sans-serif; font-weight: 700; font-size: 26px; letter-spacing: 0.2em; color: var(--destaque); }
#te-tit { margin-top: 10px; font-family: "Titulo", serif; font-weight: 700; font-size: 46px; line-height: 1.12;
          color: var(--texto); }
"""
    html = (f'<div id="te-card"><div id="te-rot">{esc(rotulo("a_seguir", d.get("_lingua")))} →</div>'
            f'<div id="te-tit">{esc(d["titulo"]["texto"])}</div></div>')
    t = _t(d["titulo"])
    return css, html, "\n".join([_entra("#te-card", t, "{opacity: 0, x: 60}", 0.5),
                                 _entra("#te-tit", t + 0.2, "{opacity: 0}", 0.35)])


# ------------------------------------------------------------------------------------------------ chamada

def chamada(d, dur):
    """O "inscreva-se": o botão vermelho entra, o cursor clica, o botão vira "inscrito" e o sino toca."""
    t = _t(d.get("texto") or {}) or 0.3
    frase = (d.get("texto") or {}).get("texto", "")
    css = SEM_VEU + """
#c-area { position: absolute; left: 0; right: 0; bottom: 10px; display: flex; flex-direction: column; align-items: center;
          gap: 18px; }
#c-frase { font-family: "Texto", sans-serif; font-weight: 600; font-size: 38px; color: var(--texto);
           text-shadow: 0 2px 12px rgba(0, 0, 0, 0.85); max-width: 1300px; text-align: center; }
#c-linha { position: relative; display: flex; align-items: center; gap: 26px; }
#c-botao { position: relative; padding: 22px 54px; border-radius: 40px; background: #E62117; color: #fff;
           font-family: "Texto", sans-serif; font-weight: 800; font-size: 42px; letter-spacing: 0.06em; }
#c-feito { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; border-radius: 40px;
           background: #3a3a3a; color: #e8e8e8; opacity: 0; }
#c-sino { width: 78px; height: 78px; border-radius: 50%; background: var(--painel); display: flex; align-items: center;
          justify-content: center; }
#c-cursor { position: absolute; left: 60%; top: 90px; width: 46px; height: 46px; }
"""
    sino = ('<svg viewBox="0 0 24 24" width="46" height="46"><path fill="#fff" d="M12 22a2.5 2.5 0 0 0 2.4-2h-4.8A2.5 2.5 '
            '0 0 0 12 22zm7-6V11a7 7 0 0 0-5.5-6.8V3a1.5 1.5 0 0 0-3 0v1.2A7 7 0 0 0 5 11v5l-2 2v1h18v-1z"/></svg>')
    cursor = ('<svg id="c-cursor" viewBox="0 0 24 24"><path fill="#fff" stroke="#111" stroke-width="1.2" '
              'd="M5 2l14 12-6.5.6 3.8 7.4-2.6 1.2-3.7-7.5L5 20z"/></svg>')
    html = (f'<div id="c-area">' + (f'<div id="c-frase">{esc(frase)}</div>' if frase else "")
            + f'<div id="c-linha"><div id="c-botao">{esc(rotulo("inscreva", d.get("_lingua")))}'
            f'<div id="c-feito">{esc(rotulo("inscrito", d.get("_lingua")))}</div></div>'
            f'<div id="c-sino">{sino}</div>{cursor}</div></div>')
    clique = t + 0.9
    js = [_entra("#c-area", max(t - 0.2, 0), "{opacity: 0, y: 40}", 0.45),
          f'tl.fromTo("#c-cursor", {{x: 220, y: 120, opacity: 0}}, {{x: 0, y: 0, opacity: 1, duration: 0.6, '
          f'ease: "power2.out"}}, {t + 0.2:.2f});',
          f'tl.to("#c-botao", {{scale: 0.92, duration: 0.08, yoyo: true, repeat: 1}}, {clique:.2f});',
          f'tl.to("#c-feito", {{opacity: 1, duration: 0.15}}, {clique + 0.08:.2f});',
          f'tl.to("#c-cursor", {{x: 130, y: 0, duration: 0.4, ease: "power2.inOut"}}, {clique + 0.35:.2f});',
          f'tl.fromTo("#c-sino", {{rotation: 0}}, {{rotation: 18, duration: 0.08, yoyo: true, repeat: 7}}, {clique + 0.8:.2f});']
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ fotos

def _foto_tag(src, i, classe):
    return f'<img id="{classe}{i}" class="{classe}" src="{esc(src)}" />' if src else f'<div id="{classe}{i}" class="{classe} f-vazia"></div>'


def carrossel(d, dur):
    """Duas a quatro fotos (as das cenas deste trecho) entrando uma a uma, como cartões, cada uma com a legenda dita."""
    itens = d["itens"]
    fotos = list(d.get("_imagens") or [])
    n = len(itens)
    largura = {2: 640, 3: 500, 4: 380}.get(n, 380)
    css = f"""
#ca-fila {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; gap: 34px; }}
.ca-card {{ width: {largura}px; padding: 16px 16px 22px; background: #F4EFE6; box-shadow: 0 18px 40px rgba(0, 0, 0, 0.55); }}
.ca-f {{ display: block; width: 100%; height: {int(largura * 0.72)}px; object-fit: cover; background: #222; }}
.f-vazia {{ background: linear-gradient(135deg, #333, #111); }}
.ca-leg {{ margin-top: 14px; font-family: "Texto", sans-serif; font-weight: 700; font-size: 32px; color: #1b1b1b;
          text-align: center; line-height: 1.15; }}
"""
    cards = "".join(f'<div id="ca-c{i}" class="ca-card" style="transform: rotate({(-3, 2, -1.5, 3)[i % 4]}deg);">'
                    f'{_foto_tag(fotos[i] if i < len(fotos) else "", i, "ca-f")}'
                    f'<div class="ca-leg">{esc(x["texto"])}</div></div>' for i, x in enumerate(itens))
    html = f'<div id="ca-fila">{cards}</div>'
    js = [_entra(f"#ca-c{i}", _t(x), "{opacity: 0, x: 160, rotation: 10}", 0.55, "power3.out") for i, x in enumerate(itens)]
    return css, html, "\n".join(js)


def foto(d, dur):
    """A foto do assunto em destaque. "polaroid": moldura branca com fita; "contato": a folha de contato com a foto
    marcada a caneta; "detalhe": a foto com uma lupa que aproxima o centro."""
    src = (d.get("_imagens") or [""])[0]
    legenda = (d.get("legenda") or {}).get("texto", "")
    t = _t(d.get("legenda") or {}) or 0.2
    variante = d.get("variante") or "polaroid"
    if variante == "contato":
        css = """
#fc-folha { position: absolute; left: 150px; top: 20px; width: 1400px; padding: 30px; background: #111;
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.fc-q { width: 100%; height: 190px; object-fit: cover; filter: grayscale(0.4) brightness(0.7); }
#fc-alvo { filter: none; }
#fc-circ { position: absolute; fill: none; stroke: #E62117; stroke-width: 7; stroke-linecap: round; }
#fc-leg { position: absolute; left: 0; right: 0; bottom: 0; text-align: center; }
.f-vazia { background: linear-gradient(135deg, #333, #111); }
"""
        quadros = "".join((f'<img id="fc-alvo" class="fc-q" src="{esc(src)}" />' if i == 5
                           else (f'<img class="fc-q" src="{esc(src)}" style="object-position: {12 * i}% 50%;" />' if src
                                 else '<div class="fc-q f-vazia"></div>')) for i in range(8))
        html = (f'<div id="fc-folha">{quadros}</div><svg id="fc-circ" viewBox="0 0 1700 760" '
                f'style="left:0;top:0;width:1700px;height:760px"><ellipse id="fc-e" cx="690" cy="355" rx="200" ry="135" '
                f'stroke-dasharray="1060" stroke-dashoffset="1060" /></svg>'
                + (f'<div id="fc-leg" class="titulo" style="font-size:56px">{esc(legenda)}</div>' if legenda else ""))
        js = [_entra("#fc-folha", max(t - 0.4, 0), "{opacity: 0, y: 30}", 0.5),
              f'tl.to("#fc-e", {{strokeDashoffset: 0, duration: 0.6, ease: "power2.inOut"}}, {t:.2f});']
        if legenda:
            js.append(_entra("#fc-leg", t + 0.4, "{opacity: 0, y: 16}", 0.4))
        return css, html, "\n".join(js)
    if variante == "detalhe":
        css = """
#fd-foto { position: absolute; left: 250px; top: 0; width: 1200px; height: 680px; object-fit: cover;
           box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6); }
#fd-lupa { position: absolute; left: 700px; top: 190px; width: 300px; height: 300px; border-radius: 50%;
           border: 10px solid var(--destaque); overflow: hidden; box-shadow: 0 0 0 6px rgba(0, 0, 0, 0.5); }
/* a lupa (300 px) fica sobre o ponto (600, 340) da foto; a foto dentro dela, 2 vezes maior, põe esse ponto no centro */
#fd-zoom { position: absolute; left: -1050px; top: -530px; width: 2400px; height: 1360px; object-fit: cover; }
#fd-leg { position: absolute; left: 0; right: 0; bottom: 0; text-align: center; font-size: 52px; }
.f-vazia { background: linear-gradient(135deg, #333, #111); }
"""
        foto_ = f'<img id="fd-foto" src="{esc(src)}" />' if src else '<div id="fd-foto" class="f-vazia"></div>'
        zoom = f'<img id="fd-zoom" src="{esc(src)}" />' if src else ""
        html = (f'{foto_}<div id="fd-lupa">{zoom}</div>'
                + (f'<div id="fd-leg" class="titulo">{esc(legenda)}</div>' if legenda else ""))
        js = [_entra("#fd-foto", max(t - 0.4, 0), "{opacity: 0, scale: 1.04}", 0.5),
              _entra("#fd-lupa", t, "{opacity: 0, scale: 0.3}", 0.45, "back.out(1.6)")]
        if legenda:
            js.append(_entra("#fd-leg", t + 0.3, "{opacity: 0, y: 16}", 0.4))
        return css, html, "\n".join(js)
    css = """
#fp-card { position: absolute; left: 520px; top: 0; width: 660px; padding: 22px 22px 90px; background: #F4EFE6;
           transform: rotate(-4deg); box-shadow: 0 24px 50px rgba(0, 0, 0, 0.6); }
#fp-img { display: block; width: 616px; height: 520px; object-fit: cover; background: #222; }
#fp-fita { position: absolute; left: 230px; top: -26px; width: 200px; height: 52px; background: rgba(232, 222, 190, 0.78);
           transform: rotate(3deg); }
#fp-leg { position: absolute; left: 22px; right: 22px; bottom: 18px; font-family: "Texto", sans-serif; font-weight: 700;
          font-size: 40px; color: #1b1b1b; text-align: center; }
.f-vazia { background: linear-gradient(135deg, #333, #111); }
"""
    img = f'<img id="fp-img" src="{esc(src)}" />' if src else '<div id="fp-img" class="f-vazia"></div>'
    html = (f'<div id="fp-card">{img}<div id="fp-fita"></div>'
            + (f'<div id="fp-leg">{esc(legenda)}</div>' if legenda else "") + "</div>")
    js = [f'tl.fromTo("#fp-card", {{opacity: 0, y: -80, rotation: 8, scale: 1.1}}, {{opacity: 1, y: 0, rotation: -4, '
          f'scale: 1, duration: 0.55, ease: "power3.out"}}, {max(t - 0.3, 0):.2f});']
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ provas

def provas(d, dur):
    """O quadro de provas em 4 variantes: ficha (uma ficha datilografada), recibo (a lista com valor de cada item e o
    total), tiras (recortes colados um a um) e fio (fichas presas no quadro, ligadas pelo fio vermelho)."""
    itens = d["itens"]
    titulo = (d.get("titulo") or {}).get("texto", "") or rotulo("prova", d.get("_lingua"))
    variante = d.get("variante") or "ficha"
    js = []
    if variante == "recibo":
        css = """
#pr-papel { position: absolute; left: 560px; top: -20px; width: 580px; padding: 34px 40px 40px; background: #F7F4EC;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.55); font-family: "Courier New", monospace; color: #1d1d1d; }
#pr-tit { font-size: 34px; font-weight: 700; text-align: center; letter-spacing: 0.1em; border-bottom: 3px dashed #555;
          padding-bottom: 16px; margin-bottom: 14px; text-transform: uppercase; }
.pr-i { display: flex; justify-content: space-between; gap: 18px; font-size: 30px; padding: 7px 0; }
.pr-v { font-weight: 700; white-space: nowrap; }
#pr-total { display: flex; justify-content: space-between; border-top: 3px dashed #555; margin-top: 14px; padding-top: 14px;
            font-size: 36px; font-weight: 800; }
"""
        linhas = "".join(f'<div id="pr-i{i}" class="pr-i"><span>{esc(x["texto"])}</span>'
                         f'<span class="pr-v">{esc(x.get("valor", ""))}</span></div>' for i, x in enumerate(itens))
        total = d.get("total") or {}
        html = (f'<div id="pr-papel"><div id="pr-tit">{esc(titulo)}</div>{linhas}'
                + (f'<div id="pr-total"><span>{esc(rotulo("total", d.get("_lingua")))}</span>'
                   f'<span>{esc(total.get("texto", ""))}</span></div>' if total.get("texto") else "") + "</div>")
        js.append(f'tl.fromTo("#pr-papel", {{clipPath: "inset(0 0 100% 0)"}}, {{clipPath: "inset(0 0 0% 0)", '
                  f'duration: 0.6, ease: "power2.out"}}, {max(_t(itens[0]) - 0.6, 0):.2f});')
        js += [_entra(f"#pr-i{i}", _t(x), "{opacity: 0}", 0.15, "none") for i, x in enumerate(itens)]
        if total.get("texto"):
            js.append(_entra("#pr-total", _t(total), "{opacity: 0, scale: 1.2}", 0.25))
        return css, html, "\n".join(js)
    if variante == "tiras":
        css = """
#pt-col { width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;
          gap: 22px; }
.pt-t { padding: 14px 34px; background: #EFE7D6; color: #161616; font-family: "Titulo", serif; font-weight: 700;
        font-size: 48px; box-shadow: 0 10px 22px rgba(0, 0, 0, 0.5); max-width: 1400px; }
"""
        tiras = "".join(f'<div id="pt-t{i}" class="pt-t" style="transform: rotate({(-2, 1.5, -1, 2.2, -1.8)[i % 5]}deg);">'
                        f'{esc(x["texto"])}</div>' for i, x in enumerate(itens))
        html = f'<div id="pt-col">{tiras}</div>'
        js = [f'tl.fromTo("#pt-t{i}", {{opacity: 0, scale: 1.4}}, {{opacity: 1, scale: 1, duration: 0.22, '
              f'ease: "power4.in"}}, {_t(x):.2f});' for i, x in enumerate(itens)]
        return css, html, "\n".join(js)
    if variante == "fio":
        n = len(itens)
        pos = [(180 + i * (1340 / max(n - 1, 1)), 200 if i % 2 == 0 else 470) for i in range(n)]
        css = """
#pf-area { position: relative; width: 1700px; height: 760px; }
#pf-fios { position: absolute; left: 0; top: 0; width: 1700px; height: 760px; }
.pf-l { fill: none; stroke: #D7263D; stroke-width: 5; stroke-linecap: round; }
.pf-c { position: absolute; width: 300px; margin-left: -150px; margin-top: -70px; padding: 26px 18px 20px;
        background: #F2EBDD; color: #161616; font-family: "Texto", sans-serif; font-weight: 700; font-size: 32px;
        text-align: center; box-shadow: 0 12px 24px rgba(0, 0, 0, 0.55); }
.pf-c::before { content: ""; position: absolute; left: 136px; top: -14px; width: 28px; height: 28px; border-radius: 50%;
                background: #D7263D; box-shadow: 2px 3px 0 rgba(0, 0, 0, 0.45); }
#pf-tit { position: absolute; left: 0; top: 0; }
"""
        fios = []
        for i in range(n - 1):
            (x1, y1), (x2, y2) = pos[i], pos[i + 1]
            comp = math.hypot(x2 - x1, y2 - y1) + 40
            fios.append(f'<path id="pf-l{i}" class="pf-l" d="M{x1:.0f},{y1 - 70:.0f} Q{(x1 + x2) / 2:.0f},'
                        f'{max(y1, y2) - 10:.0f} {x2:.0f},{y2 - 70:.0f}" stroke-dasharray="{comp:.0f}" '
                        f'stroke-dashoffset="{comp:.0f}" />')
            js.append(f'tl.to("#pf-l{i}", {{strokeDashoffset: 0, duration: 0.5, ease: "power2.out"}}, '
                      f'{_t(itens[i + 1]):.2f});')
        cards = "".join(f'<div id="pf-c{i}" class="pf-c" style="left: {x:.0f}px; top: {y:.0f}px; '
                        f'transform: rotate({(-3, 2, -2, 3, -1)[i % 5]}deg);">{esc(x_["texto"])}</div>'
                        for i, (x_, (x, y)) in enumerate(zip(itens, pos)))
        html = (f'<div id="pf-area"><div id="pf-tit" class="rotulo">{esc(titulo)}</div>'
                f'<svg id="pf-fios" viewBox="0 0 1700 760">{"".join(fios)}</svg>{cards}</div>')
        js = [_entra("#pf-tit", max(_t(itens[0]) - 0.3, 0), "{opacity: 0}", 0.3)] + [
            _entra(f"#pf-c{i}", _t(x), "{opacity: 0, y: -40, scale: 1.1}", 0.35) for i, x in enumerate(itens)] + js
        return css, html, "\n".join(js)
    # ficha
    css = """
#pfi-ficha { position: absolute; left: 260px; top: 60px; width: 1180px; padding: 40px 54px 44px; background: #EFE8D8;
             color: #1a1a1a; box-shadow: 0 20px 44px rgba(0, 0, 0, 0.6);
             background-image: repeating-linear-gradient(0deg, transparent 0 55px, rgba(60, 90, 160, 0.25) 55px 57px); }
#pfi-tit { font-family: "Courier New", monospace; font-weight: 700; font-size: 40px; letter-spacing: 0.14em;
           text-transform: uppercase; color: #8B1E1E; margin-bottom: 18px; }
.pfi-i { font-family: "Courier New", monospace; font-size: 38px; line-height: 57px; }
.pfi-i::before { content: "— "; color: #8B1E1E; }
"""
    linhas = "".join(f'<div id="pfi-i{i}" class="pfi-i">{esc(x["texto"])}</div>' for i, x in enumerate(itens))
    html = f'<div id="pfi-ficha"><div id="pfi-tit">{esc(titulo)}</div>{linhas}</div>'
    js = [_entra("#pfi-ficha", max(_t(itens[0]) - 0.5, 0), "{opacity: 0, y: 40}", 0.5)]
    js += [f'tl.fromTo("#pfi-i{i}", {{clipPath: "inset(0 100% 0 0)"}}, {{clipPath: "inset(0 0% 0 0)", duration: '
           f'{min(0.05 * len(x["texto"]), 1.0):.2f}, ease: "steps({max(len(x["texto"]), 1)})"}}, {_t(x):.2f});'
           for i, x in enumerate(itens)]
    return css, html, "\n".join(js)


# ------------------------------------------------------------------------------------------------ mapa-múndi

def _projecao(lugares_):
    """A janela do mapa (lon e lat mínimas e máximas) que mostra todos os lugares com folga, na proporção da tela."""
    lats = [l["lat"] for l in lugares_]
    lons = [l["lon"] for l in lugares_]
    meio_lon = (min(lons) + max(lons)) / 2
    meio_lat = (min(lats) + max(lats)) / 2
    vao_lon = max(max(lons) - min(lons) + 40, 70.0)
    vao_lat = max(max(lats) - min(lats) + 26, 34.0)
    # 1700 x 760: a largura em graus é 2,24 vezes a altura
    if vao_lon / vao_lat < 1700 / 760:
        vao_lon = vao_lat * 1700 / 760
    else:
        vao_lat = vao_lon * 760 / 1700
    vao_lon = min(vao_lon, 360.0)
    vao_lat = min(vao_lat, 170.0)
    return meio_lon - vao_lon / 2, meio_lat + vao_lat / 2, vao_lon, vao_lat


def mapa_mundi(d, dur):
    """O lugar no mundo: continentes estilizados, a grade de latitude e longitude, o ponto que acende no lugar certo, a
    rota pelo caminho mais curto entre dois lugares e a distância de verdade."""
    lugares_ = d["lugares"]
    lon0, lat0, vlon, vlat = _projecao(lugares_)

    meio = lon0 + vlon / 2

    def volta_de(lon):
        """Quantos 360 graus somar para o desenho ficar do lado da janela (o Pacífico de um lado ou do outro)."""
        return round((meio - lon) / 360) * 360

    def xy(lat, lon, volta=None):
        volta = volta_de(lon) if volta is None else volta
        return (lon + volta - lon0) / vlon * 1700, (lat0 - lat) / vlat * 760

    formas = []
    for pontos in _lugares.CONTINENTES.values():
        # o continente anda inteiro: ponto a ponto, ele se partiria na borda e riscaria o mapa de lado a lado
        volta = volta_de(sum(lo for _, lo in pontos) / len(pontos))
        caminho = " ".join(f"{x:.0f},{y:.0f}" for x, y in (xy(la, lo, volta) for la, lo in pontos))
        formas.append(f'<polygon class="mm-terra" points="{caminho}" />')
    grade = []
    passo = 10 if vlon < 120 else 20
    lon = math.ceil(lon0 / passo) * passo
    while lon < lon0 + vlon:
        x, _ = xy(0, lon)
        grade.append(f'<line class="mm-g" x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="760" />')
        lon += passo
    lat = math.floor(lat0 / passo) * passo
    while lat > lat0 - vlat:
        _, y = xy(lat, lon0)
        grade.append(f'<line class="mm-g" x1="0" y1="{y:.0f}" x2="1700" y2="{y:.0f}" />')
        lat -= passo
    rotas, js, rotulos_ = [], [], []
    marcas = []
    for i, l in enumerate(lugares_):
        x, y = xy(l["lat"], l["lon"])
        marcas.append(f'<circle id="mm-a{i}" class="mm-anel" cx="{x:.0f}" cy="{y:.0f}" r="40" />'
                      f'<circle id="mm-p{i}" class="mm-ponto" cx="{x:.0f}" cy="{y:.0f}" r="13" />')
        acima = y > 120
        rotulos_.append(f'<div id="mm-n{i}" class="mm-nome" style="left: {x:.0f}px; top: {y - 92 if acima else y + 34:.0f}px;">'
                        f'{esc(l["texto"])}</div>')
        t = _t(l)
        js += [f'tl.fromTo("#mm-p{i}", {{scale: 0, transformOrigin: "50% 50%"}}, {{scale: 1, duration: 0.35, '
               f'ease: "back.out(2.4)"}}, {t:.2f});',
               f'tl.fromTo("#mm-a{i}", {{scale: 0.2, opacity: 0.9, transformOrigin: "50% 50%"}}, {{scale: 2.2, opacity: 0, '
               f'duration: 1.3, ease: "power1.out"}}, {t:.2f});',
               _entra(f"#mm-n{i}", t + 0.1, "{opacity: 0, y: 14}", 0.35)]
    if d.get("rota") and len(lugares_) >= 2:
        for i in range(len(lugares_) - 1):
            # o arco é desenrolado (sem pular 360 graus no meio) e depois posto do lado da janela, de uma vez
            arco, anterior = [], None
            for la, lo in _lugares.arco(lugares_[i], lugares_[i + 1]):
                if anterior is not None:
                    lo += round((anterior - lo) / 360) * 360
                arco.append((la, lo))
                anterior = lo
            volta = volta_de(arco[0][1])
            pontos = [xy(la, lo, volta) for la, lo in arco]
            comp = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pontos, pontos[1:])) + 10
            caminho = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pontos)
            rotas.append(f'<path id="mm-r{i}" class="mm-rota" d="{caminho}" stroke-dasharray="{comp:.0f}" '
                         f'stroke-dashoffset="{comp:.0f}" />')
            js.append(f'tl.to("#mm-r{i}", {{strokeDashoffset: 0, duration: 1.1, ease: "power2.inOut"}}, '
                      f'{_t(lugares_[i]) + 0.3:.2f});')
    distancia = d.get("_distancia")
    caixa = f'<div id="mm-dist" class="cartao">{esc(distancia)}</div>' if distancia else ""
    if distancia:
        js.append(_entra("#mm-dist", _t(lugares_[-1]) + 0.6, "{opacity: 0, x: 40}", 0.4))
    css = """
#mm-area { position: relative; width: 1700px; height: 760px; overflow: hidden; }
#mm-svg { position: absolute; left: 0; top: 0; width: 1700px; height: 760px; }
.mm-terra { fill: rgba(243, 235, 221, 0.13); stroke: rgba(243, 235, 221, 0.45); stroke-width: 2; stroke-linejoin: round; }
.mm-g { stroke: rgba(243, 235, 221, 0.10); stroke-width: 1.5; }
.mm-ponto { fill: var(--destaque); }
.mm-anel { fill: none; stroke: var(--destaque); stroke-width: 4; }
.mm-rota { fill: none; stroke: var(--destaque); stroke-width: 5; stroke-linecap: round; }
.mm-nome { position: absolute; width: 440px; margin-left: -220px; text-align: center; font-family: "Titulo", serif;
           font-weight: 700; font-size: 50px; color: var(--texto); text-shadow: 0 3px 14px rgba(0, 0, 0, 0.9); }
#mm-dist { position: absolute; right: 0; bottom: 0; padding: 16px 28px; font-family: "Titulo", serif; font-weight: 700;
           font-size: 50px; color: var(--destaque); }
"""
    html = (f'<div id="mm-area"><svg id="mm-svg" viewBox="0 0 1700 760">{"".join(grade)}{"".join(formas)}'
            f'{"".join(rotas)}{"".join(marcas)}</svg>{"".join(rotulos_)}{caixa}</div>')
    js.insert(0, 'tl.fromTo("#mm-svg", {opacity: 0, scale: 1.06}, {opacity: 1, scale: 1, duration: 0.8, '
                 'ease: "power2.out"}, 0);')
    return css, html, "\n".join(js)


def distancia_texto(km: float, lingua: str) -> str:
    """"8.400 km" (ou "5,220 mi" em inglês dos EUA não: o vídeo usa km em todas as línguas), no formato da língua."""
    arredondado = int(round(km, -2)) if km >= 1000 else int(round(km, -1))
    texto = f"{arredondado:,}"
    if str(lingua or "")[:2] not in ("en", "ja", "zh", "ko", "hi", "th"):
        texto = texto.replace(",", ".")
    return f"≈ {texto} km"


MODELOS = {"secao": secao, "nome": nome, "data": data, "termo": termo, "pergunta": pergunta, "impacto": impacto,
           "karaoke": karaoke, "rede": rede, "ticker": ticker, "quiz": quiz, "teaser": teaser, "chamada": chamada,
           "carrossel": carrossel, "foto": foto, "provas": provas, "mapa_mundi": mapa_mundi}

# os modelos que mostram as fotos das cenas do trecho (a fábrica copia as imagens para a pasta da animação)
COM_FOTO = {"carrossel": 4, "foto": 1}

CATALOGO = """
- secao: o título de um capítulo novo do vídeo (a fábrica põe "CAPÍTULO N" na língua do vídeo).
  dados: {"titulo": {"texto": o nome do capítulo, "t"}, "numero": 2 (opcional)}
- nome: a tarja com o nome de quem (ou do que) a fala cita, no canto de baixo, sem escurecer o vídeo.
  dados: {"nome": {"texto", "t"}, "cargo": {"texto": o que ele é, como a fala diz, "t"} (opcional), "variante": "tarja" ou "credito"}
- data: o ano ou a data que a fala cita. "carimbo" no meio da tela, "canto" pequeno no alto.
  dados: {"data": {"texto": "1984" (em algarismos, mesmo que a fala diga por extenso), "t"}, "legenda": {"texto", "t"} (opcional), "variante": "carimbo" ou "canto"}
- termo: uma palavra técnica ou um nome de conceito, digitado letra a letra, com o que ele quer dizer.
  dados: {"termo": {"texto", "t"}, "explicacao": {"texto": até 12 palavras, "t"} (opcional), "rotulo": {"texto", "t"} (opcional)}
- pergunta: a pergunta que a fala faz, em destaque.
  dados: {"pergunta": {"texto": a pergunta com as palavras da fala, "t"}}
- impacto: UMA a TRÊS palavras gigantes, para a frase curta que bate forte ("Zero.", "It failed.").
  dados: {"palavra": {"texto", "t"}, "destaque": uma das palavras, para a cor de destaque (opcional)}
- karaoke: a frase inteira da fala (4 a 14 palavras), cada palavra acendendo quando é falada.
  dados: {"palavras": [{"texto", "t", "destaque": true/false}]}
- rede: pessoas, empresas ou coisas ligadas umas às outras (quem financiou quem, quem conhece quem).
  dados: {"centro": {"texto", "t"} (opcional), "nos": [{"texto", "t"}] (3 a 6), "ligacoes": [{"de": índice do nó ou -1 para o centro, "para": índice}] (opcional)}
- ticker: uma notícia, como a faixa de um telejornal: a manchete e 1 a 4 itens correndo.
  dados: {"manchete": {"texto", "t"}, "itens": [{"texto", "t"}]}
- quiz: a fala pergunta e dá alternativas (2 a 4), e depois diz qual é a certa.
  dados: {"pergunta": {"texto", "t"}, "opcoes": [{"texto", "t"}], "certa": {"indice": 0 a 3, "t": quando a fala diz a resposta} (opcional)}
- teaser: o que vem a seguir no vídeo, num cartão no canto.
  dados: {"titulo": {"texto", "t"}}
- chamada: a fala pede para se inscrever no canal: o botão de inscrição é clicado e o sino toca.
  dados: {"texto": {"texto": a frase curta da fala (opcional), "t"}}
- carrossel: 2 a 4 coisas que a fala cita uma depois da outra, cada uma com a foto da cena dela.
  dados: {"itens": [{"texto": o nome da coisa, "t"}]}
- foto: a foto do assunto desta cena em destaque, com a legenda.
  dados: {"legenda": {"texto", "t"}, "variante": "polaroid", "contato" ou "detalhe"}
- provas: um quadro de provas, para investigação, golpe, crime ou mistério.
  dados: {"titulo": {"texto", "t"} (opcional), "variante": "ficha", "recibo", "tiras" ou "fio",
          "itens": [{"texto", "t", "valor": "US$ 400" (só no recibo, opcional)}] (2 a 5), "total": {"texto", "t"} (só no recibo, opcional)}
- mapa_mundi: um a três lugares de verdade no mapa do mundo (país, cidade ou região), na ordem em que a fala cita;
  com "rota": true, a rota de um ao outro e a distância real. A fábrica acha o lugar no atlas pelo nome.
  dados: {"lugares": [{"texto": o nome do lugar como a fala diz, "t"}], "rota": true/false}
"""


def _item(x, limite, tempo, campo="texto"):
    if not isinstance(x, dict) or not str(x.get(campo) or "").strip():
        return None
    texto = re.sub(r"\s+", " ", str(x[campo])).strip()
    if len(texto) > limite:
        texto = texto[:limite].rsplit(" ", 1)[0]
    return {**x, campo: texto, "t": tempo(x.get("t"))}


def conferir(modelo, d, tempo, inventadas, lingua=""):
    """(dados, erros) das formas daqui, como o conferir_dados de animacoes_modelos."""
    erros = []
    d = dict(d or {})
    if modelo == "secao":
        titulo = _item(d.get("titulo"), 48, tempo)
        if not titulo:
            erros.append('secao precisa de titulo = {"texto", "t"}')
        numero = d.get("numero")
        numero = int(numero) if str(numero or "").isdigit() and 0 < int(numero) < 100 else None
        d = {"titulo": titulo, "numero": numero}
    elif modelo == "nome":
        n = _item(d.get("nome"), 40, tempo)
        if not n:
            erros.append('nome precisa de nome = {"texto", "t"}')
        d = {"nome": n, "cargo": _item(d.get("cargo"), 44, tempo),
             "variante": "credito" if d.get("variante") == "credito" else "tarja"}
    elif modelo == "data":
        x = _item(d.get("data"), 18, tempo)
        if not x or not re.search(r"\d", x["texto"]):
            erros.append('data precisa de data = {"texto": em algarismos, como "1984" ou "12/05/1984", "t"}')
        d = {"data": x, "legenda": _item(d.get("legenda"), 50, tempo),
             "variante": "canto" if d.get("variante") == "canto" else "carimbo"}
    elif modelo == "termo":
        x = _item(d.get("termo"), 30, tempo)
        if not x:
            erros.append('termo precisa de termo = {"texto", "t"}')
        elif inventadas([x]):
            erros.append(f'o termo "{x["texto"]}" não foi dito: use a palavra como a narração fala')
        d = {"termo": x, "explicacao": _item(d.get("explicacao"), 90, tempo), "rotulo": _item(d.get("rotulo"), 24, tempo)}
    elif modelo == "pergunta":
        x = _item(d.get("pergunta"), 110, tempo)
        if not x:
            erros.append('pergunta precisa de pergunta = {"texto", "t"}')
        elif inventadas([{"texto": re.sub(r"[?¿]", "", x["texto"])}]):
            erros.append("a pergunta usa palavras que não foram ditas: use as palavras da narração")
        d = {"pergunta": x}
    elif modelo == "impacto":
        x = _item(d.get("palavra"), 26, tempo)
        if not x or len(x["texto"].split()) > 3:
            erros.append('impacto precisa de palavra = {"texto": 1 a 3 palavras, "t"}')
        elif inventadas([x]):
            erros.append("a palavra de impacto não foi dita: use uma palavra da narração")
        d = {"palavra": x, "destaque": str(d.get("destaque") or "")[:20]}
    elif modelo == "karaoke":
        palavras = [p for p in (_item(p, 22, tempo) for p in (d.get("palavras") or [])[:16]) if p]
        if not 4 <= len(palavras) <= 14:
            erros.append("karaoke precisa de 4 a 14 palavras, cada uma com texto e t, na ordem da fala")
        elif inventadas(palavras):
            erros.append("o karaokê tem palavras que não foram ditas: copie a frase da narração")
        d = {"palavras": [{**p, "destaque": bool(p.get("destaque"))} for p in palavras]}
    elif modelo == "rede":
        nos = [n for n in (_item(n, 26, tempo) for n in (d.get("nos") or [])[:6]) if n]
        if len(nos) < 3:
            erros.append("rede precisa de 3 a 6 nós")
        ligacoes = []
        for lig in (d.get("ligacoes") or [])[:10]:
            try:
                ligacoes.append({"de": int(lig.get("de")), "para": int(lig.get("para"))})
            except (AttributeError, TypeError, ValueError):
                continue
        d = {"centro": _item(d.get("centro"), 24, tempo), "nos": nos, "ligacoes": ligacoes}
    elif modelo == "ticker":
        m = _item(d.get("manchete"), 40, tempo)
        if not m:
            erros.append('ticker precisa de manchete = {"texto", "t"}')
        d = {"manchete": m, "itens": [i for i in (_item(i, 60, tempo) for i in (d.get("itens") or [])[:4]) if i]}
    elif modelo == "quiz":
        p = _item(d.get("pergunta"), 90, tempo)
        ops = [o for o in (_item(o, 34, tempo) for o in (d.get("opcoes") or [])[:4]) if o]
        if not p or len(ops) < 2:
            erros.append('quiz precisa de pergunta = {"texto", "t"} e de 2 a 4 opcoes')
        certa = d.get("certa")
        if isinstance(certa, dict) and str(certa.get("indice", "")).lstrip("-").isdigit():
            certa = {"indice": int(certa["indice"]), "t": tempo(certa.get("t"))}
        else:
            certa = None
        d = {"pergunta": p, "opcoes": ops, "certa": certa}
    elif modelo == "teaser":
        x = _item(d.get("titulo"), 54, tempo)
        if not x:
            erros.append('teaser precisa de titulo = {"texto", "t"}')
        d = {"titulo": x}
    elif modelo == "chamada":
        d = {"texto": _item(d.get("texto"), 70, tempo)}
    elif modelo == "carrossel":
        itens = [i for i in (_item(i, 28, tempo) for i in (d.get("itens") or [])[:4]) if i]
        if len(itens) < 2:
            erros.append("carrossel precisa de 2 a 4 itens")
        d = {"itens": itens}
    elif modelo == "foto":
        d = {"legenda": _item(d.get("legenda"), 40, tempo),
             "variante": d.get("variante") if d.get("variante") in ("polaroid", "contato", "detalhe") else "polaroid"}
    elif modelo == "provas":
        itens = [i for i in (_item(i, 60, tempo) for i in (d.get("itens") or [])[:5]) if i]
        itens = [{**i, "valor": re.sub(r"\s+", " ", str(i.get("valor") or "")).strip()[:16]} for i in itens]
        if len(itens) < 2:
            erros.append("provas precisa de 2 a 5 itens")
        variante = d.get("variante") if d.get("variante") in ("ficha", "recibo", "tiras", "fio") else "ficha"
        d = {"titulo": _item(d.get("titulo"), 34, tempo), "variante": variante, "itens": itens,
             "total": _item(d.get("total"), 18, tempo) if variante == "recibo" else None}
    elif modelo == "mapa_mundi":
        lugares_, faltam = [], []
        for x in (d.get("lugares") or [])[:3]:
            x = _item(x, 30, tempo)
            if not x:
                continue
            achado = _lugares.achar(x["texto"])
            if achado:
                lugares_.append({**x, "lat": achado["lat"], "lon": achado["lon"]})
            else:
                faltam.append(x["texto"])
        if faltam:
            erros.append(f"o atlas não tem {', '.join(faltam)}: escreva o nome do país, da cidade ou da região como "
                         "num mapa (ex.: \"Shanghai\", \"Brasil\"), ou use o modelo mapa")
        elif not lugares_:
            erros.append('mapa_mundi precisa de lugares = [{"texto": o nome do lugar, "t"}]')
        rota = bool(d.get("rota")) and len(lugares_) >= 2
        d = {"lugares": lugares_, "rota": rota,
             "_distancia": distancia_texto(sum(_lugares.distancia_km(a, b) for a, b in zip(lugares_, lugares_[1:])),
                                           lingua) if rota else ""}
    return d, erros


def eventos_de_som(modelo, dados) -> list:
    """(segundo dentro da animação, som, nível) de cada momento que pede som. Nível: "forte" (o acento: o carimbo, a
    palavra batida), "medio" ou "suave", calibrados contra a voz no render (animacoes.NIVEL_DO_SOM)."""
    d = dados or {}
    e = []
    if modelo == "secao":
        e.append((_t(d.get("titulo")), "passagem", "medio"))
    elif modelo == "nome":
        e.append((_t(d.get("nome")), "passagem", "suave"))
    elif modelo == "data":
        e.append((_t(d.get("data")), "carimbo" if d.get("variante") != "canto" else "tecla", "forte"))
    elif modelo == "termo":
        e.append((_t(d.get("termo")), "maquina", "suave"))
    elif modelo == "pergunta":
        e.append((_t(d.get("pergunta")), "pop", "medio"))
    elif modelo == "impacto":
        e.append((max(_t(d.get("palavra")) - 0.05, 0), "slam", "forte"))
    elif modelo == "rede":
        e += [(_t(n), "pop", "suave") for n in d.get("nos") or []]
    elif modelo == "ticker":
        e.append((_t(d.get("manchete")), "bipe", "medio"))
    elif modelo == "quiz":
        e += [(_t(o), "tecla", "suave") for o in d.get("opcoes") or []]
        if d.get("certa"):
            e.append((_t(d["certa"]), "sino", "medio"))
    elif modelo == "teaser":
        e.append((_t(d.get("titulo")), "passagem", "suave"))
    elif modelo == "chamada":
        t = _t(d.get("texto") or {}) or 0.3
        e += [(t + 0.9, "clique", "medio"), (t + 1.7, "sino", "medio")]
    elif modelo == "carrossel":
        e += [(_t(x), "foto", "suave") for x in d.get("itens") or []]
    elif modelo == "foto":
        e.append((max(_t(d.get("legenda") or {}) - 0.3, 0), "foto", "medio"))
    elif modelo == "provas":
        som = {"recibo": "maquina", "tiras": "papel", "fio": "papel"}.get(d.get("variante"), "maquina")
        e += [(_t(x), som, "suave") for x in d.get("itens") or []]
        if (d.get("total") or {}).get("texto"):
            e.append((_t(d["total"]), "carimbo", "forte"))
    elif modelo == "mapa_mundi":
        e += [(_t(x), "ping", "medio") for x in d.get("lugares") or []]
    return e


def para_json(d) -> str:
    return json.dumps(d, ensure_ascii=False)
