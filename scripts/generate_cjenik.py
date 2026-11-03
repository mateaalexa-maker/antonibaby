#!/usr/bin/env python3
"""Single source of truth -> website product prices, CSVs, publicly visible 30-day archive.
No third-party Python libraries required. See UPUTE-AUTOMATIZACIJA.md.
"""
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
TZ=ZoneInfo('Europe/Zagreb')
REF='2026-09-10'

def money(x):
    try: d=Decimal(str(x))
    except InvalidOperation: raise ValueError(f'Invalid price: {x!r}')
    if not d.is_finite() or d < 0 or d.as_tuple().exponent < -2:
        raise ValueError(f'Invalid EUR price: {x!r}')
    return f'{d:.2f}'

def csv_bytes(columns,rows):
    out=StringIO(newline='')
    w=csv.writer(out,delimiter=';',lineterminator='\n')
    w.writerow(columns)
    w.writerows(rows)
    return ('\ufeff'+out.getvalue()).encode('utf-8')

def safe_write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or path.read_bytes()!=raw:
        path.write_bytes(raw)

def build(now=None):
    now=now or datetime.now(TZ)
    if now.tzinfo is None: raise ValueError('now must be timezone-aware')
    now=now.astimezone(TZ)
    data=json.loads((ROOT/'data/cijene.json').read_text(encoding='utf-8'))
    if data['reference_date']!=REF: raise ValueError('Reference date must remain fixed 2026-09-10')
    if len(data['products'])!=6: raise ValueError('Unexpected product count')
    codes=set()
    products=[]
    for p in data['products']:
        if p['code'] in codes or not re.fullmatch(r'[A-Za-z0-9-]+',p['code']): raise ValueError('Missing, invalid or duplicated product code')
        codes.add(p['code'])
        if p['availability'] not in ('dostupno','nedostupno'): raise ValueError(f'Availability required for {p["code"]}')
        if p['anchor_eur'] is None: raise ValueError('Anchor price cannot be blank')
        if p['special_sale'] and not p['special_sale_name'].strip():raise ValueError('Sale name required')
        money(p['price_eur']);money(p['anchor_eur'])
        products.append(p)
    for s in data['shipping']: money(s['price_eur']);money(s['anchor_eur'])
    cols=['Naziv','Šifra','Marka','Jedinica mjere','Cijena za jedinicu mjere (EUR)','Maloprodajna cijena (EUR)','Poseban oblik prodaje','Naziv posebnog oblika prodaje','Sidrena cijena (EUR)','Barkod','Dostupnost']
    rows=[[p['hr'],p['code'],p['brand'],p['unit'],money(p['price_eur']),money(p['price_eur']), 'da' if p['special_sale'] else 'ne',p['special_sale_name'] if p['special_sale'] else '',money(p['anchor_eur']),p.get('barcode') or '',p['availability']] for p in products]
    product_csv=csv_bytes(cols,rows)
    shipping_csv=csv_bytes(['Naziv usluge','Maloprodajna cijena (EUR)','Poseban oblik prodaje','Naziv posebnog oblika prodaje','Sidrena cijena (EUR)'],[[s['hr'],money(s['price_eur']),'ne','',money(s['anchor_eur'])] for s in data['shipping']])
    public=ROOT/'pricelists'
    safe_write(public/'cjenik.csv',product_csv)
    safe_write(public/'dostava.csv',shipping_csv)
    # Date-scoped public snapshots. Store type, street address, location ID,
    # sequence number, and local timestamp are included in the filename.
    archive=public/'arhiva'
    date=now.strftime('%Y-%m-%d')
    stamp=now.strftime('%Y-%m-%d_%H-%M')
    # Internal archive serial: latest existing number + 1 when data changes.
    # The official specification should be rechecked against any final regulations.
    prefix='obrt_Ulica-Mate-Vladica-163-Makarska_AB01'
    def store_snapshot(content,kind):
        files=sorted(archive.glob(f'{prefix}_*_{kind}.csv'))
        dated=[]
        for f in files:
            if f'_{date}_' in f.name: dated.append(f)
        if dated and dated[-1].read_bytes()==content:
            return dated[-1].name
        serials=[]
        for f in files:
            tail=f.name[len(prefix)+1:]
            candidate=tail.split('_',1)[0]
            if candidate.isdigit(): serials.append(int(candidate))
        n=max(serials,default=0)+1
        filename=f'{prefix}_{n:04d}_{stamp}_{kind}.csv'
        if (archive/filename).exists() and (archive/filename).read_bytes()!=content:
            raise ValueError('Conflicting snapshot filename: retry in one minute')
        safe_write(archive/filename,content)
        return filename
    store_snapshot(product_csv,'cjenik')
    store_snapshot(shipping_csv,'dostava')
    cutoff=(now.date()-timedelta(days=29)).isoformat()
    for f in archive.glob('*.csv'):
        match=re.search(r'_(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}_(?:cjenik|dostava)\.csv$',f.name)
        if match and match.group(1)<cutoff:
            f.unlink()
    entries=[]
    for f in archive.glob('*.csv'):
        match=re.search(r'_(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}_(cjenik|dostava)\.csv$',f.name)
        if match:
            entries.append({'filename':f.name,'url':'pricelists/arhiva/'+f.name,'date':match.group(1),'kind':'proizvodi' if match.group(2)=='cjenik' else 'dostava'})
    entries.sort(key=lambda v:v['filename'],reverse=True)
    safe_write(archive/'index.json',(json.dumps({'updated_at':now.isoformat(),'files':entries},ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    # Change price data in website's existing hardcoded product list at build time.
    app=ROOT/'app.js'
    js=app.read_text(encoding='utf-8')
    objs=[]
    for p in products:
        objs.append('{hr:'+json.dumps(p['hr'],ensure_ascii=False)+',en:'+json.dumps(p['en'],ensure_ascii=False)+',price:'+money(p['price_eur'])+',anchor:'+money(p['anchor_eur'])+',img:'+json.dumps(p['image'])+'}')
    new_products='const products=['+','.join(objs)+'];'
    js,n=re.subn(r'^const products=\[.*?\];',lambda m:new_products,js,count=1,flags=re.S)
    if n!=1:raise RuntimeError('Cannot update product pricing in app.js')
    # reference line stays untouched if reference price is unchanged and is always based on 10 Sep 2026
    js=js.replace(': ${euros(x.price)}</div></article>', ': ${euros(x.anchor)}</div></article>')
    js=js.replace(': ${euros(x.price)}</div>`', ': ${euros(x.anchor)}</div>`')
    # Derive the delivery cards from the same JSON as downloadable CSV.
    shipping=data['shipping']
    shipping_js='const shippingPrices='+json.dumps([float(s['price_eur']) for s in shipping])+';'
    js=re.sub(r'const shippingPrices=\[[^;]*;',lambda m:shipping_js,js)
    if 'const shippingPrices=' not in js:
        js=js.replace('const translations=',shipping_js+'const translations=',1)
    for code,ship in [('gls',shipping[0]),('box',shipping[1])]:
        en=f'Reference price 10 Sep 2026: €{money(ship["anchor_eur"])}'
        hr=f'Cijena 10. 9. 2026.: {money(ship["anchor_eur"]).replace(".",",")} €'
        # Replace translation strings for both languages
        js=re.sub(r"("+code+r"Anchor:')([^']*)(')",lambda m:m.group(1)+(en if 'en:{' in js[:m.start()] and js.rfind('en:{',0,m.start())>js.rfind('hr:{',0,m.start()) else hr)+m.group(3),js)
    if "document.querySelectorAll('.delivery .price-row strong')" not in js:
        js=js.replace("document.getElementById('priceTable').innerHTML=", "document.querySelectorAll('.delivery .price-row strong').forEach((e,i)=>e.textContent=euros(shippingPrices[i]));document.getElementById('priceTable').innerHTML=",1)
    safe_write(app,js.encode('utf-8'))
    htmlp=ROOT/'index.html';html=htmlp.read_text(encoding='utf-8')
    html=re.sub(r'(<span>GLS</span><strong>)[^<]+',lambda m:m.group(1)+money(data['shipping'][0]['price_eur']).replace('.',',')+' €',html)
    html=re.sub(r'(<span>BoxNow</span><strong>)[^<]+',lambda m:m.group(1)+money(data['shipping'][1]['price_eur']).replace('.',',')+' €',html)
    safe_write(htmlp,html.encode('utf-8'))
    # Shipping is not rendered from product data; update content and i18n dictionary using named placeholders.
    # Dynamic patch step is separate and idempotent.
    links='\n'.join(f'<li><a href="{f["filename"]}">{f["date"]} — {f["kind"]} (CSV)</a></li>' for f in entries)
    html_archive=f'''<!doctype html><html lang="hr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Antoni Baby — Arhiva cjenika</title><style>body{{font:16px system-ui,sans-serif;max-width:750px;margin:6vw auto;padding:0 24px;background:#f6f1eb;color:#25343c}}a{{color:#37535e}}li{{margin:12px 0}}h1{{font-weight:400}}</style></head><body><a href="../../index.html#prices">← Antoni Baby / Cjenik</a><h1>Arhiva digitalnih cjenika</h1><p>Objavljene verzije iz posljednjih 30 dana. Za najnoviji cjenik otvori <a href="../cjenik.csv">cjenik proizvoda</a> ili <a href="../dostava.csv">cjenik dostave</a>.</p><ul>{{links}}</ul></body></html>''' 
    safe_write(archive/'index.html',html_archive.encode('utf-8'))
    print('Generated CSVs, public archive and web product prices for',now.isoformat())

if __name__=='__main__':
    build()
