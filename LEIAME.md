# Previsão de demanda de fretes rodoviários e aéreos

Trabalho de Projeto Integrador — Fatec Sebrae, curso Ciência de Dados para Negócios (Novembro/2026).
Base teórica: BALLOU, Ronald H. *Gerenciamento da cadeia de suprimentos/logística empresarial*, 5. ed., Bookman, 2006, Capítulo 8.

O trabalho **prevê a demanda** (número de fretes) dos próximos 6 meses. Não propõe ações operacionais.
O produto entregue é um **site** gerado em Python.

## Para quem só quer ver o trabalho

Abra o arquivo **`index.html`** (pasta principal) com duplo clique. Funciona em qualquer navegador, sem internet
e sem instalar nada. Todos os gráficos, dados e estilos estão dentro desse único arquivo.

## O que há em cada pasta

| Caminho | O que é |
|---|---|
| `index.html` | **O site pronto.** É a entrega principal. |
| `codigo/` | Todo o programa em Python que lê a planilha, calcula a previsão e monta o site. |
| `dados/` | Pasta onde fica a planilha da empresa (`Base Movimento.xlsx`). Não vai no pacote (ver abaixo). |
| `auditoria/dados.json` | Os mesmos números exibidos no site, em texto, para conferência. |
| `publicacao/` | Arquivos e instruções para colocar o site na internet. |

### Dentro de `codigo/`

| Arquivo | Função |
|---|---|
| `config.py` | Textos do cabeçalho (curso, entrega, equipe, docentes) e parâmetros da previsão. É o único que se edita. |
| `limpeza.py` | Lê a planilha e trata os dados (datas, tipos, registros inválidos). |
| `series.py` | Monta as séries diárias e semanais, o índice sazonal, o perfil por dia da semana e as distribuições. |
| `previsao.py` | Testa 10 métodos de previsão (ingênuo, médias móveis, ponderação exponencial simples e Holt), escolhe o de menor erro (MAPE) por modal, projeta 26 semanas e calcula a faixa de 95%. |
| `mapa.py` | Calcula as rotas mais usadas e desenha o mapa do Brasil. |
| `gerar_site.py` | **Programa principal.** Executa tudo na ordem, confere os totais com a planilha e grava o `index.html`. |
| `template.html` | Layout do site (páginas, estilos e interações). |
| `chart.umd.min.js` | Biblioteca de gráficos (Chart.js 4.6.1, licença MIT), embutida no site. |
| `dados_mapa/` | Fronteiras dos estados (Natural Earth, domínio público) e coordenadas dos municípios (IBGE). |
| `requirements.txt` | Bibliotecas Python necessárias: pandas, numpy, openpyxl. |

## Como o trabalho foi feito (resumo)

1. **Dados:** 238.614 fretes (230.170 rodoviários e 8.444 aéreos), de 01/09/2025 a 30/09/2026.
2. **Série:** fretes por semana (segunda a domingo, só semanas completas).
3. **Teste:** cada método prevê a semana seguinte, usando só dados anteriores, nas últimas 16 semanas. Mede-se o erro (MAD, MAPE, sinal de rastreamento).
4. **Escolha:** vence o método de menor MAPE por modal. Rodoviário: ponderação exponencial simples (α = 0,2), MAPE 7,0%. Aéreo: média móvel de 4 semanas, MAPE 12,1%. Total (soma dos modais): MAPE 7,1%.
5. **Sazonalidade:** índice mensal calculado sobre os últimos 12 meses (Ballou, Eq. 8-6 a 8-9), aplicado sobre a projeção.
6. **Projeção:** 6 meses (outubro/2026 a março/2027) com faixa de confiança de 95%.

## Como gerar o site de novo (opcional)

1. Instale o Python 3 e, na pasta `codigo/`, rode: `pip install -r requirements.txt`
2. Copie a planilha para `dados/` com o nome **`Base Movimento.xlsx`**.
3. Abra o terminal em `codigo/` e rode: `python gerar_site.py`
   (leva cerca de 20 segundos; para outra planilha: `python gerar_site.py caminho/da/planilha.xlsx`).
4. O programa confere os totais com a planilha e atualiza `index.html` e `auditoria/dados.json`.

**Sobre a planilha:** `Base Movimento.xlsx` contém dados da empresa e **não está neste pacote**. O `index.html` já abre sem ela.
Ela só é necessária para recalcular. Para outra base, mantenha as colunas listadas em `config.py` (`COLUNAS`).

## Colocar na internet

Veja `publicacao/PUBLICAR_ONLINE.md`.

## Limitações declaradas

- Só há um ciclo anual de histórico (13 meses); o ideal seriam 24 a 36 meses.
- O erro é medido uma semana à frente; o erro da projeção de 6 meses não foi testado.
- O método foi escolhido nas mesmas semanas usadas para testá-lo (leve otimismo).
- O modal aéreo tem erro maior que o rodoviário.
- A planilha traz apenas fretes transportados.
