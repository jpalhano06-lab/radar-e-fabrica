"""O vídeo vai para a pasta logo depois do kit, e o que ficou sem entrega é entregue quando a fábrica liga
(pedido do usuário em 2026-11-09: "o vídeo depois de feito demora muito pra ir pra pasta")."""
import json
import os
import time

from fabrica import api


def _pronto(raiz, nome, entregue=None, idade_dias=0):
    pasta = raiz / nome
    pasta.mkdir()
    final = pasta / "final.mp4"
    final.write_bytes(b"mp4")
    quando = time.time() - idade_dias * 86400
    os.utime(final, (quando, quando))
    if entregue is not None:
        e = pasta / "entrega_pc.json"
        e.write_text(json.dumps({"video": "x"}), encoding="utf-8")
        os.utime(e, (quando + entregue, quando + entregue))
    return pasta


def test_acha_so_o_pronto_recente_sem_entrega(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    monkeypatch.setattr(api, "_ler_criacao", lambda nome: {"status": "processando"} if nome == "criando" else {})
    _pronto(tmp_path, "sem-entrega")
    _pronto(tmp_path, "entregue", entregue=60)
    _pronto(tmp_path, "entrega-velha", entregue=-60)       # o vídeo foi refeito depois da entrega
    _pronto(tmp_path, "antigo", idade_dias=10)
    _pronto(tmp_path, "criando")
    (tmp_path / "sem-video").mkdir()
    assert api.entregas_que_faltam() == ["entrega-velha", "sem-entrega"]


def test_a_entrega_vem_antes_das_capas_e_dos_shorts(monkeypatch):
    ordem = []
    monkeypatch.setattr(api, "Projeto", lambda nome: nome)
    monkeypatch.setattr(api.publicacao, "gerar", lambda pr, log=print, forcar=False: ordem.append("kit"))
    monkeypatch.setattr(api.entrega_pc, "entregar", lambda pr, log=print: ordem.append("entrega"))
    monkeypatch.setattr(api.entrega_pc, "config", lambda pr: {"so_o_video": True})
    monkeypatch.setattr(api.thumbnail, "gerar", lambda pr, log=print: ordem.append("capas"))
    monkeypatch.setattr(api.shorts, "config", lambda pr: {"ativo": True})
    monkeypatch.setattr(api.shorts, "gerar", lambda pr, log=print: ordem.append("shorts"))
    monkeypatch.setattr(api.drive, "enviar", lambda pr, log=print: None)
    monkeypatch.setattr(api.faxina, "faxinar", lambda log=print: None)
    api._PUBLICANDO.discard("v")
    api.iniciar_publicacao("v")
    for _ in range(100):
        if "v" not in api._PUBLICANDO:
            break
        time.sleep(0.02)
    assert ordem == ["kit", "entrega", "capas", "shorts"]          # com so_o_video, a entrega não repete no fim
