from datetime import timedelta
import hashlib
import hmac
import json
import uuid
import os
import time

from flask import Flask, request, render_template, redirect, url_for, flash, session, make_response
from werkzeug.http import parse_options_header

secret_key = os.getenv('SECRET_KEY')
band_token_secret = os.urandom(32)

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

broadcasts_by_session = {}
broadcasts_by_id = {}
report_cooldowns = {}
REPORT_COOLDOWN_SECONDS = 30
BAND_GUIDES = {
    'v1': {
        'name': 'Core Band',
        'channels': ['ops', 'cargo', 'nav']
    }
}

@app.after_request
def add_security_headers(response):
    csp = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.before_request
def persist_session_cookie():
    session.permanent = True

def get_session_id():
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    broadcasts_by_session.setdefault(session_id, [])
    return session_id

def current_broadcasts():
    return broadcasts_by_session[get_session_id()]

@app.context_processor
def inject_sidebar_broadcasts():
    return {'sidebar_broadcasts': current_broadcasts()}

def find_user_broadcast(broadcast_id):
    return next((broadcast for broadcast in current_broadcasts() if broadcast['id'] == broadcast_id), None)

def validate_band(raw_band):
    band = (raw_band or 'text/plain').strip()
    parsed_type = parse_options_header(band)[0]

    if parsed_type != 'text/plain':
        return None, "Only text/plain bands are allowed"
    if any(ch in band for ch in '\r\n'):
        return None, "Invalid band"

    return band, None

def make_band_key(name):
    return hmac.new(band_token_secret, name.encode(), hashlib.sha256).hexdigest()[:16]

def render_create_page(title='', content=''):
    return render_template(
        'create.html',
        draft_title=title,
        draft_content=content,
    )

def report_cooldown_remaining(broadcast_id):
    last_report = report_cooldowns.get(broadcast_id, 0)
    now = time.time()
    remaining = REPORT_COOLDOWN_SECONDS - (now - last_report)
    return max(0, int(remaining + 0.999))

BAND_SESSION_KEY = 'band_tune_ready'

@app.route('/band/guide/<name>')
def band_guide(name):
    guide = BAND_GUIDES.get(name)
    if not guide:
        response = make_response(json.dumps({
            'success': False,
            'error': 'No band guide found'
        }, separators=(',', ':')))
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, 404

    response = make_response(json.dumps(guide, separators=(',', ':')))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

@app.route('/band/echo/<key>/<pin>/<name>')
def band_echo(key, pin, name):
    to = request.args.get('to', '').strip()
    trail = request.args.get('r', '')
    tune_state = session.get(BAND_SESSION_KEY) or {}

    if key != make_band_key(name):
        return "Not found", 404
    if tune_state.get('name') != name:
        return "Not found", 404
    if tune_state.get('pin') != pin:
        return "Not found", 404
    if time.time() - tune_state.get('ts', 0) > 10:
        session.pop(BAND_SESSION_KEY, None)
        return "Not found", 404
    if not to:
        return "Not found", 404
    if any(ch in to for ch in '\r\n<>'):
        return "Invalid target", 400
    if not trail.endswith('?to=tune'):
        return "Not found", 404

    session.pop(BAND_SESSION_KEY, None)
    result = {
        'success': False,
        'error': 'No band guide found'
    }
    body = f"{to}({json.dumps(result, separators=(',', ':'))});"
    response = make_response(body)
    response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.route('/band/tune.js')
def band_tune():
    band = request.args.get('band', 'v1')
    safe_band = band.split('?', 1)[0]
    band_key = make_band_key(safe_band)
    band_pin = uuid.uuid4().hex[:16]
    session[BAND_SESSION_KEY] = {
        'name': safe_band,
        'pin': band_pin,
        'ts': time.time(),
    }
    body = f"""(function(){{
const band={json.dumps(band)};
const bandKey={json.dumps(band_key)};
const bandPin={json.dumps(band_pin)};
function tune(guide){{window.__starlogBand=guide;}}
const request=new XMLHttpRequest();
try{{
request.open('GET','/band/guide/'+encodeURIComponent(band),false);
request.send(null);
if(request.status!==200){{throw new Error('band unavailable');}}
tune(JSON.parse(request.responseText));
}}catch(err){{
let script=document.createElement('script');
script.src='/band/echo/'+bandKey+'/'+bandPin+'/'+band+'?to=tune';
document.head.appendChild(script);
}}
}})();"""
    response = make_response(body)
    response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.route('/')
def index():
    return render_create_page()

@app.route('/create', methods=['POST'])
def create():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    band = request.form.get('band', 'text/plain').strip()
    
    if not title:
        flash('Title required', 'error')
        return render_create_page(title=title, content=content)

    band, error = validate_band(band)
    if error:
        flash(f'Invalid band: {error}', 'error')
        return render_create_page(title=title, content=content)
    
    broadcast_id = str(uuid.uuid4())
    broadcast = {
        'id': broadcast_id,
        'title': title,
        'content': content,
        'band': band,
    }
    current_broadcasts().append(broadcast)
    broadcasts_by_id[broadcast_id] = broadcast
    return redirect(url_for('view_broadcast', id=broadcast_id))

@app.route('/note/<id>')
def view_broadcast(id):
    broadcast = find_user_broadcast(id)
    if not broadcast:
        flash('Not found', 'error')
        return redirect(url_for('index'))
    return render_template(
        'note.html',
        broadcast=broadcast,
        public_url=url_for('public_broadcast', id=broadcast['id'], _external=True)
    )

@app.route('/view/<id>')
def public_broadcast(id):
    broadcast = broadcasts_by_id.get(id)
    if not broadcast:
        return "Not found", 404

    response = make_response(broadcast.get('content', ''))
    response.headers['Content-Type'] = broadcast.get('band', 'text/plain')
    response.headers['Cache-Control'] = 'no-store'
    return response

def queue_report(broadcast_id):
    import requests as req
    
    if broadcast_id not in broadcasts_by_id:
        return False

    if report_cooldown_remaining(broadcast_id) > 0:
        return False

    now = time.time()

    try:
        bot_host = os.getenv('BOT_HOST', 'bot:3000')
        response = req.post(f'http://{bot_host}/visit', json={'path': f'/view/{broadcast_id}'}, timeout=3)
        if response.ok:
            report_cooldowns[broadcast_id] = now
        return response.ok
    except Exception as e:
        print(f"Bot error: {e}")
        return False

@app.route('/report')
def report_page():
    broadcast_id = request.args.get('id', '').strip()
    broadcast = broadcasts_by_id.get(broadcast_id) if broadcast_id else None
    if not broadcast:
        flash('Broadcast not found.', 'error')
        return redirect(url_for('index'))

    report_result = request.args.get('result', '').strip()
    report_message = request.args.get('message', '').strip()

    return render_template(
        'report.html',
        report_title=broadcast['title'],
        submit_url=url_for('report', id=broadcast_id),
        cancel_url=url_for('view_broadcast', id=broadcast_id) if find_user_broadcast(broadcast_id) else url_for('public_broadcast', id=broadcast_id),
        report_result=report_result,
        report_message=report_message,
    )

@app.route('/report/<id>', methods=['POST'])
def report(id):
    if id not in broadcasts_by_id:
        flash('Broadcast not found.', 'error')
        return redirect(url_for('index'))

    cooldown_remaining = report_cooldown_remaining(id)
    if cooldown_remaining > 0:
        message = f'This broadcast was already sent recently. Please wait {cooldown_remaining} seconds before retrying.'
        return redirect(url_for('report_page', id=id, result='error', message=message))

    if queue_report(id):
        message = 'Reported! The station bot will review this broadcast soon.'
        return redirect(url_for('report_page', id=id, result='success', message=message))
    else:
        message = 'The station bot is unavailable right now.'
        return redirect(url_for('report_page', id=id, result='error', message=message))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
