# Como colocar o site na internet

O site é **estático**: basta hospedar o `index.html` (e, se quiser, o `404.html`). Não precisa de servidor, banco de dados nem login.

## GitHub Pages (gratuito)

1. Crie uma conta em github.com e um repositório novo (ex.: `previsao-demanda`).
2. Envie para a **raiz** do repositório todo o conteúdo desta pasta do projeto (o `index.html` e o `404.html` já estão na raiz).
3. **Não envie** a planilha `Base Movimento.xlsx` (dados da empresa).
4. Em **Settings → Pages**, escolha *Deploy from a branch*, branch `main`, pasta `/ (root)`, e salve.
5. Em alguns minutos o endereço aparece nessa tela: `https://SEU-USUARIO.github.io/previsao-demanda/` (já com HTTPS).

## Netlify (mais rápido)

Em netlify.com, **Add new site → Deploy manually** e arraste uma pasta com `index.html` e `404.html`. O endereço sai na hora.

## Observações

- O site pede aos buscadores que não o listem (`noindex`): só acessa quem tem o link.
- Confirme com a empresa se a divulgação dos dados é autorizada antes de publicar.
- Para atualizar: gere o novo `index.html` (ver `README.md`) e envie-o de novo ao repositório.
