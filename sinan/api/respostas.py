"""Respostas JSON e erros com mensagem para mostrar na tela."""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from fastapi.responses import Response


class ErroUsuario(Exception):
    """Erro que o usuário consegue resolver: vira resposta 400 com a mensagem na tela."""


def _converter(v):
    """Tipos do pandas/numpy que o json não conhece."""
    try:
        if pd.isna(v):  # NaT, NaN, pd.NA (antes de isoformat: NaT também tem isoformat)
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime("%Y-%m-%d")
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "item"):
        return v.item()
    return str(v)


class RespostaJSON(Response):
    """JSON em UTF-8 (acentos legíveis) que aceita datas e números do pandas/numpy."""

    media_type = "application/json"

    def render(self, conteudo) -> bytes:
        return json.dumps(conteudo, ensure_ascii=False, default=_converter).encode("utf-8")


def json_resp(dados, status: int = 200) -> RespostaJSON:
    return RespostaJSON(dados, status_code=status)


def erro(mensagem: str, status: int = 400) -> RespostaJSON:
    """Formato de erro que a interface entende: {"erro": "..."}."""
    return json_resp({"erro": mensagem}, status)


def registros(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> lista de dicionários, com vazios como None."""
    df = df.astype(object).where(df.notna(), None)
    return df.to_dict(orient="records")


def anexo(conteudo: bytes, nome_arquivo: str, tipo: str) -> Response:
    return Response(conteudo, media_type=tipo,
                    headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'})
