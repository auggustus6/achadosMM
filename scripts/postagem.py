#!/usr/bin/env python3
"""AchadosMM: monta a postagem do grupo de WhatsApp (formato para o COMPRADOR da farmácia).

Uso:
  python3 scripts/postagem.py item.json --hoje AAAA-MM-DD     (item.json = um objeto ou uma lista)
  echo '{...}' | python3 scripts/postagem.py - --hoje AAAA-MM-DD

Campos lidos (os mesmos do ofertas.js): titulo, categoria, tipo, preco, precoDe, vistoEm,
link, ciclo, seloTecnico, full, freteGratis.
O mesmo formato está em textoOferta() no index.html (botão Compartilhar). Mudou aqui, mude lá.

Regras:
  - preço conferido hoje: "💰 *R$ Y*  (era R$ X, Z% off)" e preço por unidade/rolo/litro;
  - preço conferido de 1 a 7 dias atrás: mostra o preço com a data e pede para conferir no link;
  - sem preço ou preço com mais de 7 dias: "💰 Confira o preço do dia no link" (nunca inventa preço);
  - a quantidade do pacote sai do fim do título (", 100 unidades", ", 10 rolos", "galão 5 L")
    e vira a linha 📦 com o custo por unidade, que é a conta que o comprador faz.
"""
import argparse, datetime as dt, json, re, sys
from decimal import Decimal, ROUND_HALF_UP

SITE = 'https://achados.mandamanipular.com.br'
EMO_CAT = {'laboratorio': '🧪', 'epi': '🧤', 'etiquetagem': '🏷️', 'estoque': '📦', 'escritorio': '🗂️',
           'ti': '💻', 'atendimento': '🛍️', 'expedicao': '📦', 'copa': '☕'}
# emoji pelo produto (primeiro que casar no título); senão, o da categoria
EMO_PROD = [(r'bobina|cupom', '🧾'), (r'saco de lixo|lixeira', '🗑️'), (r'toner|cartucho|impressora', '🖨️'),
            (r'sulfite|papel a4|resma', '📄'), (r'etiqueta|ribbon|rotulador|etiquetadora|fita compat', '🏷️'),
            (r'luva|m[aá]scara|touca|prop[eé]|avental|mangote|jaleco', '🧤'),
            (r'[aá]lcool|sabonete|detergente|cloro|desinfet|limpa|esponja|palha de a[cç]o|pano|odorizante', '🧴'),
            (r'papel (toalha|higi)', '🧻'), (r'pilha|bateria', '🔋'), (r'caf[eé]|copo|filtro de papel|a[cç][uú]car', '☕'),
            (r'caixa|envelope|pl[aá]stico bolha|sacola|fita adesiva|lacre', '📦')]
CICLO = {'Quinzenal': 'quinzenal', 'Mensal': 'mensal', 'Bimestral': 'bimestral',
         'Trimestral': 'trimestral', 'Semestral': 'semestral'}
UN = {'unidades': ('cada', 'unidades'), 'unidade': ('cada', 'unidade'), 'un': ('cada', 'unidades'),
      'rolos': ('por rolo', 'rolos'), 'folhas': ('por folha', 'folhas'), 'pacotes': ('por pacote', 'pacotes'),
      'blocos': ('por bloco', 'blocos'), 'pares': ('por par', 'pares'), 'caixas': ('por caixa', 'caixas'),
      'resmas': ('por resma', 'resmas'), 'refis': ('por refil', 'refis'), 'galões': ('por galão', 'galões'),
      'tiras': ('por tira', 'tiras'), 'panos': ('por pano', 'panos'), 'sacos': ('por saco', 'sacos')}
QTD_RE = re.compile(r',\s*(?:(?:caixa|pacote|fardo|kit) com\s+)?(\d{1,3}(?:\.\d{3})*|\d+)\s+(unidades|unidade|un|rolos|folhas|pacotes|blocos|pares|caixas|resmas|refis|galões|tiras|panos|sacos)\b([^,]*)(,\s*[a-zà-ú ]+)?$', re.I)
LIQUIDO_RE = re.compile(r'[aá]lcool|sabonete|detergente|desinfet|cloro|sanit[aá]ria|alvejante|limpa|[aá]gua|l[ií]quido|gel|amaciante|lustra|multiuso', re.I)
LITRO_RE = re.compile(r'\s(\d+(?:[.,]\d+)?)\s*(L|litros)\s*$', re.I)


def brl(v, casas=2):
    v = Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    s = f'{v:,.{casas}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {s}'


def num(v):
    if v in (None, ''):
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    s = str(v).strip().replace('R$', '').strip()
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        f = float(s)
        return f if f > 0 else None
    except ValueError:
        return None


def separa_qtd(titulo):
    """'Luva nitrílica G, 100 unidades' -> ('Luva nitrílica G', 100, 'unidades', 'cada')."""
    m = QTD_RE.search(titulo)
    if m:
        q = int(m.group(1).replace('.', ''))
        cada, nome = UN[m.group(2).lower()]
        resto = m.group(3).strip()
        cor = m.group(4) or ''
        return (titulo[:m.start()] + cor).strip(), q, nome + (' ' + resto if resto else ''), cada
    m = LITRO_RE.search(titulo)
    if m and LIQUIDO_RE.search(titulo):
        q = float(m.group(1).replace(',', '.'))
        return titulo, q, None, 'o litro'
    return titulo, None, None, None


def por_unidade(preco, q, cada, titulo=''):
    if not preco or not q or q <= 1:
        return None
    u = preco / q
    if cada == 'por folha' and q >= 500 and re.search(r'sulfite|a4|resma|of[ií]cio', titulo, re.I):
        return f'{brl(u * 500)} a resma de 500'
    if cada == 'cada' and q >= 1000 and u < 0.10 and re.search(r'etiqueta', titulo, re.I):
        return f'{brl(preco / q * 1000)} o milheiro'
    return f'{brl(u, 3 if u < 0.01 else 2)} {cada}'


def emoji(o):
    t = (o.get('titulo') or '').lower()
    for rx, e in EMO_PROD:
        if re.search(rx, t):
            return e
    return EMO_CAT.get(o.get('categoria'), '🛒')


def montar(o, hoje):
    hoje = dt.date.fromisoformat(hoje)
    titulo = re.sub(r'\s+', ' ', (o.get('titulo') or '').strip())
    nome, q, qtd_txt, cada = separa_qtd(titulo)
    preco, de = num(o.get('preco')), num(o.get('precoDe'))
    visto = str(o.get('vistoEm') or '').lstrip("'")[:10]
    try:
        dias = (hoje - dt.date.fromisoformat(visto)).days if visto else None
    except ValueError:
        dias = None
    if not preco or dias is None or dias < 0 or dias > 7:
        preco, de, estado = None, None, 'sem'
    else:
        estado = 'hoje' if dias == 0 else 'antes'

    linhas = [f'{emoji(o)} *{nome}*', '']
    if estado == 'hoje':
        if de and de > preco:
            pct = round((1 - preco / de) * 100)
            linhas.append(f'💰 *{brl(preco)}*  (era ~{brl(de)}~, {pct}% off)')
        else:
            linhas.append(f'💰 *{brl(preco)}*')
    elif estado == 'antes':
        d = dt.date.fromisoformat(visto)
        linhas.append(f'💰 *{brl(preco)}* em {d:%d/%m} (confira o preço de hoje no link)')
    else:
        linhas.append('💰 Confira o preço do dia no link')
    if q:
        pu = por_unidade(preco, q, cada, titulo) if estado != 'sem' else None
        if qtd_txt:
            qn = f'{q:,}'.replace(',', '.')
            linhas.append(f'📦 {qn} {qtd_txt}' + (f': sai a *{pu}*' if pu else ''))
        elif pu:
            linhas.append(f'📦 Sai a *{pu}*')
    if o.get('ciclo') in CICLO:
        linhas.append(f'🔁 Reposição {CICLO[o["ciclo"]]}')
    if o.get('seloTecnico'):
        linhas.append('🔬 Uso técnico: confira as especificações no anúncio')
    if o.get('full'):
        linhas.append('🚚 Full: entrega rápida')
    elif o.get('freteGratis'):
        linhas.append('🚚 Frete grátis')
    linhas += ['', f'👉 {o.get("link", "").strip()}', '', f'🛒 Mais ofertas para a farmácia: {SITE}']
    return '\n'.join(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arquivo')
    ap.add_argument('--hoje', required=True)
    a = ap.parse_args()
    dados = json.load(sys.stdin if a.arquivo == '-' else open(a.arquivo, encoding='utf-8'))
    itens = dados if isinstance(dados, list) else [dados]
    print('\n\n=====\n\n'.join(montar(o, a.hoje) for o in itens))


if __name__ == '__main__':
    main()
