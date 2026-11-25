"""Uma de cada vez: a segunda entrada espera a primeira sair, e 0 no config desliga o limite."""
import threading
import time

from fabrica import tempos, vez


class Projeto:
    def __init__(self, config):
        self.config = config


def test_segunda_espera_a_primeira(monkeypatch):
    monkeypatch.setattr(vez, "_SEMAFOROS", {})
    esperas = []
    monkeypatch.setattr(tempos, "medir", lambda p, nome, log=None: _Medida(esperas, nome))
    ordem = []
    p = Projeto({"vez": {"teste": 1}})

    def trabalho(nome):
        with vez.na_vez("teste", p, log=lambda *_: None):
            ordem.append(f"entra {nome}")
            time.sleep(0.15)
            ordem.append(f"sai {nome}")

    a = threading.Thread(target=trabalho, args=("a",))
    a.start()
    time.sleep(0.03)
    b = threading.Thread(target=trabalho, args=("b",))
    b.start()
    a.join(); b.join()
    assert ordem == ["entra a", "sai a", "entra b", "sai b"]
    assert esperas == ["Esperando a vez: teste"]


def test_zero_desliga(monkeypatch):
    monkeypatch.setattr(vez, "_SEMAFOROS", {})
    p = Projeto({"vez": {"teste": 0}})
    with vez.na_vez("teste", p):
        with vez.na_vez("teste", p):   # sem limite, entra de novo sem travar
            pass
    assert "teste" not in vez._SEMAFOROS


def test_pausado_solta_a_vaga(monkeypatch):
    """O vídeo pausado DENTRO da etapa solta a vaga: o outro entra na hora, em vez de esperar a despausa."""
    monkeypatch.setattr(vez, "_SEMAFOROS", {})
    monkeypatch.setattr(tempos, "medir", lambda p, nome, log=None: _Medida([], nome))
    p = Projeto({"vez": {"teste": 1}})
    ordem, b_entrou = [], threading.Event()

    def pausado():
        with vez.na_vez("teste", p, log=lambda *_: None):
            ordem.append("entra a")
            with vez.solto(log=lambda *_: None):   # a pausa do vídeo
                b_entrou.wait(5)
            ordem.append("sai a")

    def outro():
        with vez.na_vez("teste", p, log=lambda *_: None):
            ordem.append("entra b")
            b_entrou.set()
            time.sleep(0.05)
            ordem.append("sai b")

    a = threading.Thread(target=pausado); a.start()
    time.sleep(0.05)
    b = threading.Thread(target=outro); b.start()
    a.join(5); b.join(5)
    assert ordem == ["entra a", "entra b", "sai b", "sai a"]
    assert vez._SEMAFOROS["teste"].acquire(blocking=False)   # ninguém ficou com a vaga


def test_log_da_solta_nao_solta_duas_vezes(monkeypatch):
    """O log da solta passa pelo log_w, que chama a pausa de novo: a segunda solta não pode liberar a mesma vaga."""
    monkeypatch.setattr(vez, "_SEMAFOROS", {})
    p = Projeto({"vez": {"teste": 1}})

    def log(_msg):
        with vez.solto(log=lambda *_: None):   # pausa dentro do log da própria solta
            pass

    with vez.na_vez("teste", p, log=lambda *_: None):
        with vez.solto(log=log):
            pass
    assert vez._SEMAFOROS["teste"].acquire(blocking=False)


class _Medida:
    def __init__(self, lista, nome):
        self.lista, self.nome = lista, nome

    def __enter__(self):
        self.lista.append(self.nome)

    def __exit__(self, *_):
        return False


def test_vagas_da_fabrica_somam_os_videos(monkeypatch):
    """imagens.processos é o total da fábrica: dois vídeos com 2 vagas não passam de 2 juntos (2026-11-22)."""
    monkeypatch.setattr(vez, "_GLOBAIS", {})
    dentro, maximo, trava = [0], [0], threading.Lock()

    def uma():
        vaga = vez.pegar("imagens", 2)
        try:
            with trava:
                dentro[0] += 1
                maximo[0] = max(maximo[0], dentro[0])
            time.sleep(0.05)
            with trava:
                dentro[0] -= 1
        finally:
            vez.soltar(vaga)

    fios = [threading.Thread(target=uma) for _ in range(6)]
    for f in fios:
        f.start()
    for f in fios:
        f.join()
    assert maximo[0] == 2


def test_vaga_zero_nao_limita(monkeypatch):
    monkeypatch.setattr(vez, "_GLOBAIS", {})
    assert vez.pegar("imagens", 0) is None
    vez.soltar(None)
    assert "imagens" not in vez._GLOBAIS


def test_etapas_lentas_juntas_sao_uma_de_cada_vez():
    """As medidas de 2026-11-22: trilha, narração, animações, clipes adiantados e garantia passaram de 2 vezes mais
    lentas com outro vídeo junto. A busca de acervo não (junto ela foi mais rápida)."""
    for nome in ("render_juntar", "conferencia_completadas", "render_clipes", "narracao", "garantia", "animacoes",
                 "trilha"):
        assert vez.PADRAO[nome] == 1
    assert "busca" not in vez.PADRAO
