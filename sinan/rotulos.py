"""Nomes amigáveis e grupos para as variáveis da ficha (tela "Outras variáveis").

Os rótulos dos arquivos .def do TabNet são abreviados ("Sin.clín:Dor retro",
"Pré-ex:Hipert.art.", "Conf.Desc pos2010") e os nomes dos campos têm "_"
(CS_ESCOL_N). Aqui eles viram nomes em português claro, organizados por assunto.

São três camadas, nesta ordem:
1. nome escrito à mão pelo arquivo .cnv (variantes do mesmo campo, ex.: faixas etárias);
2. nome escrito à mão pelo campo (os mais usados em todas as fichas);
3. limpeza automática do rótulo do TabNet (expande abreviações conhecidas).
"""

from __future__ import annotations

import re

# ordem em que os grupos aparecem na tela
GRUPOS = [
    "Perfil do paciente",
    "Sinais e sintomas",
    "Doenças pré-existentes",
    "Exames de laboratório",
    "Classificação e evolução",
    "Outras informações",
]

POR_CNV = {
    "fxidad10net.cnv": "Faixa etária (padrão SINAN)",
    "fxidad13net.cnv": "Faixa etária (de 10 em 10 anos)",
    "fxidad9net.cnv": "Faixa etária (9 grupos)",
    "fxidad5net.cnv": "Faixa etária (crianças e jovens)",
    "fxripsa6net.cnv": "Faixa etária (padrão RIPSA)",
    "idadedetnet.cnv": "Idade detalhada",
    "fx14a69.cnv": "Faixa etária (14 a 69 anos)",
    "grupo1a.cnv": "Ocupação informada?",
    "semocupa.cnv": "Ocupação fora da lista oficial (CBO)",
}

POR_CAMPO = {
    # perfil
    "CS_SEXO": "Sexo", "CS_RACA": "Raça/cor", "CS_ESCOL_N": "Escolaridade", "CS_GESTANT": "Gestante",
    "CS_ZONA": "Zona de residência", "ID_OCUPA_N": "Ocupação",
    # sinais e sintomas (arboviroses)
    "FEBRE": "Febre", "MIALGIA": "Dor muscular (mialgia)", "CEFALEIA": "Dor de cabeça (cefaleia)",
    "EXANTEMA": "Manchas na pele (exantema)", "VOMITO": "Vômito", "NAUSEA": "Náusea",
    "DOR_COSTAS": "Dor nas costas", "CONJUNTVIT": "Conjuntivite", "ARTRITE": "Artrite",
    "ARTRALGIA": "Dor nas articulações (artralgia)", "PETEQUIA_N": "Petéquias", "PETEQUIAS": "Petéquias",
    "LEUCOPENIA": "Leucopenia", "LACO": "Prova do laço positiva", "LACO_N": "Prova do laço positiva",
    "DOR_RETRO": "Dor atrás dos olhos", "MANI_HEMOR": "Manifestações hemorrágicas", "EPISTAXE": "Sangramento nasal",
    "GENGIVO": "Sangramento na gengiva", "METRO": "Sangramento uterino (metrorragia)",
    "HEMATURA": "Sangue na urina (hematúria)", "SANGRAM": "Sangramento gastrointestinal",
    "PLASMATICO": "Extravasamento de plasma", "EVIDENCIA": "Extravasamento evidenciado por",
    # doenças pré-existentes
    "DIABETES": "Diabetes", "HEMATOLOG": "Doença hematológica", "HEPATOPAT": "Doença do fígado",
    "RENAL": "Doença renal crônica", "HIPERTENSA": "Hipertensão arterial", "ACIDO_PEPT": "Doença ácido-péptica",
    "AUTO_IMUNE": "Doença autoimune",
    # exames
    "RESUL_SORO": "Sorologia IgM", "RESUL_NS1": "Teste NS1", "RESUL_VI_N": "Isolamento viral",
    "RESUL_PCR_": "RT-PCR", "SOROTIPO": "Sorotipo do vírus", "HISTOPA_N": "Histopatologia",
    "IMUNOH_N": "Imuno-histoquímica", "RES_CHIKS1": "IgM chikungunya (1ª amostra)",
    "RES_CHIKS2": "IgM chikungunya (2ª amostra)", "RESUL_PRNT": "PRNT (teste de neutralização)",
    # classificação e evolução
    "CLASSI_FIN": "Classificação final", "CRITERIO": "Critério de confirmação", "EVOLUCAO": "Evolução do caso",
    "CLINC_CHIK": "Forma clínica", "CON_FHD": "Grau da febre hemorrágica (FHD)", "COMPLICA": "Complicações",
    "HOSPITALIZ": "Hospitalização", "TPAUTOCTO": "Infectado no município onde mora",
    "DOENCA_TRA": "Relacionada ao trabalho", "TP_SISTEMA": "Sistema de registro",
}

_GRUPO_CAMPO = {
    "Perfil do paciente": {"NU_IDADE_N", "CS_SEXO", "CS_RACA", "CS_ESCOL_N", "CS_GESTANT", "CS_ZONA", "ID_OCUPA_N"},
    "Sinais e sintomas": {"FEBRE", "MIALGIA", "CEFALEIA", "EXANTEMA", "VOMITO", "NAUSEA", "DOR_COSTAS", "CONJUNTVIT",
                          "ARTRITE", "ARTRALGIA", "PETEQUIA_N", "PETEQUIAS", "LEUCOPENIA", "LACO", "LACO_N", "DOR_RETRO",
                          "MANI_HEMOR", "EPISTAXE", "GENGIVO", "METRO", "HEMATURA", "SANGRAM", "PLASMATICO", "EVIDENCIA"},
    "Doenças pré-existentes": {"DIABETES", "HEMATOLOG", "HEPATOPAT", "RENAL", "HIPERTENSA", "ACIDO_PEPT", "AUTO_IMUNE"},
    "Exames de laboratório": {"RESUL_SORO", "RESUL_NS1", "RESUL_VI_N", "RESUL_PCR_", "SOROTIPO", "HISTOPA_N", "IMUNOH_N",
                              "RES_CHIKS1", "RES_CHIKS2", "RESUL_PRNT"},
    "Classificação e evolução": {"CLASSI_FIN", "CRITERIO", "EVOLUCAO", "CLINC_CHIK", "CON_FHD", "COMPLICA", "HOSPITALIZ",
                                 "TPAUTOCTO", "DOENCA_TRA"},
}

# pistas no rótulo do TabNet para as fichas sem grupo escrito à mão
_GRUPO_ROTULO = [
    ("Perfil do paciente", r"^(fx|faixa|idade|sexo|ra[çc]a|escolar|gestante|ocupa)"),
    ("Doenças pré-existentes", r"^(pr[ée]-?ex|doen[çc]as? pr[ée]|comorb)"),
    ("Sinais e sintomas", r"^(sin\.|sinais|sintoma|cl[ií]n?\.?:|manif)"),
    ("Exames de laboratório", r"\b(exame|ex\.|igm|igg|pcr|sorolog|isolamento|result|res\.|cultura|bacilosc|"
                              r"l[ií]quor|histopat|imuno|elisa|microsc|raio|rx|teste)"),
    ("Classificação e evolução", r"\b(classif|evolu|conf\.?\s*desc|crit[ée]rio|hospital|aut[óo]ct|[óo]bito|encerr|alta\b)"),
]

# abreviações comuns nos rótulos do TabNet (aplicadas em ordem, sem diferenciar maiúsculas)
_EXPANSOES = [
    (r"^sin\.?\s*cl[ií]n\.?\s*:\s*", ""),
    (r"^pr[ée]-?ex\.?\s*:\s*", ""),
    (r"^fx\.?\s*et[áa]ria\b", "Faixa etária"),
    (r"\bconf\.?\s*desc\b", "Critério de confirmação"),
    (r"\bate\s*(\d{4})\b", r"(até \1)"),
    (r"\bp[óo]s\s*(\d{4})\b", r"(após \1)"),
    (r"\bres\.\s*", "Resultado "),
    (r"\bex\.\s*", "exame "),
    (r"\bdt\.?\s+", "Data "),
    (r"\bnot\.\s*", "notificação "),
    (r"\bhipert\.?\s*art\.?", "Hipertensão arterial"),
    (r"\bprov\.?\s*la[çc]o\b", "Prova do laço"),
    (r"\bmun\.?\s*res\b", "município de residência"),
    (r"\bmun\b", "município"),
    (r"\bresid\.?\b", "residência"),
    (r"\bassoc\.?\b", "associado"),
    (r"\btrab\.?\b", "trabalho"),
    (r"\brelat\.?\b", "relacionada ao"),
    (r"\bcompl\.?\b", "complicação"),
    (r"\bsinannet\b", ""),
    (r"_", " "),
]


def _limpar(rotulo: str) -> str:
    texto = rotulo.strip()
    for padrao, troca in _EXPANSOES:
        texto = re.sub(padrao, troca, texto, flags=re.I)
    texto = re.sub(r"\s+", " ", texto).strip(" .:-")
    return texto[:1].upper() + texto[1:] if texto else rotulo


def _periodo(rotulo: str) -> str:
    """Sufixo " (até 2010)" / " (após 2010)" quando o .def tem versões por período."""
    m = re.search(r"\b(ate|p[óo]s)\s*(\d{4})\b", rotulo, flags=re.I)
    if not m:
        return ""
    return f" (até {m.group(2)})" if m.group(1).lower() == "ate" else f" (após {m.group(2)})"


# aparece primeiro dentro do grupo (e é a variável aberta ao entrar na tela)
PREFERIDOS = {"fxidad10net.cnv"}


def nome_amigavel(rotulo: str, campo: str, cnv: str) -> str:
    cnv = cnv.lower()
    if cnv in POR_CNV:
        return POR_CNV[cnv]
    if campo in POR_CAMPO:
        return POR_CAMPO[campo] + _periodo(rotulo)
    return _limpar(rotulo)


def grupo(rotulo: str, campo: str) -> str:
    for nome, campos in _GRUPO_CAMPO.items():
        if campo in campos:
            return nome
    texto = rotulo.strip().lower()
    for nome, padrao in _GRUPO_ROTULO:
        if re.search(padrao, texto):
            return nome
    return "Outras informações"


# ------------------------------------------------------------ valores das respostas
NAO_INFORMADO = "Não informado"

# grafias do DATASUS para "o campo ficou vazio ou foi marcado como ignorado"
# ("Ign/Branco", "Em branco", "IGNORADA", "Nao Informada"...). "Branca" (raça/cor)
# não entra: só "branco" no masculino, que nos .cnv sempre é campo vazio.
_VAZIO = re.compile(
    r"^(ign\.?|ignorad[oa]|ign\.?\s*/\s*(em\s+)?branc[o]?|ignorad[oa]\s*/\s*(em\s+)?branco|(em\s+)?branco"
    r"|n[ãa]o\s+informad[oa]|sem\s+informa[çc][ãa]o)$",
    flags=re.I,
)

_VALORES = {
    "Em aberto/Ign.": "Em aberto (sem classificação)",
}


def valor_simples(valor) -> str:
    """Troca os códigos de "sem resposta" do DATASUS por um texto que qualquer pessoa entende."""
    if valor is None or (isinstance(valor, float) and valor != valor):  # None ou NaN
        return NAO_INFORMADO
    texto = str(valor).strip()
    if not texto or _VAZIO.match(texto):
        return NAO_INFORMADO
    return _VALORES.get(texto, texto)
