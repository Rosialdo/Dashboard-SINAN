"""Nomes amigáveis e grupos da tela "Outras variáveis" (sinan/rotulos.py)."""

import pytest

from sinan import agravos as cat
from sinan import rotulos
from sinan.tabnet import ler_def


@pytest.mark.parametrize(("rotulo", "campo", "cnv", "esperado"), [
    ("Escolar SinanNET", "CS_ESCOL_N", "ESCOLARNET.CNV", "Escolaridade"),
    ("Sin.clín:Dor retro", "DOR_RETRO", "Sim_nao.cnv", "Dor atrás dos olhos"),
    ("Pré-ex:Hipert.art.", "HIPERTENSA", "Sim_nao.cnv", "Hipertensão arterial"),
    ("Conf.Desc pos2010", "CRITERIO", "CONFDESCDENG2011.CNV", "Critério de confirmação (após 2010)"),
    ("Conf.Desc ate2010", "CRITERIO", "CONFDESC.CNV", "Critério de confirmação (até 2010)"),
    ("Fx Etaria SINAN", "NU_IDADE_N", "FXIDAD10NET.CNV", "Faixa etária (padrão SINAN)"),
    # campos sem nome escrito à mão: limpeza automática
    ("Sin.clín:Calafrio", "CALAFRIO", "sim_nao.cnv", "Calafrio"),
    ("Res.ex. Sorologia", "RES_SORO_X", "Resultado.cnv", "Resultado exame Sorologia"),
    ("Tipo_de_exposicao", "TP_EXPO", "x.cnv", "Tipo de exposicao"),
])
def test_nome_amigavel(rotulo, campo, cnv, esperado):
    assert rotulos.nome_amigavel(rotulo, campo, cnv) == esperado


@pytest.mark.parametrize(("rotulo", "campo", "esperado"), [
    ("Sexo", "CS_SEXO", "Perfil do paciente"),
    ("Sin.clín:Febre", "FEBRE", "Sinais e sintomas"),
    ("Sin.clín:Calafrio", "CALAFRIO", "Sinais e sintomas"),
    ("Pré-ex:Asma", "ASMA", "Doenças pré-existentes"),
    ("Res.2ª Bacilosc.", "BACILOSC_2", "Exames de laboratório"),
    ("Evolução Outros Agravos", "EVOLUCAO", "Classificação e evolução"),
    ("Colaborador", "COLAB", "Outras informações"),  # "lab" no meio da palavra não é exame
    ("Altura", "ALTURA", "Outras informações"),       # "alta" só como palavra inteira
])
def test_grupo(rotulo, campo, esperado):
    assert rotulos.grupo(rotulo, campo) == esperado


def test_nenhum_nome_fica_com_sublinhado():
    """Em todas as fichas do catálogo, nenhum nome mostrado tem "_" nem fica vazio."""
    for ag in cat.AGRAVOS.values():
        for v in ler_def(ag.arquivo_def or ""):
            nome = rotulos.nome_amigavel(v.rotulo, v.campo, v.cnv)
            assert nome and "_" not in nome, (ag.codigo, v.rotulo)
            assert rotulos.grupo(v.rotulo, v.campo) in rotulos.GRUPOS


def test_api_variaveis_agrupada(cliente):
    lista = cliente.get("/api/variaveis?agravo=ACBI").json()
    assert lista and all({"id", "nome", "grupo", "rotulo", "campo"} <= set(v) for v in lista)
    ordem = [rotulos.GRUPOS.index(v["grupo"]) for v in lista]
    assert ordem == sorted(ordem)  # já vem na ordem dos grupos
    assert not any(v["campo"] in ("ID_AGRAVO", "ID_MUNICIP", "ID_MN_RESI") for v in lista)
    assert len({v["nome"] for v in lista}) == len(lista)  # nomes não se repetem
    assert lista[0]["nome"] == "Faixa etária (padrão SINAN)"  # opção principal vem primeiro
    d = cliente.get(f"/api/variavel?agravo=ACBI&id={lista[0]['id']}").json()
    assert d["rotulo"] == lista[0]["nome"]
