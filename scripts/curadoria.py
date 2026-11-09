#!/usr/bin/env python3
"""Curadoria AchadosMM: aplica as ofertas do dia no ofertas.js do site.

Uso:
  python3 scripts/curadoria.py ofertas.js novos.json --hoje AAAA-MM-DD
  python3 scripts/curadoria.py ofertas.js --resumo        (só mostra o estado)

novos.json = lista de ofertas conferidas hoje. Campos aceitos:
  id (opcional: atualiza o item com esse id), titulo, marca, categoria, loja, link,
  preco, precoDe, vendidos, vendidosNum, porQueVale, seloTecnico, full, freteGratis,
  imagem, mlb (id do anúncio no Mercado Livre, só números; usado para conferir o preço), ciclo (Quinzenal, Mensal, Bimestral, Trimestral, Semestral, Anual / sazonal ou vazio), tipo (id de public.tipos_produto no Supabase, ex.: luva, etiqueta-termica), destaque (true = entra em "Destaques do dia" e conta como oferta nova).

Regras aplicadas:
  - casa pelo id; sem id, pelo título normalizado; senão cria item novo;
  - preco/precoDe só valem com vistoEm = hoje; preço visto há mais de 7 dias é apagado
    (o card volta a "Confira o preço do dia na loja");
  - link precisa começar com https://; preco precisa ser número > 0;
  - categoria precisa existir em "categorias";
  - instrumento de medição (balança, peso, termômetro, termo-higrômetro, pHmetro etc.) só entra
    com Inmetro, certificado de calibração ou marca de laboratório no título; de cozinha, bolso,
    joia ou aquário sai do site (ativo false) e aparece como ERRO;
  - imagem precisa ser a foto do anúncio (https://http2.mlstatic.com/...): item novo sem foto
    não entra, e o site só mostra itens com foto.

  python3 scripts/curadoria.py ofertas.js --sem-foto lista.json   (grava os itens ativos sem foto,
    para a curadoria buscar a imagem no painel; use o id deles no novos.json com o campo imagem)
Imprime "SEM MUDANCA" quando nada mudou.
"""
import argparse, datetime as dt, json, re, sys, unicodedata

IMG_RE = re.compile(r'^https://http2\.mlstatic\.com/\S+\.(jpg|jpeg|png|webp)$')

PREFIX = 'window.ACHADOS = '
HEAD = ('/* AchadosMM: base de ofertas. Gerado pela Curadoria AchadosMM (scripts/curadoria.py). '
        'Não editar à mão: o objeto abaixo é JSON puro. */\n')
CAMPOS = ['titulo', 'marca', 'categoria', 'loja', 'link', 'preco', 'precoDe', 'vendidos',
          'vendidosNum', 'tipo', 'porQueVale', 'seloTecnico', 'full', 'freteGratis', 'imagem', 'ciclo', 'mlb', 'ativo']


# Tipo de produto (id de public.tipos_produto no Supabase) deduzido pelo título
# quando a curadoria não informa "tipo". Usado no site para casar ofertas com o
# que cada farmácia marcou em "Minha farmácia".
TIPOS_RE = [
    ('mesa-balanca', r'mesa.*(anti.?vibra|balan)'), ('balanca-postal', r'balan\w* (postal|de envio|encomenda)'),
    ('balanca-precisao', r'balan\w* .*(precis|anal[ií]tica|semi.?anal)'), ('termo-higrometro', r'higr[oô]metro'),
    ('termometro-geladeira', r'term[oô]metro.*(geladeira|freezer|refrigerador|vacina)'), ('vidraria', r'b[ée]quer|proveta|bal[aã]o volum|erlenmeyer|vidraria'),
    ('gral-pistilo', r'gral|pistilo|almofariz'), ('espatula', r'esp[aá]tula'), ('agitador-magnetico', r'agitador magn'),
    ('banho-maria', r'banho.?maria'), ('fogao-chapa', r'fog[aã]o|chapa (el[eé]trica|aquecedora)|cooktop'),
    ('mixer', r'mixer|homogeneizador|misturador'), ('cronometro', r'cron[oô]metro|timer'), ('pisseta', r'pisseta'),
    ('jarra-graduada', r'jarra'), ('colher-descartavel', r'colher'), ('carrinho-auxiliar', r'carrinho'),
    ('luva', r'\bluva'), ('touca-prope', r'touca|prop[eé]'), ('mascara', r'm[aá]scara'), ('jaleco-avental', r'jaleco|avental'),
    ('dispenser', r'dispenser|saboneteira'), ('papel-toalha', r'papel toalha|interfolha'), ('limpeza', r'esponja|detergente|pano|desinfetante|rodo|vassoura|mop'),
    ('etiquetadora', r'etiquetadora|rotulador'), ('ribbon', r'ribbon'), ('etiqueta-termica', r'etiqueta.*t[eé]rmica|t[eé]rmica.*etiqueta|10x15'),
    ('etiqueta-adesiva', r'etiqueta'), ('estrado', r'estrado|pallet|palete'), ('caixa-organizadora', r'caixa organizadora|organizador.*(gaveta|caixa)'),
    ('prateleira', r'prateleira(?!.*divisor)|estante (de )?a[cç]o|estante(?!.*tubo)'), ('gaveteiro', r'gaveteiro'), ('escada', r'escada|banqueta'), ('veda-porta', r'veda.?porta'),
    ('papel-sulfite', r'sulfite|papel a4|resma'), ('pastas-arquivo', r'pasta|arquivo morto|fichário'), ('fragmentadora', r'fragmentadora|trituradora'),
    ('guilhotina', r'guilhotina'), ('papelaria', r'grampeador|clipe|clips|post.?it|tesoura|caneta|organizador'), ('calculadora', r'calculadora'),
    ('impressora', r'impressora|toner|cartucho'), ('leitor-codigo', r'leitor.*c[oó]digo|scanner'), ('nobreak-filtro', r'nobreak|filtro de linha|r[eé]gua (de )?(extens|\d+ tomadas|tomadas)'),
    ('suporte-monitor', r'suporte.*monitor'), ('roteador', r'roteador|repetidor'), ('teclado-mouse', r'teclado|mouse'), ('pilhas', r'pilha|bateria'),
    ('fone-headset', r'fone|headset'), ('suporte-celular', r'suporte.*celular'), ('bolsa-termica', r'bolsa t[eé]rmica|caixa t[eé]rmica|bag'),
    ('fita-adesiva', r'fita (adesiva|durex|lacradora|transparente)|suporte.*fita'), ('envelope', r'envelope'), ('protecao-entregador', r'manguito|capa de chuva'),
    ('cafeteira-bule', r'cafeteira|bule|garrafa t[eé]rmica'), ('micro-ondas', r'micro.?ondas'), ('frigobar', r'frigobar'),
    ('bebedouro', r'bebedouro|purificador (de [aá]gua|hidro)|hidrofiltros|refil ibbl'), ('aquecedor', r'aquecedor'),
    # tipos da revisão de 05/11/2026 (só entram quando nenhum tipo acima casou)
    ('phmetro', r'\bph\b|phmetro|condutiv|solu[cç][aã]o tamp[aã]o'),
    ('instrumentos-cq', r'ponto de fus[aã]o|man[oô]metro|paqu[ií]metro|\blupa\b|term[oô]metro'),
    ('encapsuladora', r'encapsulad|contador de c[aá]psulas'), ('purificacao-agua', r'osmose|deionizador|refil.*micras'),
    ('equipamentos-lab', r'estufa|capela|seladora|ultrass[oô]nica'),
    ('utensilios-lab', r'pipeta|tamis|pin[cç]a|placa de vidro|papel (de )?pesagem|papel filtro|barquinha|seringa|autoclave|s[ií]lica gel'),
    ('residuos', r'lixeira|saco de lixo|perfurocortante'), ('higiene-maos', r'[aá]lcool gel|sabonete'),
    ('protecao-individual', r'[oó]culos de prote|face shield|protetor facial|sapato|cal[cç]ado'),
    ('papel-higienico', r'papel higi[eê]nico|len[cç]o de papel'), ('primeiros-socorros', r'primeiros socorros|lava.?olhos'),
    ('iluminacao', r'l[aâ]mpada|lumin[aá]ria|plafon|interruptor'),
    ('seguranca', r'c[aâ]mera|cadeado|alarme|sensor de presen|fechadura|detector de fuma'),
    ('armario', r'arm[aá]rio|roupeiro|cabideiro'), ('controle-pragas', r'armadilha|mosquiteira|insetos'),
    ('climatizacao', r'ar.?condicionado|cortina de ar|ventilador|desumidificador'), ('sinalizacao', r'placa|cone |fita zebrada'),
    ('manutencao', r'parafus|veda rosca|fita isolante|ferramenta|trena|silicone|tinta|n[ií]vel'),
    ('mobiliario', r'cadeira|longarina|ergon[oô]mic|antifadiga'), ('financeiro', r'cofre|malote|c[eé]dulas'),
    ('rotina-equipe', r'quadro|crach[aá]|rel[oó]gio de ponto|medalha'),
    ('computador', r'computador|\bpc\b|monitor|tablet|notebook|webcam|mem[oó]ria ram|celular|power bank|carregador'),
    ('rede-cabos', r'cabo|rj45|switch|\bssd\b|\bhd\b|pendrive|canaleta|abra[cç]adeira|certificado digital'),
    ('balcao', r'gaveta de dinheiro|troco|expositor|display|campainha|sineta|cestinha|painel de senha|precificador|bobina'),
    ('foto-video', r'ring light|trip[eé]|est[uú]dio fotogr|microfone'), ('decoracao', r'natal|guirlanda|pisca'),
    ('acessorio-moto', r'\bmoto\b|ba[uú] '), ('descartaveis-copa', r'copo descart|guardanapo|filtro de papel|filme pvc'),
    ('utensilios-copa', r'caneca|faqueiro|pote de vidro|sanduicheira|squeeze'),
]


# Somos farmácia: instrumento de medição e controle só entra com Inmetro ou certificado
# de calibração informado no anúncio, ou de marca de laboratório. Nunca de cozinha,
# bolso, joia, aquário ou "5 em 1".
TIPOS_MEDICAO = {'balanca-precisao', 'termo-higrometro', 'termometro-geladeira', 'phmetro', 'instrumentos-cq'}
MEDICAO_OK = re.compile(r'inmetro|certificad|\brbc\b|marte|shimadzu|\bbel\b|gehaka|urano|incoterm|instrutherm|akso|akrom|testo|milwaukee|hanna|impac|merck|kasvi|elitech|bomvink|peguepet', re.I)
MEDICAO_NAO = re.compile(r'cozinha|culin[aá]ri|bolso|joia|j[oó]ias|corporal|bioimped|aqu[aá]rio|piscina|5 em 1|tds', re.I)
UTENSILIO_NAO = re.compile(r'funil de cozinha|papel manteiga', re.I)


def medicao_inadequada(o):
    t = (o.get('titulo') or '') + ' ' + (o.get('marca') or '')
    if UTENSILIO_NAO.search(t):
        return 'utensílio de cozinha no lugar de material de laboratório'
    if o.get('tipo') == 'mesa-balanca' or re.search(r'\blupa|mesa anti', t, re.I):
        return ''
    if o.get('tipo') in TIPOS_MEDICAO or o.get('seloTecnico') and re.search(r'balan|term[oô]m|higr|\bph|peso', t, re.I):
        if MEDICAO_NAO.search(t):
            return 'instrumento de medição de cozinha, bolso, joia ou aquário'
        if not MEDICAO_OK.search(t):
            return 'instrumento de medição sem Inmetro, certificado ou marca de laboratório no anúncio'
    return ''


def tipo_por_titulo(t):
    t = unicodedata.normalize('NFC', (t or '').lower())
    for tid, rx in TIPOS_RE:
        if re.search(rx, t):
            return tid
    return ''


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
    sem_foto = [o for o in of if not IMG_RE.match(o.get('imagem') or '')]
    por_cat = {}
    for o in of:
        por_cat[o['categoria']] = por_cat.get(o['categoria'], 0) + 1
    print(f"itens ativos: {len(of)} | com preço conferido: {len(com_preco)} | com link de afiliado: {len(afil)} "
          f"| sem link de afiliado: {len(of) - len(afil)} | sem foto (fora do site): {len(sem_foto)} | destaques de {hoje}: {len(novos)}")
    print('por categoria: ' + ', '.join(f'{k} {v}' for k, v in sorted(por_cat.items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ofertas')
    ap.add_argument('novos', nargs='?')
    ap.add_argument('--hoje', default=dt.date.today().isoformat())
    ap.add_argument('--resumo', action='store_true')
    ap.add_argument('--sem-foto', metavar='ARQ')
    a = ap.parse_args()
    d = load(a.ofertas)
    if a.sem_foto:
        lst = [{k: o.get(k, '') for k in ('id', 'titulo', 'marca', 'categoria', 'tipo', 'mlb', 'link')}
               for o in d['ofertas'] if o.get('ativo', True) and not IMG_RE.match(o.get('imagem') or '')]
        json.dump(lst, open(a.sem_foto, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'{len(lst)} itens ativos sem foto gravados em {a.sem_foto}')
        return
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
        if n.get('imagem') and not IMG_RE.match(str(n['imagem'])):
            erros.append(f"imagem inválida (precisa ser https://http2.mlstatic.com/...): {t or n.get('id')}"); continue
        o = by_id.get(n.get('id')) or by_key.get(key(t))
        if o is None:
            if not n.get('imagem'):
                erros.append(f'item novo sem foto (imagem do card): {t or n}'); continue
            if not (t and n.get('categoria') and n.get('link')):
                erros.append(f'item novo sem titulo/categoria/link: {t or n}'); continue
            base = slug(t); nid = base; i = 2
            while nid in by_id:
                nid = f'{base}-{i}'; i += 1
            o = {'id': nid, 'titulo': t, 'marca': '', 'categoria': n['categoria'], 'loja': 'Mercado Livre',
                 'link': n['link'], 'preco': None, 'precoDe': None, 'vendidos': '', 'vendidosNum': 0,
                 'porQueVale': '', 'tipo': '', 'ciclo': '', 'mlb': '', 'seloTecnico': False, 'full': False, 'freteGratis': False, 'imagem': '',
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
        if n.get('tipo') == '':
            o['tipo'] = ''  # "tipo": "" = item sem tipo de produto (não deduz pelo título)
        elif not o.get('tipo'):
            o['tipo'] = tipo_por_titulo(o.get('titulo'))
        if n.get('destaque'):
            o['adicionadoEm'] = a.hoje
        motivo = medicao_inadequada(o)
        if motivo and o.get('ativo', True):
            o['ativo'] = False
            erros.append(f"fora do site ({motivo}): {o['titulo']}")
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
