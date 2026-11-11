"""NEXUS Browser: limited public-web reader, not a full browser or general proxy."""
import ipaddress
import os
import re
import socket
from urllib.parse import urljoin, urlparse, quote, parse_qs, unquote
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')
app.json.ensure_ascii = False
AGENT = 'NEXUSReader/1.0 (public web reader; contact site operator for opt-out)'
HEADERS = {'User-Agent': AGENT, 'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.3'}
MAX_BODY = 1_500_000

@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    # Allow the one-file Chromebook frontend (Origin: null) to call its hosted reader.
    if request.headers.get('Origin') == 'null':
        response.headers['Access-Control-Allow-Origin'] = 'null'
        response.headers['Vary'] = 'Origin'
    return response

def safe_url(value):
    if not isinstance(value, str) or len(value) > 2048: raise ValueError('Invalid website address')
    value = value.strip()
    if not value: raise ValueError('Enter a website address')
    if not re.match(r'^https?://', value, re.I): value = 'https://' + value
    u = urlparse(value)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.port not in (None,80,443):
        raise ValueError('Only public HTTP and HTTPS websites are supported')
    hostname = u.hostname.lower().rstrip('.')
    if hostname in ('localhost',) or hostname.endswith(('.localhost', '.local', '.internal', '.test')) or '.' not in hostname:
        raise ValueError('Private and local network addresses are blocked')
    try:
        ips = [r[4][0] for r in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)]
    except (socket.gaierror, OSError):
        raise ValueError('Website address could not be resolved')
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise ValueError('Private and reserved networks are blocked')
    return u.geturl()

def fetch_public(url):
    # Prevent redirects to private/local networks. This prototype must not be used as an unrestricted proxy.
    session = requests.Session()
    session.trust_env = False
    for _ in range(5):
        url = safe_url(url)
        try:
            with session.get(url, headers=HEADERS, timeout=(5, 12), allow_redirects=False, stream=True) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    dest = r.headers.get('location')
                    if not dest: raise ValueError('Website returned an incomplete redirect')
                    url = urljoin(url, dest)
                    continue
                r.raise_for_status()
                content_type = r.headers.get('Content-Type', '').lower()
                if not ('text/html' in content_type or 'application/xhtml+xml' in content_type):
                    raise ValueError('NEXUS Reader supports public HTML pages only')
                size = 0; parts = []
                for chunk in r.iter_content(16384):
                    size += len(chunk)
                    if size > MAX_BODY: raise ValueError('This page is too large for Reader mode')
                    parts.append(chunk)
                encoding = r.encoding or 'utf-8'
                return url, b''.join(parts).decode(encoding, errors='replace')
        except requests.RequestException as exc:
            raise ValueError('Unable to load this website. It might block automated readers.') from exc
    raise ValueError('Too many website redirects')

def extract_page(url, html):
    soup = BeautifulSoup(html, 'html.parser')
    for n in soup(['script','style','noscript','template','svg','iframe','form','nav','footer','header','aside','button','input','textarea']): n.decompose()
    title = soup.title.get_text(' ', strip=True) if soup.title else urlparse(url).hostname
    root = soup.select_one('article') or soup.select_one('main') or soup.body or soup
    blocks = []
    total_chars = 0
    for el in root.find_all(['h1','h2','h3','p','li','blockquote','img'], recursive=True):
        if el.find_parent(['p','li','blockquote']) and el.name != 'img': continue
        if el.name == 'img':
            if el.find_parent(['p','li','blockquote']): continue
            src = urljoin(url, el.get('src',''))
            if src.startswith('https://') and len(src) < 1500 and len(blocks)<100:
                blocks.append({'type':'image','src':src,'alt':(el.get('alt') or '')[:180]})
            continue
        text = el.get_text(' ', strip=True)
        if len(text) < 3: continue
        if len(text) > 2200: text = text[:2200]
        links = []
        for a in el.find_all('a', href=True, limit=8):
            dest = urljoin(url, a['href'])
            if dest.startswith(('https://','http://')):
                links.append({'title':a.get_text(' ', strip=True)[:100] or dest[:60], 'url':dest})
        blocks.append({'type':el.name,'text':text,'links':links})
        total_chars += len(text)
        if len(blocks)>=100 or total_chars>19000: break
    return {'title':title[:180], 'url':url, 'blocks':blocks, 'note':'Reader mode displays extracted content, not the full interactive website.'}

@app.get('/')
def root(): return send_from_directory('.', 'index.html')

@app.get('/health')
def health(): return jsonify({'ok':True,'service':'NEXUS Reader'})

@app.get('/api/read')
def read():
    try:
        url, html = fetch_public(request.args.get('url',''))
        return jsonify(extract_page(url, html))
    except ValueError as exc: return jsonify({'error':str(exc)}), 422

@app.get('/api/search')
def search():
    q = request.args.get('q','').strip()
    if not q or len(q)>180: return jsonify({'error':'Enter a search of 1 to 180 characters'}), 400
    # Search without credentials using Wikipedia's public MediaWiki search API.
    # Not Google or general web search; results link to real articles shown in NEXUS Reader.
    api = 'https://en.wikipedia.org/w/api.php'
    try:
        r = requests.get(api, params={'action':'query','list':'search','srsearch':q,'srlimit':12,'format':'json','utf8':1},
                         headers={'User-Agent':'NEXUSBrowserReader/1.0 (educational prototype)'},timeout=12)
        r.raise_for_status()
        items = r.json().get('query',{}).get('search',[])
        results=[]
        for it in items:
            label = it.get('title','')
            snippet = BeautifulSoup(it.get('snippet',''), 'html.parser').get_text(' ', strip=True)
            results.append({'title':label,'url':'https://en.wikipedia.org/wiki/'+quote(label.replace(' ','_')),'snippet':snippet})
        return jsonify({'engine':'Wikipedia','results':results})
    except (requests.RequestException, ValueError, KeyError):
        return jsonify({'error':'Search is unavailable right now. You can still enter a website address.'}),502

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT','5000')), debug=False)
