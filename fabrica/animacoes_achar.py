"""O que a fábrica acha sozinha na narração para virar animação, sem o agente de roteiro ter marcado a cena.

Do estudo da Dotti (2026-11-22): as edições dela saem de famílias com prioridade (seções, fatos, datas, listas, nomes,
termos, rankings, foto em destaque, citações, contrastes, karaokê, perguntas e impactos). Aqui cada família tem um
detector barato, sem modelo de linguagem, que olha a fala de cada cena e devolve a forma indicada e uma dica para o
modelo preencher. Uma cena vira no máximo uma candidata (a família mais forte), e todas passam pelo ritmo
(`animacoes.espacar`: 5 s livres e no máximo 6 por minuto).

As palavras funcionais (FUNCIONAIS) ficam de fora de termo, nome e destaque, em inglês, português e espanhol.
"""
import re
import unicodedata

from . import lugares

# palavras que nunca viram destaque nem termo: artigos, preposições, pronomes, conjunções e advérbios de ligação
FUNCIONAIS = {
    "en": set("""a an the and or but nor so yet for of to in on at by from with without into onto over under about
        above below between among through during before after since until while as than then there here this that these
        those it its they them their he him his she her we us our you your i me my mine is are was were be been being
        am do does did done have has had having will would shall should can could may might must not no yes very just
        also only even still already again ever never always often more most less least much many some any all each
        every both either neither other another such what which who whom whose when where why how if because though
        although unless whether up down out off now once well too quite rather almost enough""".split()),
    "pt": set("""a o as os um uma uns umas e ou mas nem que de do da dos das em no na nos nas por pelo pela pelos pelas
        para pra com sem sob sobre entre até ate após apos desde durante antes depois ao aos à às este esta estes estas
        esse essa esses essas aquele aquela aqueles aquelas aquilo isto isso ele ela eles elas nós nos vós voce você
        vocês voces eu me mim meu minha meus minhas seu sua seus suas nosso nossa lhe lhes se é e era foi ser sido estar
        está esta estava ter tem tinha há ha não nao sim muito muita muitos muitas pouco mais menos já ja ainda também
        tambem só so sempre nunca quando onde como porque porquê qual quais quem cujo então entao aqui ali lá la cá
        tão tao tanto tudo todo toda todos todas nada algo alguém algum alguma cada outro outra outros outras mesmo
        mesma bem mal agora logo assim""".split()),
    "es": set("""a o el la los las un una unos unas y e u ni que de del en por para con sin sobre entre hasta desde
        durante antes después despues al este esta estos estas ese esa esos esas aquel aquella aquellos aquellas esto
        eso aquello él ella ellos ellas nosotros vosotros usted ustedes yo me mi mis tu tus su sus nuestro nuestra le
        les se es era fue ser sido estar está estaba tener tiene tenía hay no sí si muy mucho mucha muchos muchas poco
        más menos ya aún aun también solo sólo siempre nunca cuando donde como porque cuál cual cuáles quién quien
        entonces aquí ahí allí allá tan tanto todo toda todos todas nada algo alguien algún alguna cada otro otra otros
        otras mismo misma bien mal ahora luego así""".split()),
}

ORDEM = ("secao", "chamada", "mapa_mundi", "data", "numero", "nome", "termo", "foto", "pergunta", "karaoke",
         "impacto", "teaser")
# a família mais forte escolhe o lugar primeiro no ritmo; as marcadas pelo agente de roteiro valem 2 a 4
PRIORIDADE = {"secao": 5.0, "chamada": 4.5, "mapa_mundi": 1.95, "data": 1.9, "numero": 1.8, "nome": 1.7, "termo": 1.6,
              "foto": 1.5, "pergunta": 1.4, "karaoke": 1.3, "impacto": 1.2, "teaser": 1.1}
DESLIGADAS_PADRAO = ("teaser",)  # o título da seção seguinte já diz o que vem; o teaser liga no config
SECAO_A_CADA = 90.0  # segundos: no máximo um título de capítulo nesse intervalo (os blocos do roteiro têm uns 50 s)
CHAMADA_A_CADA = 300.0  # segundos: o inscreva-se não aparece de novo antes disso

_INSCREVER = re.compile(r"\b(subscrib\w*|inscrev\w*|inscreva\w*|suscrib\w*|suscríbe\w*|ative o sino|activa la campana|"
                        r"hit the bell|turn on notifications)\b", re.I)
_TERMO = {
    "en": re.compile(r"\b(?:known as|called|so-called|termed|dubbed|nicknamed|the term)\s+(?:the |a |an )?[\"“']?"
                     r"([A-Za-z][\w'-]*(?:\s+[A-Za-z][\w'-]*){0,2})", re.I),
    "pt": re.compile(r"\b(?:chamad[oa]s? de|conhecid[oa]s? como|apelidad[oa]s? de|o chamado|a chamada|o termo|"
                     r"o que se chama de)\s+(?:o |a |um |uma )?[\"“']?(\w[\w'-]*(?:\s+\w[\w'-]*){0,2})", re.I),
    "es": re.compile(r"\b(?:llamad[oa]s?|conocid[oa]s? como|denominad[oa]s?|apodad[oa]s?|el llamado|la llamada|"
                     r"el término)\s+(?:el |la |un |una )?[\"“']?(\w[\w'-]*(?:\s+\w[\w'-]*){0,2})", re.I),
}
_ANO_EM_PALAVRAS = {
    "en": re.compile(r"\b(?:in|since|by|until|from|of|around|circa)\s+((?:eleven|twelve|thirteen|fourteen|fifteen|"
                     r"sixteen|seventeen|eighteen|nineteen|twenty)[ -](?:hundred|oh[ -]\w+|ten|eleven|twelve|thirteen|"
                     r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
                     r"eighty|ninety)(?:[ -](?:one|two|three|four|five|six|seven|eight|nine))?|two thousand"
                     r"(?: and)?(?: (?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
                     r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty(?:[ -]\w+)?))?)\b", re.I),
    "pt": re.compile(r"\b(?:em|de|desde|até|ate|no ano de|o ano de)\s+((?:mil (?:quinhentos|seiscentos|setecentos|"
                     r"oitocentos|novecentos)|dois mil)(?: e (?:\w+)(?: e \w+)?)?)\b(?! (?:reais|dólares|dolares|euros|"
                     r"pessoas|quilos|metros|quilômetros|vezes|anos))", re.I),
    "es": re.compile(r"\b(?:en|de|desde|hasta|el año|año)\s+((?:mil (?:quinientos|seiscientos|setecientos|ochocientos|"
                     r"novecientos)|dos mil)(?: (?:y )?\w+(?: y \w+)?)?)\b(?! (?:dólares|dolares|euros|personas|kilos|"
                     r"metros|veces|años))", re.I),
}
_ANO_EM_ALGARISMOS = re.compile(r"\b(1[5-9]\d\d|20[0-4]\d)\b")
_MESES = set("""january february march april may june july august september october november december monday tuesday
    wednesday thursday friday saturday sunday janeiro fevereiro março abril maio junho julho agosto setembro outubro
    novembro dezembro segunda terça quarta quinta sexta sábado domingo enero febrero marzo mayo junio julio
    septiembre octubre noviembre diciembre lunes martes miércoles jueves viernes""".split())


def _normal(texto) -> str:
    return unicodedata.normalize("NFKD", str(texto).lower()).encode("ascii", "ignore").decode()


def _frases(texto):
    return [f.strip() for f in re.findall(r"[^.!?…]+[.!?…]*", str(texto or "")) if f.strip()]


def funcional(palavra, lingua) -> bool:
    p = str(palavra).lower().strip(".,;:!?\"'“”()")
    return p in FUNCIONAIS.get(lingua, FUNCIONAIS["en"]) or _normal(p) in {_normal(x) for x in FUNCIONAIS.get(lingua, ())}


def ano(texto, lingua) -> str:
    """O ano que a fala cita ("in nineteen eighty-four", "em mil novecentos e trinta", "1984"), ou ""."""
    achado = _ANO_EM_ALGARISMOS.search(str(texto or ""))
    if achado:
        return achado.group(1)
    regra = _ANO_EM_PALAVRAS.get(lingua)
    achado = regra.search(str(texto or "")) if regra else None
    return achado.group(1) if achado else ""


def termo(texto, lingua) -> str:
    """O termo que a fala apresenta ("a practice known as short selling"), sem as palavras funcionais do fim."""
    regra = _TERMO.get(lingua)
    achado = regra.search(str(texto or "")) if regra else None
    if not achado:
        return ""
    palavras = re.split(r"[\s]+", re.split(r"[,.;:!?\"”]", achado.group(1))[0].strip())
    while palavras and funcional(palavras[-1], lingua):
        palavras.pop()
    while palavras and funcional(palavras[0], lingua):
        palavras.pop(0)
    termo_ = " ".join(palavras)
    return termo_ if len(termo_) >= 4 else ""


def nomes(texto, lingua, conhecidos=()) -> list:
    """Nomes próprios citados no meio da frase: duas a quatro palavras com maiúscula seguidas ("Elon Musk",
    "General Motors"), e os nomes de pessoas reais que o mapa do roteiro lista. Lugar do atlas não conta (vira mapa)."""
    achados = []
    normal = _normal(texto)
    for nome_ in conhecidos:
        if nome_ and _normal(nome_) in normal and nome_ not in achados:
            achados.append(nome_)
    for frase in _frases(texto):
        palavras = frase.split()
        # a primeira palavra da frase tem maiúscula de qualquer jeito, mas o nome pede duas seguidas ("Elon Musk said");
        # "Then General Motors" passa porque "Then" é palavra funcional e não abre nome
        i = 0
        while i < len(palavras):
            j = i
            while j < len(palavras) and re.match(r"^[A-ZÀ-ÖØ-Þ][\w'’-]+[,.;:!?]?$", palavras[j]) and \
                    not funcional(palavras[j], lingua) and _normal(palavras[j].strip(",.;:!?")) not in _MESES:
                j += 1
                if palavras[j - 1][-1] in ",.;:!?":
                    break
            if 2 <= j - i <= 4:
                nome_ = " ".join(p.strip(",.;:!?") for p in palavras[i:j])
                if not lugares.achar(nome_) and nome_ not in achados:
                    achados.append(nome_)
            i = max(j, i + 1)
    return achados


def _frases_inteiras(texto, comeca_frase=True):
    """As frases da fala da cena que estão inteiras nela: a primeira só conta se a cena começa uma frase (a cena
    anterior terminou com ponto), e a última só se termina com pontuação. A fala é cortada em cenas no meio da frase,
    e "floor." (o fim de uma frase da cena anterior) não é frase de impacto."""
    frases = _frases(texto)
    if frases and not comeca_frase:
        frases = frases[1:]
    return [f for f in frases if f[-1:] in ".!?…"]


def pergunta(texto, comeca_frase=True) -> str:
    for frase in _frases_inteiras(texto, comeca_frase):
        if frase.endswith("?") and 4 <= len(frase.split()) <= 18:
            return frase
    return ""


def impacto(texto, lingua, comeca_frase=True) -> str:
    """A frase curta que bate forte: 1 a 3 palavras, com pelo menos uma de verdade (não só "But." ou "So.")."""
    for frase in _frases_inteiras(texto, comeca_frase):
        palavras = frase.rstrip(".!…").split()
        if 1 <= len(palavras) <= 3 and frase[-1:] in ".!" and frase[:1].isupper() and \
                any(len(p) >= 4 and not funcional(p, lingua) for p in palavras):
            return frase.rstrip(".!… ")
    return ""


def karaoke(texto, comeca_frase=True) -> str:
    """A frase exclamada de 5 a 12 palavras: a que se lê junto com a voz."""
    for frase in _frases_inteiras(texto, comeca_frase):
        if frase.endswith("!") and 5 <= len(frase.split()) <= 12:
            return frase
    return ""


def _imagem(cena):
    midia = cena.get("midia") or {}
    return midia.get("capa") or (midia.get("arquivo") if midia.get("tipo") in ("imagem", "foto") else "")


def candidatas(cenas, lingua, mapa_do_roteiro=None, desligadas=(), numero_que_pesa=None) -> list:
    """[(cena, família, forma indicada, dica para o modelo)] na ordem das cenas, no máximo uma por cena.

    mapa_do_roteiro: o roteiro_mapa.json (os blocos com nome, para o título de seção, e as pessoas reais).
    numero_que_pesa: o detector de número (animacoes.numero_que_pesa), para a família numero."""
    mapa_do_roteiro = mapa_do_roteiro or {}
    blocos = {b.get("id"): b for b in mapa_do_roteiro.get("blocos") or []}
    pessoas = [p for p in mapa_do_roteiro.get("pessoas_reais") or [] if isinstance(p, str)]
    desligadas = set(desligadas)
    vistos_nomes, vistos_lugares, saida = set(), set(), []
    ultima_secao = ultima_chamada = None
    anterior_bloco = None
    ordem_dos_blocos = [b.get("id") for b in mapa_do_roteiro.get("blocos") or []]
    for k, c in enumerate(cenas):
        texto = c.get("texto") or ""
        achou = None
        bloco = c.get("bloco")
        novo_bloco = bloco is not None and bloco != anterior_bloco
        anterior_bloco = bloco if bloco is not None else anterior_bloco
        comeca_frase = k == 0 or str(cenas[k - 1].get("texto") or "").rstrip()[-1:] in ".!?…"
        for familia in ORDEM:
            if familia in desligadas:
                continue
            if familia == "secao" and novo_bloco and k > 0 and (blocos.get(bloco) or {}).get("nome") and \
                    (ultima_secao is None or c["ini"] - ultima_secao >= SECAO_A_CADA):
                ultima_secao = c["ini"]
                numero = ordem_dos_blocos.index(bloco) + 1 if bloco in ordem_dos_blocos else None
                achou = ("secao", f'título do capítulo: "{blocos[bloco]["nome"]}"' + (f" (número {numero})" if numero else "")
                         + "; ponha o t na primeira palavra da fala")
            elif familia == "chamada" and _INSCREVER.search(texto) and \
                    (ultima_chamada is None or c["ini"] - ultima_chamada >= CHAMADA_A_CADA):
                ultima_chamada = c["ini"]
                achou = ("chamada", "a fala pede para se inscrever no canal")
            elif familia == "mapa_mundi":
                novos = [l for l in lugares.lugares_no_texto(texto) if l["nome"] not in vistos_lugares]
                if novos:
                    vistos_lugares.update(l["nome"] for l in novos)
                    rota = len(novos) >= 2
                    achou = ("mapa_mundi", "lugares citados: " + ", ".join(l["nome"] for l in novos[:3])
                             + ("; com rota de um ao outro" if rota else ""))
            elif familia == "data":
                a = ano(texto, lingua)
                if a:
                    achou = ("data", f'o ano que a fala cita: "{a}" (escreva em algarismos)')
            elif familia == "numero" and numero_que_pesa:
                n = numero_que_pesa(texto, lingua)
                if n:
                    achou = ("numero", f"card do número que a narração fala: {n}")
            elif familia == "nome":
                novos = [n for n in nomes(texto, lingua, pessoas) if n not in vistos_nomes]
                if novos:
                    vistos_nomes.add(novos[0])
                    achou = ("nome", f'a tarja do nome "{novos[0]}" (com o que ele é, se a fala disser)')
            elif familia == "termo":
                t = termo(texto, lingua)
                if t:
                    achou = ("termo", f'o termo apresentado na fala: "{t}"')
            elif familia == "foto" and _imagem(c) and c.get("exato") and str(c.get("sujeito") or "")[:1].isupper():
                achou = ("foto", f'a foto de "{c["sujeito"]}" em destaque, com a legenda')
            elif familia == "pergunta":
                p = pergunta(texto, comeca_frase)
                if p:
                    achou = ("pergunta", f'a pergunta da fala: "{p}"')
            elif familia == "karaoke":
                f = karaoke(texto, comeca_frase)
                if f:
                    achou = ("karaoke", f'a frase para ler junto: "{f}"')
            elif familia == "impacto":
                f = impacto(texto, lingua, comeca_frase)
                if f:
                    achou = ("impacto", f'a frase curta de impacto: "{f}"')
            elif familia == "teaser":
                seguinte = next((x for x in cenas[k + 1:] if x.get("bloco") != bloco), None)
                b = blocos.get((seguinte or {}).get("bloco")) or {}
                if seguinte and b.get("nome") and 8 <= seguinte["ini"] - c["ini"] <= 16:
                    achou = ("teaser", f'o que vem a seguir: "{b["nome"]}"')
            if achou:
                break
        if achou:
            saida.append((c, achou[0], achou[0], achou[1]))
    return saida
