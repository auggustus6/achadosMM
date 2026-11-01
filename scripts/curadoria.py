#!/usr/bin/env python3
"""Curadoria AchadosMM: aplica as ofertas do dia no ofertas.js do site.

Uso:
  python3 scripts/curadoria.py ofertas.js novos.json --hoje AAAA-MM-DD
  python3 scripts/curadoria.py ofertas.js --resumo        (só mostra o estado)

novos.json = lista de ofertas conferidas hoje. Campos aceitos:
  id (opcional: atualiza o item com esse id), titulo, marca, categoria, loja, link,
  preco, precoDe, vendidos, vendidosNum, porQueVale, seloTecnico, full, freteGratis,
  imagem, destaque (true = entra em "Destaques do dia" e conta como oferta nova).

Regras aplicadas:
  - casa pelo id; sem id, pelo título normalizado; senão cria item novo;
  - preco/precoDe só valem com vistoEm = hoje; preço visto há mais de 7 dias é apagado
    (o card volta a "Confira o preço do dia na loja");
  - link precisa começar com https://; preco precisa ser número > 0;
  - categoria precisa existir em "categorias".
Imprime "SEM MUDANCA" quando nada mudou.
"""
import argparse, datetime as dt, json, re, sys, unicodedata

PREFIX = 'window.ACHADOS = '
HEAD = ('/* AchadosMM: base de ofertas. Gerado pela Curadoria AchadosMM (scripts/curadoria.py). '
        'Não editar à mão: o objeto abaixo é JSON puro. */\n')
CAMPOS = ['titulo', 'marca', 'categoria', 'loja', 'link', 'preco', 'precoDe', 'vendidos',
          'vendidosNum', 'porQueVale', 'seloTecnico', 'full', 'freteGratis', 'imagem', 'ativo']


def load(path):
    s = open(path, encoding='utf-8').read()
    i = s.index('\n' + PREFIX) + 1 + len(PREFIX)
    return json.loads(s[i:].strip().rstrip(';'))


def save(path, d):
    open(path, 'w', encoding='utf-8').write(HEAD + PREFIX + json.dumps(d, ensure_ascii=False, indent=2) + ';\n')


def key(t):
    t = unicodedata.normalize('NFD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', t).strip()[:40]


def slug(t):
    return re.sub(r'\s+', '-', key(t))[:48].strip('-') or 'item'


def resumo(d, hoje):
    of = [o for o in d['ofertas'] if o.get('ativo', True)]
    com_preco = [o for o in of if o.get('preco')]
    afil = [o for o in of if str(o.get('link', '')).startswith('https://meli.la/')]
    novos = [o for o in of if o.get('adicionadoEm') == hoje and o.get('preco')]
    por_cat = {}
    for o in of:
        por_cat[o['categoria']] = por_cat.get(o['categoria'], 0) + 1
    print(f"itens ativos: {len(of)} | com preço conferido: {len(com_preco)} | com link de afiliado: {len(afil)} "
          f"| sem link de afiliado: {len(of) - len(afil)} | destaques de {hoje}: {len(novos)}")
    print('por categoria: ' + ', '.join(f'{k} {v}' for k, v in sorted(por_cat.items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ofertas')
    ap.add_argument('novos', nargs='?')
    ap.add_argument('--hoje', default=dt.date.today().isoformat())
    ap.add_argument('--resumo', action='store_true')
    a = ap.parse_args()
    d = load(a.ofertas)
    if a.resumo or not a.novos:
        resumo(d, a.hoje)
        return
    antes = json.dumps(d, sort_keys=True)
    cats = {c['id'] for c in d['categorias']}
    by_id = {o['id']: o for o in d['ofertas']}
    by_key = {key(o['titulo']): o for o in d['ofertas']}
    novos = json.load(open(a.novos, encoding='utf-8'))
    erros, criados, atualizados = [], 0, 0
    for n in novos:
        t = n.get('titulo', '').strip()
        if n.get('categoria') and n['categoria'] not in cats:
            erros.append(f"categoria inexistente: {n['categoria']} ({t})"); continue
        if n.get('link') and not str(n['link']).startswith('https://'):
            erros.append(f'link inválido: {t}'); continue
        if n.get('preco') is not None and not (isinstance(n['preco'], (int, float)) and n['preco'] > 0):
            erros.append(f'preço inválido: {t}'); continue
        o = by_id.get(n.get('id')) or by_key.get(key(t))
        if o is None:
            if not (t and n.get('categoria') and n.get('link')):
                erros.append(f'item novo sem titulo/categoria/link: {t or n}'); continue
            base = slug(t); nid = base; i = 2
            while nid in by_id:
                nid = f'{base}-{i}'; i += 1
            o = {'id': nid, 'titulo': t, 'marca': '', 'categoria': n['categoria'], 'loja': 'Mercado Livre',
                 'link': n['link'], 'preco': None, 'precoDe': None, 'vendidos': '', 'vendidosNum': 0,
                 'porQueVale': '', 'seloTecnico': False, 'full': False, 'freteGratis': False, 'imagem': '',
                 'adicionadoEm': a.hoje, 'vistoEm': '', 'ativo': True}
            d['ofertas'].append(o); by_id[nid] = o; by_key[key(t)] = o; criados += 1
        else:
            atualizados += 1
        for c in CAMPOS:
            if c in n and n[c] is not None and n[c] != '':
                o[c] = n[c]
        if 'precoDe' in n and n['precoDe'] is None:
            o['precoDe'] = None
        if n.get('preco'):
            o['vistoEm'] = a.hoje
            if o.get('precoDe') and o['precoDe'] <= o['preco']:
                o['precoDe'] = None
        if n.get('destaque'):
            o['adicionadoEm'] = a.hoje
    # preço com mais de 7 dias deixa de ser mostrado
    limite = (dt.date.fromisoformat(a.hoje) - dt.timedelta(days=7)).isoformat()
    expirados = 0
    for o in d['ofertas']:
        if o.get('preco') and (not o.get('vistoEm') or o['vistoEm'] < limite):
            o['preco'] = None; o['precoDe'] = None; o['full'] = False; o['freteGratis'] = False; expirados += 1
    d['atualizadoEm'] = a.hoje
    if json.dumps(d, sort_keys=True) == antes:
        print('SEM MUDANCA')
    else:
        save(a.ofertas, d)
        print(f'OK: {criados} novos, {atualizados} atualizados, {expirados} preços expirados')
    for e in erros:
        print('ERRO: ' + e)
    resumo(d, a.hoje)
    if erros:
        sys.exit(2 if not (criados or atualizados) else 0)


if __name__ == '__main__':
    main()
