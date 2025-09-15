from flask import Flask, request, jsonify, redirect, send_from_directory, render_template_string
import sqlite3
import os
import string, random
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

DB_PATH = os.path.join(os.path.dirname(__file__), "links.db")

# Alternative domain configuration
ALT_DOMAIN = os.getenv('ALT_DOMAIN', None)
ALT_DOMAIN_ENABLED = ALT_DOMAIN is not None and ALT_DOMAIN.strip() != ''

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS links (
                id TEXT PRIMARY KEY,
                target TEXT NOT NULL,
                tracking_id TEXT,
                use_alt_domain BOOLEAN DEFAULT 0,
                add_utm BOOLEAN DEFAULT 0,
                apply_mask BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
    conn.commit()
    conn.close()

def generate_short_id(length=8):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def save_link(short_id, target, tracking_id=None, use_alt_domain=False, add_utm=False, apply_mask=True):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO links 
                (id, target, tracking_id, use_alt_domain, add_utm, apply_mask) 
                VALUES (?, ?, ?, ?, ?, ?)""", 
                (short_id, target, tracking_id, use_alt_domain, add_utm, apply_mask))
    conn.commit()
    conn.close()

def get_link_data(short_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT target, tracking_id, use_alt_domain, add_utm, apply_mask FROM links WHERE id = ?", (short_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'target': row[0],
            'tracking_id': row[1],
            'use_alt_domain': bool(row[2]),
            'add_utm': bool(row[3]),
            'apply_mask': bool(row[4])
        }
    return None

def get_target(short_id):
    link_data = get_link_data(short_id)
    return link_data['target'] if link_data else None

def add_utm_parameters(url, tracking_id=None):
    """Add UTM parameters to URL for better tracking"""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    utm_params = {
        'utm_source': 'affiliate_cloner',
        'utm_medium': 'cloned_link',
        'utm_campaign': 'affiliate_campaign'
    }
    
    if tracking_id:
        utm_params['utm_content'] = tracking_id
    
    for key, value in utm_params.items():
        if key not in query_params:
            query_params[key] = [value]
    
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def process_url_with_options(original_url, options):
    processed_url = original_url
    if options.get('add_utm', False):
        processed_url = add_utm_parameters(processed_url, options.get('tracking_id'))
    return processed_url

app = Flask(__name__, static_folder='static', static_url_path='/static')

init_db()

# ---------------------------------
# ROTAS (mantive todas suas rotas)
# ---------------------------------

@app.route('/')
def index():
    return render_template_string(HOME_HTML)

@app.route('/api/shorten', methods=['POST'])
def shorten():
    data = request.get_json(force=True)
    if not data or 'url' not in data:
        return jsonify({'error': 'missing url'}), 400
    url = data['url'].strip()
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return jsonify({'error': 'url must start with http:// or https://'}), 400
    
    short_id = generate_short_id(8)
    tries = 0
    while get_target(short_id) and tries < 5:
        short_id = generate_short_id(8)
        tries += 1
    
    save_link(short_id, url)
    short_url = request.host_url.rstrip('/') + '/' + short_id
    return jsonify({'short_id': short_id, 'short_url': short_url}), 200

@app.route('/api/clone', methods=['POST'])
def clone_link():
    data = request.get_json(force=True)
    if not data or 'url' not in data:
        return jsonify({'error': 'missing url'}), 400
    
    original_url = data['url'].strip()
    parsed = urlparse(original_url)
    if parsed.scheme not in ('http', 'https'):
        return jsonify({'error': 'url must start with http:// or https://'}), 400
    
    custom_domain = data.get('customDomain', '').strip()
    options = {
        'use_alt_domain': data.get('useAltDomain', False),
        'custom_domain': custom_domain if custom_domain else None,
        'add_utm': data.get('addUtm', False),
        'tracking_id': data.get('trackingId', '').strip() or None,
        'apply_mask': data.get('applyMask', True)
    }
    
    processed_url = process_url_with_options(original_url, options)
    
    short_id = generate_short_id(8)
    tries = 0
    while get_target(short_id) and tries < 5:
        short_id = generate_short_id(8)
        tries += 1
    
    if tries >= 5:
        return jsonify({'error': 'failed to generate unique id'}), 500
    
    save_link(
        short_id,
        processed_url,
        tracking_id=options['tracking_id'],
        use_alt_domain=options['use_alt_domain'],
        add_utm=options['add_utm'],
        apply_mask=options['apply_mask']
    )
    
    custom_domain_used = False
    alt_domain_used = False
    
    if options['use_alt_domain']:
        if options['custom_domain']:
            custom_domain = options['custom_domain']
            if not custom_domain.startswith(('http://', 'https://')):
                custom_domain = 'https://' + custom_domain
            cloned_url = custom_domain.rstrip('/') + '/' + short_id
            custom_domain_used = True
        elif ALT_DOMAIN_ENABLED and ALT_DOMAIN:
            if not ALT_DOMAIN.startswith(('http://', 'https://')):
                alt_domain = 'https://' + ALT_DOMAIN
            else:
                alt_domain = ALT_DOMAIN
            cloned_url = alt_domain.rstrip('/') + '/' + short_id
            alt_domain_used = True
        else:
            cloned_url = request.host_url.rstrip('/') + '/' + short_id
    else:
        cloned_url = request.host_url.rstrip('/') + '/' + short_id
    
    return jsonify({
        'short_id': short_id,
        'cloned_url': cloned_url,
        'original_url': original_url,
        'processed_url': processed_url,
        'masked': options['apply_mask'],
        'utm_added': options['add_utm'],
        'tracking_id': options['tracking_id'],
        'alt_domain_enabled': ALT_DOMAIN_ENABLED,
        'alt_domain_used': alt_domain_used,
        'custom_domain_used': custom_domain_used,
        'custom_domain': options['custom_domain'] if custom_domain_used else None
    }), 200

@app.route('/go/<short_id>')
def final_redirect(short_id):
    target = get_target(short_id)
    if not target:
        return "Link não encontrado", 404
    return redirect(target, code=302)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'link-cloner'}), 200

@app.route('/api/config')
def get_config():
    return jsonify({
        'alt_domain_enabled': ALT_DOMAIN_ENABLED,
        'alt_domain': ALT_DOMAIN if ALT_DOMAIN_ENABLED else None,
        'service': 'link-cloner',
        'features': {
            'url_masking': True,
            'utm_parameters': True,
            'alternative_domain': ALT_DOMAIN_ENABLED,
            'tracking_id': True
        }
    }), 200

@app.route('/<short_id>')
def redirect_short(short_id):
    link_data = get_link_data(short_id)
    if not link_data:
        return "Link não encontrado", 404
    
    target = link_data['target']
    apply_mask = link_data['apply_mask']
    
    if not apply_mask:
        return redirect(target, code=302)
    
    return render_template_string(MASK_PAGE_HTML, target_url=target, short_id=short_id)

# ------------------------------
# Execução local (Render usa Procfile + gunicorn)
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
