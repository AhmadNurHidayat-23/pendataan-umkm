from functools import wraps
import os
import secrets
import re
from flask import Blueprint, request, g, jsonify
from .security import Problem, authenticate, new_session
auth = Blueprint('auth', __name__)

def data():
    value = request.get_json()
    if not isinstance(value, dict):
        raise Problem('Format data tidak valid.')
    return value

def require(roles=('Admin', 'Petugas')):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not g.user:
                raise Problem('Silakan masuk terlebih dahulu.', 401)
            if g.user['role'] not in roles:
                raise Problem('Tindakan ini hanya untuk Admin.', 403)
            if request.method != 'GET':
                token = request.headers.get('X-CSRF-Token', '')
                if not re.fullmatch(r'[a-f0-9]{64}', token) or not secrets.compare_digest(g.session['csrf'], token):
                    raise Problem('Sesi formulir tidak valid. Muat ulang halaman.', 403)
            return fn(*args, **kwargs)
        return wrapped
    return decorate

@auth.get('/api/session')
def session():
    return jsonify(user=g.user, csrf=g.session['csrf'] if g.session else None,
                   configured=g.db.execute('SELECT id FROM users LIMIT 1').fetchone() is not None)

@auth.post('/api/login')
def login():
    values = data()
    user_id, key = authenticate(g.db, values.get('username', ''), values.get('password', ''))
    token, csrf = new_session(g.db, user_id, g.session, key)
    user = dict(g.db.execute('SELECT id,username,name,role FROM users WHERE id=?', (user_id,)).fetchone())
    response = jsonify(user=user, csrf=csrf)
    response.set_cookie('app_session', token, max_age=28800, httponly=True, samesite='Strict', secure=os.getenv('SECURE_COOKIE') == '1')
    return response

@auth.post('/api/logout')
@require()
def logout():
    with g.db:
        g.db.execute('DELETE FROM sessions WHERE token=?', (g.session['token'],))
    response = jsonify(message='Anda telah keluar.')
    response.delete_cookie('app_session', path='/')
    return response
