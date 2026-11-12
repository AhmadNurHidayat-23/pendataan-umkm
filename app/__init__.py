from pathlib import Path
import os
import sqlite3
from flask import Flask, g, request, jsonify, render_template
from werkzeug.exceptions import HTTPException
from core.db import initialize, connect
from core.security import Problem, get_session
from core.auth import auth
from .routes import api

def create_app(config=None):
    app = Flask(__name__)
    app.config.update(INSTANCE_DIR=os.getenv('APP_INSTANCE', './instance'), MAX_CONTENT_LENGTH=65536)
    if config:
        app.config.update(config)
    initialize(app.config['INSTANCE_DIR'], (Path(__file__).parent / 'schema.sql').read_text())
    app.json.ensure_ascii = False

    @app.before_request
    def prepare():
        g.db = connect(app.config['INSTANCE_DIR'])
        g.session = get_session(g.db, request.cookies.get('pendataan_umkm_session'))
        g.user = {k: g.session[k] for k in ('id', 'username', 'name', 'role')} if g.session else None
        if request.method in ('POST', 'PUT', 'DELETE'):
            if request.headers.get('Origin') and request.headers['Origin'] != request.host_url.rstrip('/'):
                raise Problem('Asal permintaan tidak diizinkan.', 403)
            if not request.is_json and not (app.config.get('ALLOW_MULTIPART') and request.mimetype == 'multipart/form-data'):
                raise Problem('Format permintaan tidak valid.', 415)

    @app.teardown_request
    def close(_error=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.errorhandler(Problem)
    def problem(error):
        return jsonify(error=str(error)), error.status

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity(_error):
        return jsonify(error='Data sudah digunakan atau masih memiliki relasi yang harus dipertahankan.'), 409

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error='Permintaan terlalu besar.' if error.code == 413 else 'Alamat atau format permintaan tidak valid.'), error.code

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'"
        return response
    app.register_blueprint(auth)
    app.register_blueprint(api)
    return app
