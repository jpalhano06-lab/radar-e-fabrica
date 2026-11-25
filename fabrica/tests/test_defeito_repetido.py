"""Erro de código que volta igual em toda tentativa para a criação, em vez de girar para sempre (cd-2, 24/11/2026:
42 tentativas de 5 em 5 min num ValueError do Pillow), e a miniatura PNG com texto gigante não derruba a busca."""
import contextlib
import io
import json

import pytest
from PIL import Image, PngImagePlugin

from fabrica import api, midia


@pytest.fixture
def etapa(monkeypatch, tmp_path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "projeto.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(api, "PROJETOS", tmp_path)
    monkeypatch.setattr(api, "_log_tarefa", lambda *a: None)
    monkeypatch.setattr(api, "_atualizar", lambda *a, **k: None)
    monkeypatch.setattr(api, "_esperar", lambda *a: None)


def test_o_mesmo_defeito_repetido_para_e_pede_voce(etapa):
    vezes = []

    def funcao():
        vezes.append(1)
        raise ValueError("Decompressed data too large for PngImagePlugin.MAX_TEXT_CHUNK")

    with pytest.raises(api.ParadaPrecisaDeVoce, match="MAX_TEXT_CHUNK"):
        api._etapa_tentando("t", "p", "Busca de acervo", funcao)
    assert len(vezes) == api.REPETICOES_DE_DEFEITO


def test_servico_fora_do_ar_continua_tentando(etapa):
    vezes = []

    def funcao():
        vezes.append(1)
        if len(vezes) <= api.REPETICOES_DE_DEFEITO + 3:
            raise RuntimeError("um serviço caiu")
        return "ok"

    assert api._etapa_tentando("t", "p", "Narração", funcao) == "ok"


def test_json_quebrado_de_servico_continua_tentando(etapa):
    vezes = []

    def funcao():
        vezes.append(1)
        if len(vezes) <= api.REPETICOES_DE_DEFEITO + 3:
            json.loads("<html>502</html>")
        return "ok"

    assert api._etapa_tentando("t", "p", "Roteiro", funcao) == "ok"


def test_defeitos_diferentes_nao_somam(etapa):
    vezes = []

    def funcao():
        vezes.append(1)
        if len(vezes) <= api.REPETICOES_DE_DEFEITO + 3:
            raise KeyError(f"cena {len(vezes)}")
        return "ok"

    assert api._etapa_tentando("t", "p", "Cenas", funcao) == "ok"


def test_miniatura_png_com_texto_gigante_fica_fora():
    info = PngImagePlugin.PngInfo()
    info.add_text("x", "A" * (PngImagePlugin.MAX_TEXT_CHUNK + 10), zip=True)
    b = io.BytesIO()
    Image.new("RGB", (4, 4)).save(b, "PNG", pnginfo=info)

    class Resposta:
        def raise_for_status(self):
            pass

        def iter_bytes(self):
            yield b.getvalue()

    class Cliente:
        @contextlib.contextmanager
        def stream(self, *a):
            yield Resposta()

    assert midia._miniatura(Cliente(), "x") is None
