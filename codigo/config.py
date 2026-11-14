"""Configurações do projeto. Edite aqui, sem mexer na lógica."""
from pathlib import Path

CODIGO = Path(__file__).resolve().parent   # pasta codigo/
RAIZ = CODIGO.parent                          # pasta principal do projeto

# ------------------------------------------------------------------ arquivos --
PLANILHA = RAIZ / "dados" / "Base Movimento.xlsx"   # coloque a planilha aqui
TEMPLATE = CODIGO / "template.html"
CHARTJS = CODIGO / "chart.umd.min.js"      # biblioteca de gráficos (embutida no site)
SAIDA_HTML = RAIZ / "index.html"          # o site gerado
SAIDA_JSON = RAIZ / "auditoria" / "dados.json" # os mesmos dados do site, para auditoria
LOGO = None                                # ex.: CODIGO / "logo.png" (opcional)

# ------------------------------------------------------- textos do cabeçalho --
TITULO = "Trabalho de Previsão de Demandas"
SUBTITULO = "Previsão de demanda de fretes rodoviários e aéreos"
EMPRESA = ""                               # opcional: nome da empresa
FACULDADE = "Fatec Sebrae"                 # <- edite
CURSO = "Ciência de Dados para Negócios"  # <- edite
DATA_ENTREGA = "Novembro/2026"                   # <- edite

# Equipe e docentes (aba "Equipe")
EQUIPE = [
    "João Gabriel Matos Barbosa",
    "Eduardo Takeuchi",
    "Janilson Barros",
    "Icaro Fogaca",
    "Matheus Vilar",
    "Juan Jose",
]
DISCIPLINAS = [                                # (disciplina, docente)
    ("Projeto Integrador", "Nathane de Castro"),
    ("Empreendedorismo Inovação em Ambientes Disruptivos", "Caio Flavio Stettiner"),
]

# --------------------------------------------------------------- previsão ----
SEMANAS_TESTE = 16        # janela do backtest (previsão de uma semana à frente)
SEMANAS_PREVISAO = 26     # 6 meses: curto prazo, segundo o livro (menos de seis meses)
Z_95 = 1.96               # faixa de aproximadamente 95%
TOP_N = 8                 # itens nos rankings de origem, destino e rota

# Colunas esperadas na planilha
COLUNAS = [
    "Data Frete", "Data Entrega", "Modal do frete", "Cidade origem", "UF Origem",
    "Cidade destino", "UF Destino", "Volumes", "Peso Real", "Peso Taxado",
]

# Referência bibliográfica
REFERENCIA = (
    "BALLOU, Ronald H. Gerenciamento da cadeia de suprimentos/logística empresarial. "
    "Tradução de Raul Rubenich. 5. ed. Porto Alegre: Bookman, 2006."
)
