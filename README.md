# AchadosMM by MandaManipular.com

Site estático com as ofertas do dia para farmácias de manipulação. A curadoria é diária e cobre Mercado Livre, Shopee e Amazon.

## Arquivos

| Arquivo | O que é |
|---|---|
| `index.html` | Layout do site, com HTML, CSS e JS num arquivo só. No dia a dia, não precisa mexer. |
| `ofertas.js` | Base de ofertas (`window.ACHADOS`, com JSON puro). É o único arquivo de dados que a curadoria altera, sempre pelo script. |
| `scripts/curadoria.py` | Junta as ofertas do dia no `ofertas.js` e aplica as regras de preço e validade. |
| `og.png` | Imagem de prévia quando o link é compartilhado no WhatsApp ou em redes sociais. |
| `img/logo.png` | Logo do AchadosMM usada no cabeçalho e no rodapé. |
| `favicon.ico`, `favicon-32.png`, `apple-touch-icon.png`, `img/icon-192.png`, `img/icon-512.png`, `site.webmanifest` | Ícone do site (aba do navegador, atalho no celular), feito a partir da logo. |
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
- **Base AchadosMM:** desde 01/11/2026 o site traz a base completa (itens do dia a dia da farmácia com link de afiliado MSI). A tarefa "AchadosMM — preços da base" confere o preço dos itens de recompra todo dia, para o preço não expirar.
- **Categorias:** uma aba e uma seção para cada item de `categorias`. Os links ficam como `/#laboratorio`, `/#epi` etc. e servem para mandar uma categoria direto no grupo.

## Campos da oferta

`id`, `titulo`, `marca`, `categoria`, `loja`, `link` (de afiliado), `preco`, `precoDe`, `vendidos`, `vendidosNum`, `porQueVale`, `seloTecnico`, `full`, `freteGratis`, `imagem` (URL da foto ou arquivo em `img/`), `ciclo` (ciclo de recompra sugerido: Quinzenal, Mensal, Bimestral, Trimestral, Semestral ou Anual / sazonal; vazio = compra pontual), `mlb` (id do anúncio no Mercado Livre, só números), `adicionadoEm`, `vistoEm`, `ativo`.

Itens com `ciclo` de quinzenal a semestral ganham o selo "Recompra mensal" (ou o ciclo correspondente) no card. Todo `link` é de afiliado da conta MSI (`https://meli.la/...`).

Regra: `preco` e `precoDe` só com valor conferido na página no dia (`vistoEm`). Sem preço conferido, o campo fica `null` e o card mostra "Confira o preço do dia na loja".

## Configurações em `ofertas.js`

- `grupoUrl`: link de convite da Comunidade de WhatsApp.
- `whatsappPedidos`: número para pedidos de itens (ex.: `5517999999999`).

## Quando tiver domínio

Trocar `og:image` no `index.html` para a URL absoluta, por exemplo `https://achados.mandamanipular.com/og.png`. O WhatsApp só mostra a prévia com URL absoluta.

## Conta da farmácia (Supabase)

Projeto Supabase **AchadosMM** (`gltxisnlyclsabtuhtjv`). O site usa só a chave publishable. A segurança fica nas regras (RLS) do banco.

- **Criar conta:** edge function `cadastro`. Ela recebe nome, celular, senha, farmácia, cidade, UF e o aceite do WhatsApp. O celular vira o login interno `55DDDNUMERO@contas.achadosmm.mandamanipular.com`, já confirmado, sem SMS.
- **Entrar:** `signInWithPassword` com esse login interno e a senha.
- **Tabelas:**
  - `perfis`: 1 por farmácia; o telefone não pode ser trocado pela própria conta.
  - `tipos_produto`: catálogo de tipos.
  - `interesses`: o que a farmácia compra, com `lembrar_dias` e `ultima_compra`.
  - `cliques`: cliques em "Ver oferta" de quem está logado.
- **Relatórios** (schema `relatorios`, que não sai pela API):
  - `farmacias_interesses`;
  - `lembretes_vencendo`: só quem aceitou o WhatsApp, vencendo em até 2 dias;
  - `ranking_interesses`.
- **Senha esquecida:** redefinir pelo painel do Supabase (Authentication → Users).
- **Ligação com as ofertas:** `ofertas.js` tem o campo `tipo` (id de `tipos_produto`). Se a curadoria não informar, o `scripts/curadoria.py` deduz o tipo pelo título.

## Copiar link e compartilhar
Todo card de oferta (e o carrossel do topo) tem dois botões:
- **Copiar link:** copia o link de afiliado (meli.la) da oferta.
- **Compartilhar:** no celular abre o menu de compartilhar do aparelho; no computador abre o WhatsApp com a mensagem pronta.

A mensagem segue o mesmo formato da postagem do grupo (tarefas "Curadoria AchadosMM" e "AchadosMM — envio ao grupo"), e termina com "🛒 Veja todas as ofertas do dia para a sua farmácia: https://achadosmm.vercel.app" e "#AchadosMM | by MandaManipular.com" (sem a frase "Link de parceiro", decisão de 09/11). Se mudar o formato do post, mude nos três lugares: `textoOferta()` no `index.html` e as duas tarefas.
