"""narracao_no_video: false (perfil sem-narracao, o Canal de teste de 5 min do Radar, 2026-11-12): a voz do computador
só mede o tempo das cenas e entra muda na trilha do vídeo final."""
from types import SimpleNamespace

from fabrica import render


def _filtro(monkeypatch, tmp_path, perfil):
    comandos = []
    monkeypatch.setattr(render, "_preparar_voz", lambda projeto, base: tmp_path / "voz.wav")
    monkeypatch.setattr(render, "_musica", lambda *a, **k: None)
    monkeypatch.setattr(render, "rodar", lambda cmd, *a, **k: comandos.append(cmd))
    projeto = SimpleNamespace(perfil=perfil, caminho=lambda *partes: tmp_path / partes[-1])
    render._trilha(projeto, 10.0)
    return comandos[-1][comandos[-1].index("-filter_complex") + 1]


def test_sem_narracao_a_voz_entra_muda(monkeypatch, tmp_path):
    assert "volume=0[voz]" in _filtro(monkeypatch, tmp_path, {"narracao_no_video": False})


def test_com_narracao_a_voz_fica(monkeypatch, tmp_path):
    assert "volume=0" not in _filtro(monkeypatch, tmp_path, {})
