"""A busca rápida: só o começo tem a busca completa; depois dele, uma busca só e o que demora vai para a IA
(pedido do usuário em 2026-11-16)."""
import time
import types
from concurrent.futures import Future

from fabrica import midia


def _projeto(**midia_cfg):
    return types.SimpleNamespace(config={"midia": midia_cfg}, offline=False, perfil={})


def test_so_depois_do_comeco_e_com_a_ia_ligada():
    p = _projeto()
    assert not midia.busca_rapida(p, {"ini": 120})
    assert midia.busca_rapida(p, {"ini": 300})
    assert not midia.busca_rapida(types.SimpleNamespace(config={"ia": {"ativa": False}}, offline=False), {"ini": 900})
    assert not midia.busca_rapida(_projeto(busca_rapida_depois_de=0), {"ini": 900})


def _buscador(projeto, achados_por_busca):
    b = midia.Buscador.__new__(midia.Buscador)
    b.projeto, b.blocos, b.nomes, b.quantidade = projeto, {}, set(), 8
    b.cfg = {"fontes_video": ["pexels", "youtube"]}
    feitas, garimpos = [], []
    b._das_fontes = lambda tipo, busca, preferida=None, acervo=False: feitas.append(busca) or achados_por_busca
    b._do_garimpo = lambda busca: garimpos.append(busca) or []
    b._de_outro_item = lambda a, c: False
    return b, feitas, garimpos


def test_depois_do_comeco_uma_busca_so_e_sem_youtube():
    cena = {"n": 90, "ini": 600, "tipo": "foto_real", "busca": "candle tea light", "busca_alternativa": "candles",
            "sujeito": "tea lights on plate"}
    b, feitas, garimpos = _buscador(_projeto(), [])
    b.candidatos(cena)
    assert len(feitas) == 1 and garimpos == []
    b, feitas, garimpos = _buscador(_projeto(), [])
    b.candidatos({**cena, "ini": 10})
    assert len(feitas) > 1 and garimpos  # o começo segue com a busca completa, com o YouTube


def _feito(valor):
    f = Future()
    f.set_result(valor)
    return f


def test_passou_do_prazo_cancela_so_os_lotes_depois_do_comeco():
    p = _projeto(prazo_da_busca_min=1)
    lotes = [[{"n": 1, "ini": 10}], [{"n": 2, "ini": 400}], [{"n": 3, "ini": 20}]]
    futuros = [_feito({1: [0]}), Future(), _feito({3: [0]})]
    aplicados = []
    erro, cancelados = midia._aplicar_com_prazo(futuros, lotes, aplicados.append, p, time.time() - 120, lambda *_: None)
    assert erro is None and cancelados == {2}
    assert aplicados == [{1: [0]}, {3: [0]}]  # o começo nunca é cortado pelo prazo


def test_dentro_do_prazo_nada_e_cancelado():
    p = _projeto(prazo_da_busca_min=10)
    lotes = [[{"n": 2, "ini": 400}]]
    aplicados = []
    erro, cancelados = midia._aplicar_com_prazo([_feito({2: []})], lotes, aplicados.append, p, time.time(),
                                                lambda *_: None)
    assert cancelados == set() and aplicados == [{2: []}]
