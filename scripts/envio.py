#!/usr/bin/env python3
"""AchadosMM: escolhe a oferta da BASE DO SITE para o envio ao grupo (tarefa "AchadosMM — envio ao grupo").

Uso:
  python3 scripts/envio.py ofertas.js enviados.json --hoje AAAA-MM-DD
    enviados.json = lista das linhas da Fila dos últimos 30 dias com status enviado/enviado-texto/enviando:
                    [{"data": "AAAA-MM-DD", "titulo": D, "tipo": S, "id": V, "categoria": C}, ...]
  Imprime o item escolhido (JSON do ofertas.js) ou "NENHUM".

Regras (decisão do Erick em 23/11: nada de repetir produto):
  - candidatos: ativo, link meli.la, imagem, ciclo Quinzenal/Mensal/Bimestral/Trimestral;
  - fora: o mesmo produto (id ou título) enviado nos últimos 30 dias; mesmo tipo ou mesma família (1ª palavra do título: luva, bobina, etiqueta,
    saco...) enviados nos últimos 7 dias, e categoria já enviada hoje;
  - ordem: preço conferido hoje > preço de até 7 dias (mais recente) > sem preço; depois quantidade
    no título (o post mostra quanto sai cada unidade); ciclo mais curto; maior desconto; mais vendidos.
"""
import argparse, datetime as dt, json, re, sys, unicodedata

CICLOS = ['Quinzenal', 'Mensal', 'Bimestral', 'Trimestral']
PARAR = {'de', 'da', 'do', 'para', 'com', 'e', 'em', 'kit', 'refil', 'caixa', 'pacote', 'rolo', 'par'}
sys.path.insert(0, __import__('os').path.dirname(__file__))
from postagem import separa_qtd  # noqa: E402


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9 ]+', ' ', s)


def familia(titulo):
    for w in norm(titulo).split():
        if w not in PARAR and not w.isdigit() and len(w) > 2:
            return w
    return ''


def ler_ofertas(caminho):
    t = open(caminho, encoding='utf-8').read()
    return json.loads(t[t.index('\nwindow.ACHADOS = ') + 18:t.rindex(';')])['ofertas']


def escolher(ofertas, enviados, hoje, dias_familia=7):
    h = dt.date.fromisoformat(hoje)

    def recente(d, n):
        try:
            return 0 <= (h - dt.date.fromisoformat(str(d).lstrip("'")[:10])).days < n
        except ValueError:
            return False
    ids = {e.get('id') for e in enviados if recente(e.get('data'), 30) and e.get('id')}
    titulos = {norm(e.get('titulo')) for e in enviados if recente(e.get('data'), 30)}
    tipos = {e.get('tipo') for e in enviados if recente(e.get('data'), dias_familia) and e.get('tipo')}
    fams = {familia(e.get('titulo')) for e in enviados if recente(e.get('data'), dias_familia)}
    cats_hoje = {e.get('categoria') for e in enviados if recente(e.get('data'), 1)}
    cand = []
    for o in ofertas:
        if o.get('ativo') is False or not str(o.get('link', '')).startswith('https://meli.la/') or not o.get('imagem'):
            continue
        if o.get('ciclo') not in CICLOS or o.get('id') in ids or norm(o.get('titulo')) in titulos or o.get('tipo') in tipos:
            continue
        if familia(o.get('titulo')) in fams or o.get('categoria') in cats_hoje:
            continue
        cand.append(o)

    def chave(o):
        try:
            dias = (h - dt.date.fromisoformat(o.get('vistoEm') or '')).days if o.get('preco') else 99
        except ValueError:
            dias = 99
        grupo = 0 if dias == 0 else (1 if 0 < dias <= 7 else 2)
        tem_qtd = 0 if separa_qtd(o.get('titulo') or '')[1] else 1
        desc = 1 - o['preco'] / o['precoDe'] if o.get('preco') and o.get('precoDe') and o['precoDe'] > o['preco'] else 0
        return (grupo, dias if grupo == 1 else 0, tem_qtd, CICLOS.index(o['ciclo']), -desc, -(o.get('vendidosNum') or 0))
    cand.sort(key=chave)
    if not cand and dias_familia > 4:
        return escolher(ofertas, enviados, hoje, 4)
    return cand[0] if cand else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ofertas')
    ap.add_argument('enviados')
    ap.add_argument('--hoje', required=True)
    a = ap.parse_args()
    o = escolher(ler_ofertas(a.ofertas), json.load(open(a.enviados, encoding='utf-8')), a.hoje)
    print(json.dumps(o, ensure_ascii=False) if o else 'NENHUM')


if __name__ == '__main__':
    main()
