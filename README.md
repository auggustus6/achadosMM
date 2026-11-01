# AchadosMM by MandaManipular.com

Site estático com as ofertas do dia para farmácias de manipulação. A curadoria é diária e cobre Mercado Livre, Shopee e Amazon.

## Arquivos

| Arquivo | O que é |
|---|---|
| `index.html` | Layout do site, com HTML, CSS e JS num arquivo só. No dia a dia, não precisa mexer. |
| `ofertas.js` | Base de ofertas (`window.ACHADOS`, com JSON puro). É o único arquivo de dados que a curadoria altera, sempre pelo script. |
| `scripts/curadoria.py` | Junta as ofertas do dia no `ofertas.js` e aplica as regras de preço e validade. |
| `og.png` | Imagem de prévia quando o link é compartilhado no WhatsApp ou em redes sociais. |
| `favicon.svg` | Ícone do site. |
| `vercel.json` | Configuração da Vercel. O `ofertas.js` sai sem cache para a atualização aparecer na hora. |

Não tem build. A Vercel publica a pasta como está, com Framework Preset "Other" e sem comando de build.

## Atualização diária (tarefa "Curadoria AchadosMM")

1. A curadoria coleta as ofertas no painel de Afiliados do Mercado Livre (conta MSI) e grava as postagens na planilha "Fila AchadosMM — ofertas farmácias", no Google Drive. Essa planilha é separada da Fila Baratinha.
2. Ela monta o `novos.json` com as ofertas conferidas no dia e roda `python3 scripts/curadoria.py ofertas.js novos.json --hoje AAAA-MM-DD`. O script junta as ofertas novas com as que já existem e apaga os preços com mais de 7 dias. Quando não houver nada novo, ele imprime `SEM MUDANCA`.
3. Faz commit e push na `main`. A Vercel publica sozinha.

`python3 scripts/curadoria.py ofertas.js --resumo` mostra quantos itens têm preço conferido e link de afiliado.

O site monta as seções sozinho a partir dos dados:

- **Top ofertas:** itens com `preco` e `precoDe`, ordenados pelo maior desconto.
- **Mais vendidos:** maiores valores em `vendidosNum`.
- **Destaques do dia:** itens com `adicionadoEm` igual a `atualizadoEm`. Também alimentam o contador "N ofertas novas".
- **Categorias:** uma aba e uma seção para cada item de `categorias`. Os links ficam como `/#laboratorio`, `/#epi` etc. e servem para mandar uma categoria direto no grupo.

## Campos da oferta

`id`, `titulo`, `marca`, `categoria`, `loja`, `link` (de afiliado), `preco`, `precoDe`, `vendidos`, `vendidosNum`, `porQueVale`, `seloTecnico`, `full`, `freteGratis`, `imagem` (URL da foto ou arquivo em `img/`), `adicionadoEm`, `vistoEm`, `ativo`.

Regra: `preco` e `precoDe` só com valor conferido na página no dia (`vistoEm`). Sem preço conferido, o campo fica `null` e o card mostra "Confira o preço do dia na loja".

## Configurações em `ofertas.js`

- `grupoUrl`: link de convite da Comunidade de WhatsApp.
- `whatsappPedidos`: número para pedidos de itens (ex.: `5517999999999`).

## Quando tiver domínio

Trocar `og:image` no `index.html` para a URL absoluta, por exemplo `https://achados.mandamanipular.com/og.png`. O WhatsApp só mostra a prévia com URL absoluta.
