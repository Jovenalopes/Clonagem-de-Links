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
    
    # Add default UTM parameters
    utm_params = {
        'utm_source': 'affiliate_cloner',
        'utm_medium': 'cloned_link',
        'utm_campaign': 'affiliate_campaign'
    }
    
    if tracking_id:
        utm_params['utm_content'] = tracking_id
    
    # Merge with existing parameters
    for key, value in utm_params.items():
        if key not in query_params:
            query_params[key] = [value]
    
    # Rebuild query string
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def process_url_with_options(original_url, options):
    """Process URL with advanced options"""
    processed_url = original_url
    
    # Add UTM parameters if requested
    if options.get('add_utm', False):
        processed_url = add_utm_parameters(processed_url, options.get('tracking_id'))
    
    return processed_url

app = Flask(__name__, static_folder='static', static_url_path='/static')

init_db()

# Modern affiliate link cloning interface
# Masking page template for affiliate links
MASK_PAGE_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Redirecionando...</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            max-width: 500px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            text-align: center;
        }
        
        .icon {
            font-size: 48px;
            margin-bottom: 20px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.8em;
        }
        
        p {
            color: #666;
            margin-bottom: 25px;
            line-height: 1.5;
        }
        
        .url-display {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            word-break: break-all;
            font-family: monospace;
            font-size: 14px;
            color: #495057;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            text-decoration: none;
            display: inline-block;
            margin: 10px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .countdown {
            color: #28a745;
            font-weight: bold;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🔗</div>
        <h1>Link Seguro</h1>
        <p>Você está sendo redirecionado para um link de afiliado. Por segurança, confirme se deseja continuar.</p>
        
        <div class="url-display">
            {{ target_url | e }}
        </div>
        
        <div>
            <a href="/go/{{ short_id }}" class="btn">Continuar</a>
            <a href="/" class="btn btn-secondary">Voltar</a>
        </div>
        
        <p style="margin-top: 20px; font-size: 12px; color: #999;">
            Redirecionamento automático em <span class="countdown" id="countdown">10</span> segundos
        </p>
    </div>
    
    <script>
        let countdown = 10;
        const countdownElement = document.getElementById('countdown');
        
        const timer = setInterval(() => {
            countdown--;
            countdownElement.textContent = countdown;
            
            if (countdown <= 0) {
                clearInterval(timer);
                window.location.href = '/go/{{ short_id }}';
            }
        }, 1000);
    </script>
</body>
</html>"""

HOME_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ferramenta de Clonagem de Links de Afiliados</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.2em;
            margin-bottom: 10px;
            font-weight: 600;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
            line-height: 1.5;
        }
        
        .content {
            padding: 40px 30px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            color: #333;
            font-size: 1.4em;
            margin-bottom: 20px;
            font-weight: 600;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        
        .form-group input[type="text"], .form-group input[type="url"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e1e1;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .checkbox-group input[type="checkbox"] {
            margin-right: 10px;
            transform: scale(1.2);
        }
        
        .checkbox-group label {
            margin: 0;
            cursor: pointer;
        }
        
        .recommended {
            background: #e8f5e8;
            color: #2d5a2d;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-left: 10px;
        }
        
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            width: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .result {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .preview-section {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 15px;
            margin-top: 20px;
        }
        
        .preview-content {
            text-align: center;
            color: #666;
            font-style: italic;
        }
        
        .error {
            color: #dc3545;
            background: #f8d7da;
            padding: 15px;
            border-radius: 10px;
            margin-top: 10px;
        }
        
        .success {
            color: #155724;
            background: #d4edda;
            padding: 15px;
            border-radius: 10px;
            margin-top: 10px;
        }
        
        .copy-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            margin-left: 10px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .advanced-options {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Ferramenta de Clonagem de Links de Afiliados</h1>
            <p>Clone e personalize seus links de afiliado para campanhas de Google Ads. Evite bloqueios e mantenha o rastreamento de comissão.</p>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>Gerador de Links</h2>
                <p style="color: #666; margin-bottom: 20px;">Configure e clone seu link de afiliado</p>
                
                <form id="linkForm">
                    <div class="form-group">
                        <label for="originalUrl">Link de Afiliado Original</label>
                        <input type="url" id="originalUrl" placeholder="https://exemplo.com/affiliate?id=123" required>
                    </div>
                    
                    <div class="advanced-options">
                        <h3 style="margin-bottom: 20px; color: #333;">Opções Avançadas</h3>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" id="useAltDomain">
                            <label for="useAltDomain">Usar Domínio Alternativo</label>
                        </div>
                        
                        <div class="form-group" id="customDomainGroup" style="display: none; margin-left: 25px; margin-top: 10px;">
                            <input type="text" id="customDomain" placeholder="ex: meu-dominio.com" style="width: 100%; padding: 12px; border: 2px solid #e1e1e1; border-radius: 8px; font-size: 14px;">
                        </div>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" id="addUtm">
                            <label for="addUtm">Adicionar Parâmetros UTM</label>
                        </div>
                        
                        <div class="form-group">
                            <label for="trackingId">Tracking ID (Opcional)</label>
                            <input type="text" id="trackingId" placeholder="SEU_ID_DE_TRACKING">
                        </div>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" id="applyMask" checked>
                            <label for="applyMask">Aplicar Máscara de URL</label>
                            <span class="recommended">Recomendado</span>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn">Clonar Link</button>
                </form>
                
                <div id="result"></div>
            </div>
            
            <div class="section">
                <div class="preview-section">
                    <h2>Pré-visualização do Destino</h2>
                    <p style="color: #666; margin-bottom: 20px;">Visualize onde o link direciona</p>
                    
                    <div id="previewContent" class="preview-content">
                        Cole um link e clique em "Clonar Link" para ver a pré-visualização
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('linkForm').onsubmit = async function(e) {
            e.preventDefault();
            
            const formData = {
                url: document.getElementById('originalUrl').value,
                useAltDomain: document.getElementById('useAltDomain').checked,
                customDomain: document.getElementById('customDomain').value.trim(),
                addUtm: document.getElementById('addUtm').checked,
                trackingId: document.getElementById('trackingId').value,
                applyMask: document.getElementById('applyMask').checked
            };
            
            try {
                const response = await fetch('/api/clone', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById('result');
                
                if (response.ok) {
                    // Create success div securely
                    const successDiv = document.createElement('div');
                    successDiv.className = 'success';
                    
                    const title = document.createElement('h3');
                    title.textContent = 'Link Clonado com Sucesso!';
                    successDiv.appendChild(title);
                    
                    const linkP = document.createElement('p');
                    const linkLabel = document.createElement('strong');
                    linkLabel.textContent = 'Link Clonado: ';
                    const linkA = document.createElement('a');
                    linkA.href = result.cloned_url;
                    linkA.target = '_blank';
                    linkA.textContent = result.cloned_url;
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'copy-btn';
                    copyBtn.textContent = 'Copiar';
                    copyBtn.onclick = () => copyToClipboard(result.cloned_url);
                    
                    linkP.appendChild(linkLabel);
                    linkP.appendChild(linkA);
                    linkP.appendChild(document.createTextNode(' '));
                    linkP.appendChild(copyBtn);
                    successDiv.appendChild(linkP);
                    
                    const idP = document.createElement('p');
                    const idLabel = document.createElement('strong');
                    idLabel.textContent = 'ID: ';
                    idP.appendChild(idLabel);
                    idP.appendChild(document.createTextNode(result.short_id));
                    successDiv.appendChild(idP);
                    
                    resultDiv.innerHTML = '';
                    resultDiv.appendChild(successDiv);
                    
                    // Update preview securely
                    const previewContent = document.getElementById('previewContent');
                    previewContent.innerHTML = '';
                    
                    const destP = document.createElement('p');
                    const destLabel = document.createElement('strong');
                    destLabel.textContent = 'Destino: ';
                    destP.appendChild(destLabel);
                    destP.appendChild(document.createTextNode(result.original_url));
                    
                    const redirectP = document.createElement('p');
                    const redirectLabel = document.createElement('strong');
                    redirectLabel.textContent = 'Redirecionamento: ';
                    redirectP.appendChild(redirectLabel);
                    redirectP.appendChild(document.createTextNode('HTTP 302'));
                    
                    const maskP = document.createElement('p');
                    const maskLabel = document.createElement('strong');
                    maskLabel.textContent = 'Mascaramento: ';
                    maskP.appendChild(maskLabel);
                    maskP.appendChild(document.createTextNode(result.masked ? 'Ativo' : 'Desativo'));
                    
                    previewContent.appendChild(destP);
                    previewContent.appendChild(redirectP);
                    previewContent.appendChild(maskP);
                } else {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error';
                    errorDiv.textContent = 'Erro: ' + result.error;
                    resultDiv.innerHTML = '';
                    resultDiv.appendChild(errorDiv);
                }
            } catch (error) {
                const resultDiv = document.getElementById('result');
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error';
                errorDiv.textContent = 'Erro de conexão: ' + error.message;
                resultDiv.innerHTML = '';
                resultDiv.appendChild(errorDiv);
            }
        };
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(function() {
                alert('Link copiado para a área de transferência!');
            });
        }
        
        // Preview on URL input - secure implementation
        document.getElementById('originalUrl').oninput = function() {
            const url = this.value;
            if (url && url.startsWith('http')) {
                const previewContent = document.getElementById('previewContent');
                previewContent.innerHTML = '';
                
                const urlP = document.createElement('p');
                const urlLabel = document.createElement('strong');
                urlLabel.textContent = 'URL Original: ';
                urlP.appendChild(urlLabel);
                urlP.appendChild(document.createTextNode(url));
                
                const instructionP = document.createElement('p');
                const instructionEm = document.createElement('em');
                instructionEm.textContent = 'Clique em "Clonar Link" para gerar o link clonado';
                instructionP.appendChild(instructionEm);
                
                previewContent.appendChild(urlP);
                previewContent.appendChild(instructionP);
            }
        };
        
        // Toggle custom domain input field
        document.getElementById('useAltDomain').onchange = function() {
            const customDomainGroup = document.getElementById('customDomainGroup');
            if (this.checked) {
                customDomainGroup.style.display = 'block';
            } else {
                customDomainGroup.style.display = 'none';
                document.getElementById('customDomain').value = '';
            }
        };
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HOME_HTML)

@app.route('/api/shorten', methods=['POST'])
def shorten():
    data = request.get_json(force=True)
    if not data or 'url' not in data:
        return jsonify({'error':'missing url'}), 400
    url = data['url'].strip()
    parsed = urlparse(url)
    if parsed.scheme not in ('http','https'):
        return jsonify({'error':'url must start with http:// or https://'}), 400
    # generate unique id
    short_id = generate_short_id(8)
    # ensure uniqueness
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
        return jsonify({'error':'missing url'}), 400
    
    original_url = data['url'].strip()
    parsed = urlparse(original_url)
    if parsed.scheme not in ('http','https'):
        return jsonify({'error':'url must start with http:// or https://'}), 400
    
    # Extract options
    custom_domain = data.get('customDomain', '').strip()
    options = {
        'use_alt_domain': data.get('useAltDomain', False),
        'custom_domain': custom_domain if custom_domain else None,
        'add_utm': data.get('addUtm', False),
        'tracking_id': data.get('trackingId', '').strip() or None,
        'apply_mask': data.get('applyMask', True)
    }
    
    # Process URL with advanced options
    processed_url = process_url_with_options(original_url, options)
    
    # Generate unique ID
    short_id = generate_short_id(8)
    tries = 0
    while get_target(short_id) and tries < 5:
        short_id = generate_short_id(8)
        tries += 1
    
    if tries >= 5:
        return jsonify({'error':'failed to generate unique id'}), 500
    
    # Save link with options
    save_link(
        short_id, 
        processed_url,
        tracking_id=options['tracking_id'],
        use_alt_domain=options['use_alt_domain'],
        add_utm=options['add_utm'],
        apply_mask=options['apply_mask']
    )
    
    # Generate cloned URL with custom or alternative domain if requested
    custom_domain_used = False
    alt_domain_used = False
    
    if options['use_alt_domain']:
        if options['custom_domain']:
            # Use user-specified custom domain
            custom_domain = options['custom_domain']
            if not custom_domain.startswith(('http://', 'https://')):
                custom_domain = 'https://' + custom_domain
            cloned_url = custom_domain.rstrip('/') + '/' + short_id
            custom_domain_used = True
        elif ALT_DOMAIN_ENABLED and ALT_DOMAIN:
            # Use configured alternative domain
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
    """Final redirect route for masked links"""
    target = get_target(short_id)
    if not target:
        return "Link não encontrado", 404
    return redirect(target, code=302)

@app.route('/health')
def health():
    return jsonify({'status':'healthy','service':'link-cloner-fixed'}), 200

@app.route('/api/config')
def get_config():
    """Get current configuration status"""
    return jsonify({
        'alt_domain_enabled': ALT_DOMAIN_ENABLED,
        'alt_domain': ALT_DOMAIN if ALT_DOMAIN_ENABLED else None,
        'service': 'link-cloner-fixed',
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
    
    # If masking is disabled, do direct redirect
    if not apply_mask:
        return redirect(target, code=302)
    
    # If masking is enabled, show masking page
    return render_template_string(MASK_PAGE_HTML, target_url=target, short_id=short_id)

    if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


