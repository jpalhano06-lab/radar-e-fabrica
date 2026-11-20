"""Narração pelo OpenSpeaker (ai33.pro), a alternativa barata à GenAIPro (troca pedida pelo usuário em 2026-11-17).

O que estes testes seguram: o prefixo do provedor no voice_id (os perfis guardam o id cru da ElevenLabs), o
limite de velocidade, a tarefa retomada que não é cobrada duas vezes, o tempo das palavras vindo do json ou do
srt, e o preço do crédito, que é de outro pacote e não pode cair no da GenAIPro.
"""
import json

import pytest

from fabrica import custos_reais, openspeaker


@pytest.fixture(autouse=True)
def sem_marca_de_transcricao(tmp_path, monkeypatch):
    """O aviso de transcrição pendurada fica num arquivo da pasta da fábrica: nos testes ele vai para a pasta
    temporária, senão um teste marcaria a conta de verdade como pendurada e os outros veriam a marca dele."""
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "openspeaker_transcricao.json")
    monkeypatch.setattr(openspeaker, "_transcricao_pendurada", False)
    # a memória de fila cheia é escrita dentro de _criar: sem zerar aqui, um teste condenava a conta nos seguintes
    monkeypatch.setattr(openspeaker, "_vagas_cheias_em", 0.0)


# ---------------------------------------------------------------- voz e corpo da tarefa

def test_id_cru_da_elevenlabs_ganha_o_prefixo():
    assert openspeaker.voz_prefixada("hpp4J3VqNfWAUOO0d1Us") == "elevenlabs_hpp4J3VqNfWAUOO0d1Us"


def test_id_que_ja_tem_prefixo_fica_como_esta():
    for voz in ("minimax_male-qn-qingse", "clone_123", "edge_vi-VN-HoaiMyNeural"):
        assert openspeaker.voz_prefixada(voz) == voz


def test_velocidade_fica_dentro_do_que_a_api_aceita():
    assert openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc", "velocidade": 2.0})["speed"] == 1.5
    assert openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc", "velocidade": 0.1})["speed"] == 0.5


def test_corpo_pede_a_transcricao(monkeypatch):
    """Sem nada no config.yaml, a transcrição é pedida (é ela que mede o tempo de cada palavra)."""
    monkeypatch.setattr(openspeaker, "config_geral", lambda: {})
    corpo = openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc"})
    assert corpo["with_transcript"] == "true" and corpo["text"] == "oi"


def test_transcricao_desligada_no_config_sai_do_corpo(monkeypatch):
    monkeypatch.setattr(openspeaker, "config_geral", lambda: {"openspeaker": {"transcricao": False}})
    assert openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc"})["with_transcript"] == "false"


def test_fila_pendurada_para_de_pedir_transcricao(monkeypatch):
    """Tarefa pendurada não libera a vaga: com 20 presas, a conta toda para com queue_limit_exceeded."""
    monkeypatch.setattr(openspeaker, "_transcricao_pendurada", True)
    assert openspeaker.corpo_da_tarefa("oi", {"voice_id": "abc"})["with_transcript"] == "false"


def test_sem_voz_no_perfil_explica_o_que_fazer():
    with pytest.raises(SystemExit) as erro:
        openspeaker.corpo_da_tarefa("oi", {"voice_id": "COLE AQUI"})
    assert "voz.voice_id" in str(erro.value)


# ---------------------------------------------------------------- tempo das palavras

def test_json_de_palavras_em_segundos():
    palavras = openspeaker.ler_json_de_palavras({"words": [{"word": "oi", "start": 0.0, "end": 0.4}]})
    assert palavras == [("oi", 0.0, 0.4)]


def test_json_em_milissegundos_vira_segundos():
    palavras = openspeaker.ler_json_de_palavras([{"text": "bom", "start": 12000, "end": 12500}])
    assert palavras == [("bom", 12.0, 12.5)]


def test_json_por_trechos():
    dados = {"segments": [{"words": [{"word": "a", "start": 0, "end": 1}]},
                          {"words": [{"word": "b", "start": 1, "end": 2}]}]}
    assert [p[0] for p in openspeaker.ler_json_de_palavras(dados)] == ["a", "b"]


def test_json_estragado_nao_derruba():
    assert openspeaker.ler_json_de_palavras({"nada": 1}) == []
    assert openspeaker.ler_json_de_palavras([{"word": "sem tempo"}]) == []


# ---------------------------------------------------------------- narração

class _Resposta:
    def __init__(self, dados=None, conteudo=b""):
        self._dados, self.content = dados or {}, conteudo

    def json(self):
        return self._dados

    def raise_for_status(self):
        pass


def _api_falsa(monkeypatch, tmp_path, srt="1\n00:00:00,000 --> 00:00:01,000\noi mundo\n", custo=224):
    """A API respondendo como a documentação descreve: tarefa criada, tarefa pronta, áudio e legenda."""
    pedidos = []

    def pedir(metodo, caminho, **kw):
        pedidos.append((metodo, caminho))
        if caminho == "/v3/text-to-speech":
            return _Resposta({"success": True, "task_id": "tarefa-1"})
        if caminho.startswith("/v1/task/"):
            return _Resposta({"id": "tarefa-1", "status": "done", "credit_cost": custo,
                              "metadata": {"audio_url": "https://x/a.mp3", "srt_url": "https://x/a.srt"}})
        raise AssertionError(f"pedido inesperado: {caminho}")

    def baixar(url, **kw):
        return _Resposta(conteudo=srt.encode("utf-8") if url.endswith(".srt") else b"MP3")

    monkeypatch.setattr(openspeaker, "_pedir", pedir)
    monkeypatch.setattr(openspeaker.httpx, "get", baixar)
    monkeypatch.setattr(openspeaker, "_arquivo_velocidade", lambda: tmp_path / "openspeaker_vozes.json")
    return pedidos


def test_narrar_grava_o_audio_e_devolve_os_creditos_cobrados(tmp_path, monkeypatch):
    _api_falsa(monkeypatch, tmp_path)
    mp3 = tmp_path / "bloco.mp3"
    palavras, creditos = openspeaker.narrar("oi mundo", {"voice_id": "abc"}, mp3, log=lambda *_: None)
    assert mp3.read_bytes() == b"MP3"
    assert creditos == 224  # o credit_cost da própria tarefa, não uma estimativa
    assert [p[0] for p in palavras] == ["oi", "mundo"]


def test_tarefa_retomada_nao_entra_na_conta_de_novo(tmp_path, monkeypatch):
    pedidos = _api_falsa(monkeypatch, tmp_path)
    mp3 = tmp_path / "bloco.mp3"
    corpo = openspeaker.corpo_da_tarefa("oi mundo", {"voice_id": "abc"})
    mp3.with_name(mp3.name + ".tarefa.json").write_text(
        json.dumps({"id": "tarefa-1", "corpo": corpo}), encoding="utf-8")
    palavras, creditos = openspeaker.narrar("oi mundo", {"voice_id": "abc"}, mp3, log=lambda *_: None)
    assert creditos == 0  # a tarefa já foi paga quando foi criada
    assert palavras and ("POST", "/v3/text-to-speech") not in pedidos  # e nenhuma tarefa nova foi criada


def test_anotacao_some_quando_o_audio_chega(tmp_path, monkeypatch):
    _api_falsa(monkeypatch, tmp_path)
    mp3 = tmp_path / "bloco.mp3"
    openspeaker.narrar("oi mundo", {"voice_id": "abc"}, mp3, log=lambda *_: None)
    assert not mp3.with_name(mp3.name + ".tarefa.json").exists()


def test_tarefa_com_erro_explica_em_portugues(tmp_path, monkeypatch):
    _api_falsa(monkeypatch, tmp_path)
    monkeypatch.setattr(openspeaker, "_pedir", lambda m, c, **kw: _Resposta(
        {"success": True, "task_id": "tarefa-1"} if c == "/v3/text-to-speech"
        else {"status": "error", "error_message": "sem créditos"}))
    with pytest.raises(SystemExit) as erro:
        openspeaker.narrar("oi", {"voice_id": "abc"}, tmp_path / "b.mp3", log=lambda *_: None)
    assert "sem créditos" in str(erro.value)


def test_audio_pronto_e_transcricao_atrasada_segue_sem_ela(tmp_path, monkeypatch):
    """A fila de transcrição do OpenSpeaker parou em 2026-11-18 e a tarefa ficava "doing" com o áudio pronto.

    Sem isto, cada bloco esperava os 20 minutos do limite, errava e tentava de novo, sem entregar narração."""
    _api_falsa(monkeypatch, tmp_path)
    monkeypatch.setattr(openspeaker, "_pedir", lambda m, c, **kw: _Resposta(
        {"success": True, "task_id": "tarefa-1"} if c == "/v3/text-to-speech"
        else {"id": "tarefa-1", "status": "doing", "progress": 90, "credit_cost": 224,
              "metadata": {"audio_url": "https://x/a.mp3", "transcript_status": "processing"}}))
    monkeypatch.setattr(openspeaker, "ESPERA_DA_TRANSCRICAO", 0)
    mp3 = tmp_path / "bloco.mp3"
    palavras, creditos = openspeaker.narrar("oi mundo", {"voice_id": "abc"}, mp3, log=lambda *_: None)
    assert mp3.read_bytes() == b"MP3"      # o áudio que já estava pago vem para o disco
    assert palavras == []                   # sem transcrição: narracao estima o tempo pelas pausas
    assert creditos == 224


def test_sem_audio_nenhum_a_espera_ainda_estoura(tmp_path, monkeypatch):
    """A saída sem transcrição não pode virar desculpa para aceitar tarefa que não gravou nada."""
    monkeypatch.setattr(openspeaker, "_pedir", lambda m, c, **kw: _Resposta(
        {"id": "tarefa-1", "status": "doing", "progress": 10, "metadata": {}}))
    monkeypatch.setattr(openspeaker, "ESPERA_DA_TRANSCRICAO", 0)
    with pytest.raises(SystemExit) as erro:
        openspeaker._esperar("tarefa-1", limite=0, log=lambda *_: None)
    assert "não terminou" in str(erro.value)


# ---------------------------------------------------------------- preço

def test_preco_do_openspeaker_nao_sai_do_pacote_da_genaipro():
    config = {"assinaturas": {"genaipro": {"preco_mensal": 22.0, "incluido_no_mes": 1000000}},
              "precos": {"openspeaker_por_mil_creditos": 0.00476}}
    assert custos_reais.preco_por_credito(config)[0] == pytest.approx(0.000022)
    assert custos_reais.preco_por_credito(config, "openspeaker")[0] == pytest.approx(0.00000476)


def test_pacote_comprado_do_openspeaker_manda_no_preco():
    config = {"assinaturas": {"openspeaker": {"plano": "OpenSpeaker 2,1 milhões", "preco_mensal": 10.0,
                                              "incluido_no_mes": 2100000}}}
    por_credito, origem = custos_reais.preco_por_credito(config, "openspeaker")
    assert por_credito == pytest.approx(10 / 2100000)
    assert "OpenSpeaker" in origem


def test_caractere_do_openspeaker_custa_1_29_credito():
    """1,29 é o que a API cobrou de verdade por um bloco de roteiro: 1,12 da fala mais a transcrição."""
    config = {"precos": {"openspeaker_por_mil_creditos": 0.00476}}
    taxa, _ = custos_reais.creditos_por_caractere(config, provedor="openspeaker")
    assert taxa == pytest.approx(1.29)
    # o caractere sai bem mais barato que os US$ 0,000022 da GenAIPro, mesmo gastando mais créditos
    assert custos_reais.preco_por_caractere(config, provedor="openspeaker")[0] == pytest.approx(0.0000061404)


# ---------------------------------------------------------------- as vagas da conta (2026-11-19)

class _RespostaHttp:
    """Resposta crua, como httpx devolve: tem status_code e text, que é o que _pedir olha."""

    def __init__(self, status_code, text="", dados=None):
        self.status_code, self.text, self._dados = status_code, text, dados or {}

    def json(self):
        return self._dados


FILA_CHEIA = ('{"success":false,"message":"You have too many tasks in queue (20/20), please wait for it to '
              'finish.","error":{"code":"queue_limit_exceeded"}}')


def test_fila_cheia_nao_insiste_em_segundos(monkeypatch):
    """Antes, queue_limit_exceeded virava 4 tentativas rápidas e um erro em 40s: a criação só tentava de novo."""
    pedidos = []

    def request(metodo, url, **kw):
        pedidos.append(url)
        return _RespostaHttp(429, FILA_CHEIA, json.loads(FILA_CHEIA))

    monkeypatch.setattr(openspeaker.httpx, "request", request)
    monkeypatch.setattr(openspeaker, "chave", lambda: "k")
    with pytest.raises(openspeaker.FilaCheia) as erro:
        openspeaker._pedir("POST", "/v3/text-to-speech")
    assert len(pedidos) == 1 and "vagas" in str(erro.value)


def _tarefa_presa(ident="presa-1", quando="2020-01-01T00:00:00.000Z", transcricao="processing"):
    return {"id": ident, "status": "doing", "created_at": quando, "text": "oi mundo",
            "metadata": {"audio_url": "https://x/a.mp3", "transcript_status": transcricao,
                         "v3": {"raw_voice_id": "elevenlabs_abc"}}}


def test_presa_na_transcricao_e_a_tarefa_com_audio_que_nunca_termina():
    assert openspeaker._presa_na_transcricao(_tarefa_presa())
    # a que já terminou não está presa, e a que ainda não gravou áudio também não (cancelar perderia a narração)
    assert not openspeaker._presa_na_transcricao({**_tarefa_presa(), "status": "done"})
    assert not openspeaker._presa_na_transcricao({"status": "doing", "metadata": {}})


def test_liberar_vagas_nao_cancela_a_tarefa_que_este_processo_espera(monkeypatch, tmp_path):
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "t.json")
    monkeypatch.setattr(openspeaker, "tarefas", lambda: [_tarefa_presa("minha"), _tarefa_presa("velha")])
    canceladas = []
    monkeypatch.setattr(openspeaker, "cancelar", lambda i: canceladas.append(i) or True)
    openspeaker._minhas.add("minha")
    try:
        assert openspeaker.liberar_vagas(log=lambda *_: None) == 1
    finally:
        openspeaker._minhas.discard("minha")
    assert canceladas == ["velha"]


def test_tarefa_recem_criada_nao_perde_a_vaga(monkeypatch, tmp_path):
    """Cancelar uma tarefa de agora mataria a narração que está gravando: só a presa há mais de 10 min sai."""
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "t.json")
    monkeypatch.setattr(openspeaker, "_idade", lambda t: 60)
    monkeypatch.setattr(openspeaker, "tarefas", lambda: [_tarefa_presa()])
    monkeypatch.setattr(openspeaker, "cancelar", lambda i: True)
    assert openspeaker.liberar_vagas(log=lambda *_: None) == 0


def test_fila_cheia_aproveita_a_tarefa_igual_sem_pagar_de_novo(monkeypatch, tmp_path):
    monkeypatch.setattr(openspeaker, "chave", lambda: "k")
    monkeypatch.setattr(openspeaker.httpx, "request",
                        lambda m, u, **kw: _RespostaHttp(429, FILA_CHEIA, json.loads(FILA_CHEIA)))
    monkeypatch.setattr(openspeaker, "tarefas", lambda: [_tarefa_presa("ja-paga")])
    corpo = openspeaker.corpo_da_tarefa("oi mundo", {"voice_id": "abc"})
    assert openspeaker._criar(corpo, log=lambda *_: None) == ("ja-paga", True)


def test_fila_cheia_sem_tarefa_igual_desiste_depois_do_limite(monkeypatch, tmp_path):
    monkeypatch.setattr(openspeaker, "chave", lambda: "k")
    monkeypatch.setattr(openspeaker.httpx, "request",
                        lambda m, u, **kw: _RespostaHttp(429, FILA_CHEIA, json.loads(FILA_CHEIA)))
    monkeypatch.setattr(openspeaker, "tarefas", lambda: [])
    monkeypatch.setattr(openspeaker, "ESPERA_POR_VAGA", -1)   # o limite já passou na primeira volta
    corpo = openspeaker.corpo_da_tarefa("oi mundo", {"voice_id": "abc"})
    with pytest.raises(openspeaker.FilaCheia):
        openspeaker._criar(corpo, log=lambda *_: None)


def test_transcricao_pendurada_vale_depois_de_reiniciar(monkeypatch, tmp_path):
    """O aviso em memória se perdia no reinício e a conta voltava a encher as 20 vagas em minutos."""
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "t.json")
    monkeypatch.setattr(openspeaker, "config_geral", lambda: {})
    openspeaker.marcar_transcricao_pendurada()
    monkeypatch.setattr(openspeaker, "_transcricao_pendurada", False)   # como se a fábrica tivesse reiniciado
    assert openspeaker.pedir_transcricao() is False
    # passadas as horas, a fábrica tenta a transcrição de novo: o problema é do lado deles e costuma passar
    monkeypatch.setattr(openspeaker, "HORAS_SEM_TRANSCRICAO", 0)
    assert openspeaker.pedir_transcricao() is True


def test_tarefa_pendurada_sai_da_fila_quando_o_audio_chega(tmp_path, monkeypatch):
    """Sem isso a vaga ficava ocupada para sempre, mesmo com o áudio já baixado."""
    _api_falsa(monkeypatch, tmp_path)
    monkeypatch.setattr(openspeaker, "_pedir", lambda m, c, **kw: _Resposta(
        {"success": True, "task_id": "tarefa-1"} if c == "/v3/text-to-speech"
        else {"id": "tarefa-1", "status": "doing", "credit_cost": 224,
              "metadata": {"audio_url": "https://x/a.mp3"}}))
    monkeypatch.setattr(openspeaker, "ESPERA_DA_TRANSCRICAO", 0)
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "t.json")
    canceladas = []
    monkeypatch.setattr(openspeaker, "cancelar", lambda i: canceladas.append(i) or True)
    openspeaker.narrar("oi mundo", {"voice_id": "abc"}, tmp_path / "bloco.mp3", log=lambda *_: None)
    assert canceladas == ["tarefa-1"]


def test_conta_travada_quando_as_vagas_estao_todas_ocupadas(monkeypatch, tmp_path):
    """É isto que manda o vídeo narrar na reserva (Fish) em vez de esperar vaga por horas."""
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "t.json")
    monkeypatch.setattr(openspeaker, "VAGAS_DA_CONTA", 2)
    monkeypatch.setattr(openspeaker, "tarefas", lambda: [_tarefa_presa("a"), _tarefa_presa("b")])
    monkeypatch.setattr(openspeaker, "cancelar", lambda i: False)   # a API deles não tem cancelamento
    assert openspeaker.conta_travada(log=lambda *_: None) is True


def test_conta_com_vaga_sobrando_nao_vai_para_a_reserva(monkeypatch, tmp_path):
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "t.json")
    monkeypatch.setattr(openspeaker, "VAGAS_DA_CONTA", 2)
    monkeypatch.setattr(openspeaker, "tarefas", lambda: [_tarefa_presa("a")])
    assert openspeaker.conta_travada(log=lambda *_: None) is False


def test_lista_de_tarefas_que_nao_responde_nao_troca_a_voz_do_canal(monkeypatch):
    """Falha de leitura não pode virar motivo para o vídeo sair com outra voz."""
    def explode():
        raise openspeaker.ErroOpenSpeaker("a lista não respondeu")
    monkeypatch.setattr(openspeaker, "tarefas", explode)
    assert openspeaker.conta_travada(log=lambda *_: None) is False


def test_vaga_que_abriu_depois_do_cancelamento_mantem_o_openspeaker(monkeypatch, tmp_path):
    monkeypatch.setattr(openspeaker, "_arquivo_transcricao", lambda: tmp_path / "t.json")
    monkeypatch.setattr(openspeaker, "VAGAS_DA_CONTA", 2)
    filas = [[_tarefa_presa("a"), _tarefa_presa("b")], [_tarefa_presa("b")]]
    monkeypatch.setattr(openspeaker, "tarefas", lambda: filas.pop(0) if len(filas) > 1 else filas[0])
    monkeypatch.setattr(openspeaker, "cancelar", lambda i: True)
    assert openspeaker.conta_travada(log=lambda *_: None) is False


# ---------------------------------------------------------------- a reserva da narração (narracao.voz_com_reserva)

def test_conta_travada_manda_o_video_para_a_fish(monkeypatch):
    from fabrica import narracao
    monkeypatch.setattr(openspeaker, "conta_travada", lambda log=print: True)
    voz = {"provedor": "openspeaker", "voice_id": "elevenlabs_abc", "velocidade": 1.1}
    nova = narracao.voz_com_reserva(voz, log=lambda *_: None)
    assert nova["provedor"] == "fish" and nova["voice_id"] == "" and nova["velocidade"] == 1.1


def test_openspeaker_com_vaga_grava_na_voz_do_canal(monkeypatch):
    from fabrica import narracao
    monkeypatch.setattr(openspeaker, "conta_travada", lambda log=print: False)
    voz = {"provedor": "openspeaker", "voice_id": "elevenlabs_abc"}
    assert narracao.voz_com_reserva(voz, log=lambda *_: None) is voz


def test_voz_de_outro_provedor_nao_e_mexida(monkeypatch):
    from fabrica import narracao
    monkeypatch.setattr(openspeaker, "conta_travada", lambda log=print: pytest.fail("nem devia olhar a conta"))
    voz = {"provedor": "genaipro", "voice_id": "abc"}
    assert narracao.voz_com_reserva(voz, log=lambda *_: None) is voz


def test_voz_da_fish_escolhida_no_perfil_vale_na_reserva(monkeypatch):
    """voz.voice_id_fish no perfil do canal: a reserva grava com ela em vez da voz padrão da Fish."""
    from fabrica import narracao
    monkeypatch.setattr(openspeaker, "conta_travada", lambda log=print: True)
    voz = {"provedor": "openspeaker", "voice_id": "elevenlabs_abc", "voice_id_fish": "fish-123"}
    assert narracao.voz_com_reserva(voz, log=lambda *_: None)["voice_id"] == "fish-123"


def test_fila_cheia_fica_lembrada_mesmo_com_a_listagem_fora(monkeypatch):
    """A listagem deles devolve 503 de vez em quando: sem memória, o vídeo não ia para a reserva."""
    def explode():
        raise openspeaker.ErroOpenSpeaker("503 Task polling temporarily busy")
    monkeypatch.setattr(openspeaker, "tarefas", explode)
    monkeypatch.setattr(openspeaker, "_vagas_cheias_em", openspeaker.time.time())
    assert openspeaker.conta_travada(log=lambda *_: None) is True
    # passada a memória, volta a perguntar à API em vez de condenar a conta para sempre
    monkeypatch.setattr(openspeaker, "MEMORIA_DA_FILA_CHEIA", 0)
    assert openspeaker.conta_travada(log=lambda *_: None) is False
