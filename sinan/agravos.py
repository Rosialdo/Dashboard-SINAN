"""Catálogo dos agravos disponíveis no FTP do SINAN.

Para cada código de arquivo (ex.: DENG em DENGBR24.dbc) temos o nome por
extenso, o arquivo .def do TabNet com os rótulos oficiais e algumas regras
de interpretação.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Agravo:
    codigo: str
    nome: str
    arquivo_def: str | None = None
    # True quando toda notificação já é um caso (não há confirmação/descarte),
    # por exemplo tuberculose, hanseníase, violência e acidentes de trabalho.
    todos_casos: bool = False
    # campo com a evolução/encerramento do caso
    campo_evolucao: str = "EVOLUCAO"
    # códigos de CLASSI_FIN que contam como confirmados (None = deduz pelo rótulo)
    confirmados: frozenset[str] | None = None
    aviso: str | None = None


_AVISO_MALARIA = (
    "Na Amazônia Legal a malária é notificada no SIVEP-Malária, não no SINAN. "
    "Aqui aparecem só os casos registrados no SINAN (em geral poucos)."
)

AGRAVOS: dict[str, Agravo] = {a.codigo: a for a in [
    Agravo("DENG", "Dengue", "denguenet.def",
           confirmados=frozenset({"1", "2", "3", "4", "10", "11", "12"}),
           aviso="Os arquivos de dengue do DATASUS não incluem os casos descartados: "
                 "\"todas as notificações\" aqui equivale a casos prováveis. Antes de 2014 a "
                 "classificação usava outros nomes (dengue clássico, FHD...)."),
    Agravo("CHIK", "Chikungunya", "chiknon.def", confirmados=frozenset({"13"})),
    Agravo("ZIKA", "Zika vírus", "notindivinet.def", confirmados=frozenset({"1"})),
    Agravo("ACBI", "Acidente de trabalho com material biológico", "acidbionet.def", todos_casos=True),
    Agravo("ACGR", "Acidente de trabalho grave", "acidgravenet.def", todos_casos=True),
    Agravo("ANIM", "Acidente por animais peçonhentos", "animaispnet.def", todos_casos=True),
    Agravo("ANTR", "Atendimento antirrábico", "antirabnet.def", todos_casos=True),
    Agravo("BOTU", "Botulismo", "botunet.def"),
    Agravo("CANC", "Câncer relacionado ao trabalho", "drtcancernet.def", todos_casos=True),
    Agravo("CHAG", "Doença de Chagas aguda", "chagasnet.def"),
    Agravo("COLE", "Cólera", "coleranet.def"),
    Agravo("COQU", "Coqueluche", "coquenet.def"),
    Agravo("DCRJ", "Doença de Creutzfeldt-Jakob", "notindivinet.def"),
    Agravo("DERM", "Dermatoses ocupacionais", "drtdermatosenet.def", todos_casos=True),
    Agravo("DIFT", "Difteria", "difterinet.def"),
    Agravo("ESPO", "Esporotricose", "notindivinet.def"),
    Agravo("ESQU", "Esquistossomose", "esquisnet.def", todos_casos=True),
    Agravo("FMAC", "Febre maculosa", "fmacnet.def"),
    Agravo("FTIF", "Febre tifoide", "ftifoidenet.def"),
    Agravo("HANS", "Hanseníase", "hansnet.def", todos_casos=True, campo_evolucao="TPALTA_N"),
    Agravo("HANT", "Hantavirose", "hantanet.def"),
    Agravo("IEXO", "Intoxicação exógena", "intoxnet.def", confirmados=frozenset({"1"})),
    Agravo("LEIV", "Leishmaniose visceral", "leishvisnet.def"),
    Agravo("LEPT", "Leptospirose", "leptonet.def"),
    Agravo("LER", "LER/DORT", "drtlerdortnet.def", todos_casos=True),
    Agravo("LERD", "LER/DORT", "drtlerdortnet.def", todos_casos=True),
    Agravo("LTAN", "Leishmaniose tegumentar americana", "leishtegnet.def", todos_casos=True),
    Agravo("MALA", "Malária", "malarianet.def", aviso=_AVISO_MALARIA),
    Agravo("MENI", "Meningite", "meningenet.def"),
    Agravo("MENT", "Transtornos mentais relacionados ao trabalho", "drttransmentalnet.def", todos_casos=True),
    Agravo("NTRA", "Tracoma (notificação)", "nottraconet.def", todos_casos=True),
    Agravo("PAIR", "Perda auditiva induzida por ruído", "drtpairnet.def", todos_casos=True),
    Agravo("PEST", "Peste", "pestenet.def"),
    Agravo("PFAN", "Paralisia flácida aguda", "pfapolionet.def"),
    Agravo("PNEU", "Pneumoconioses", "drtpneumoconiosenet.def", todos_casos=True),
    Agravo("RAIV", "Raiva humana", "raivanet.def"),
    Agravo("ROTA", "Rotavírus", "rotanet.def"),
    Agravo("SDTA", "Surtos de doenças transmitidas por alimentos", "dtanet.def", todos_casos=True),
    Agravo("TETA", "Tétano acidental", "tetacidnet.def"),
    Agravo("TETN", "Tétano neonatal", "tetneonet.def"),
    Agravo("TOXC", "Toxoplasmose congênita", "notindivinet.def"),
    Agravo("TOXG", "Toxoplasmose gestacional", "notindivinet.def"),
    Agravo("TRAC", "Tracoma (inquérito)", "traconet.def", todos_casos=True),
    Agravo("TUBE", "Tuberculose", "tuberculnet5_0.def", todos_casos=True, campo_evolucao="SITUA_ENCE"),
    Agravo("VIOL", "Violência interpessoal/autoprovocada", "violencianet.def", todos_casos=True),
]}


def obter(codigo: str) -> Agravo:
    codigo = codigo.upper()
    return AGRAVOS.get(codigo) or Agravo(codigo, codigo, "notindivinet.def")


def nome(codigo: str) -> str:
    return obter(codigo).nome
