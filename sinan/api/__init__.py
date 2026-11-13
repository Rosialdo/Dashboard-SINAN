"""Servidor local do dashboard: entrega a interface (pasta web/) e uma API JSON.

Tudo roda no próprio computador (localhost); só a atualização de dados usa a internet.

Organização:
    app.py        monta o FastAPI (rotas, erros, arquivos da interface, segurança)
    rotas/        um arquivo por assunto (como os "routers" do Express)
    filtros.py    lê os filtros da URL e monta o consultas.Filtro
    servicos.py   cálculos usados por mais de uma rota
    tarefa.py     download/processamento em segundo plano
    cache.py      cache dos resultados agregados
    seguranca.py  proteção contra outros sites abertos no navegador
    respostas.py  JSON, conversão de tipos e erros com mensagem para a tela
"""

from .app import app, criar_app

__all__ = ["app", "criar_app"]
