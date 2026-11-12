import csv
import io
import secrets
import pytest
from app import create_app
from core.db import connect
from core.security import add_user, digest

@pytest.fixture
def env(tmp_path):
    app = create_app({'TESTING': True, 'INSTANCE_DIR': str(tmp_path)})
    password = secrets.token_urlsafe(20)
    db = connect(tmp_path)
    add_user(db, 'admin', 'Admin Uji', 'Admin', password)
    add_user(db, 'petugas', 'Petugas Uji', 'Petugas', password)
    db.close()
    clients = {}
    for username in ('admin', 'petugas'):
        c = app.test_client()
        response = c.post('/api/login', json={'username': username, 'password': password})
        assert response.status_code == 200
        clients[username] = (c, {'X-CSRF-Token': response.json['csrf']})
    c, headers = clients['admin']
    c.post('/api/categories', json={'name': 'Kuliner'}, headers=headers)
    c.post('/api/regions', json={'name': 'Wilayah Uji'}, headers=headers)
    return app, clients, tmp_path

def business(**extra):
    return {'code': 'UJI-01', 'name': 'Usaha Contoh', 'owner': 'Pelaku Contoh', 'category_id': 1, 'region_id': 1,
            'address': 'Alamat demonstrasi', 'scale': 'Mikro', 'status': 'Aktif', **extra}

def program(**extra):
    return {'name': 'Pembinaan Contoh', 'description': 'Program pengujian', 'date': '2026-11-12', 'location': 'Lokasi Contoh', **extra}

def test_business_crud_and_archive_restore(env):
    _, clients, _ = env
    c, h = clients['petugas']
    assert c.post('/api/businesses', json=business(), headers=h).status_code == 200
    assert c.put('/api/businesses/1', json=business(name='Usaha Diubah', status='Tidak Aktif'), headers=h).status_code == 200
    assert c.get('/api/state').json['businesses'][0]['name'] == 'Usaha Diubah'
    assert c.delete('/api/businesses/1', json={}, headers=h).status_code == 200
    assert c.get('/api/state').json['businesses'] == []
    assert len(c.get('/api/state?archived=1').json['businesses']) == 1
    assert c.post('/api/businesses/1/restore', json={}, headers=h).status_code == 403
    admin, ah = clients['admin']
    assert admin.post('/api/businesses/1/restore', json={}, headers=ah).status_code == 200
    assert admin.get('/api/state').json['businesses'][0]['status'] == 'Tidak Aktif'

def test_master_program_crud_and_relations(env):
    _, clients, _ = env
    c, h = clients['admin']
    for kind in ('categories', 'regions'):
        assert c.post('/api/' + kind, json={'name': 'Tambahan'}, headers=h).status_code == 200
        assert c.put('/api/' + kind + '/2', json={'name': 'Diubah'}, headers=h).status_code == 200
        assert c.delete('/api/' + kind + '/2', json={}, headers=h).status_code == 200
    assert c.post('/api/programs', json=program(), headers=h).status_code == 200
    assert c.put('/api/programs/1', json=program(name='Program Diubah'), headers=h).status_code == 200
    assert c.delete('/api/programs/1', json={}, headers=h).status_code == 200
    c.post('/api/businesses', json=business(), headers=h)
    assert c.delete('/api/categories/1', json={}, headers=h).status_code == 409
    assert c.delete('/api/regions/1', json={}, headers=h).status_code == 409

def test_participation_duplicate_attendance_and_history_preserved(env):
    _, clients, _ = env
    admin, ah = clients['admin']
    staff, sh = clients['petugas']
    admin.post('/api/businesses', json=business(), headers=ah)
    admin.post('/api/programs', json=program(), headers=ah)
    assert staff.post('/api/programs/1/participants', json={'business_id': 1}, headers=sh).status_code == 201
    assert staff.post('/api/programs/1/participants', json={'business_id': 1}, headers=sh).status_code == 409
    assert staff.put('/api/enrollments/1', json={'status': 'Hadir'}, headers=sh).status_code == 200
    assert staff.get('/api/programs/1/participants').json[0]['status'] == 'Hadir'
    assert admin.delete('/api/programs/1', json={}, headers=ah).status_code == 409
    staff.delete('/api/businesses/1', json={}, headers=sh)
    assert len(staff.get('/api/programs/1/participants').json) == 1
    assert staff.delete('/api/enrollments/1', json={}, headers=sh).status_code == 200
    assert staff.get('/api/programs/1/participants').json == []

def test_validation_unique_codes_and_invalid_refs(env):
    _, clients, _ = env
    c, h = clients['admin']
    for values in ({'name': ''}, {'scale': 'Besar'}, {'status': 'Tidak valid'}, {'category_id': 99}, {'region_id': True}):
        assert c.post('/api/businesses', json=business(**values), headers=h).status_code in (400, 404)
    c.post('/api/businesses', json=business(), headers=h)
    assert c.post('/api/businesses', json=business(code='uji-01'), headers=h).status_code == 409
    assert c.post('/api/programs', json=program(date='2026-02-30'), headers=h).status_code == 400
    assert c.post('/api/programs/999/participants', json={'business_id': 1}, headers=h).status_code == 404

def test_search_filters_statistics_and_csv(env):
    _, clients, _ = env
    c, h = clients['petugas']
    c.post('/api/businesses', json=business(), headers=h)
    c.post('/api/businesses', json=business(code='UJI-02', name='Usaha Kedua', status='Tidak Aktif', scale='Kecil'), headers=h)
    response = c.get('/api/state?q=contoh&category_id=1&region_id=1&scale=Mikro&status=Aktif')
    assert len(response.json['businesses']) == 1 and response.json['summary']['active'] == 1
    assert response.json['groups'] == [{'name': 'Kuliner', 'count': 1}]
    assert c.get('/api/state?scale=Menengah').json['businesses'] == []
    csv_response = c.get('/api/export?status=Aktif')
    rows = list(csv.reader(io.StringIO(csv_response.data.decode('utf-8-sig'))))
    assert rows[0][0] == 'Kode' and len(rows) == 2 and rows[1][1] == 'Usaha Contoh'

def test_roles_csrf_origin_and_logout(env):
    app, clients, folder = env
    anonymous = app.test_client()
    assert anonymous.get('/api/state').status_code == 401
    staff, h = clients['petugas']
    assert staff.post('/api/programs', json=program(), headers=h).status_code == 403
    assert staff.post('/api/regions', json={'name': 'Tidak boleh'}, headers=h).status_code == 403
    assert staff.post('/api/businesses', json=business()).status_code == 403
    assert staff.post('/api/businesses', json=business(), headers={'X-CSRF-Token': 'é'}).status_code == 403
    assert staff.post('/api/businesses', json=business(), headers={**h, 'Origin': 'https://lain.example'}).status_code == 403
    token = staff.get_cookie('app_session').value
    db = connect(folder)
    assert db.execute('SELECT token FROM sessions WHERE token=?', (token,)).fetchone() is None
    assert db.execute('SELECT token FROM sessions WHERE token=?', (digest(token),)).fetchone() is not None
    db.close()
    assert staff.post('/api/logout', json={}, headers=h).status_code == 200
    assert staff.get('/api/state').status_code == 401

def test_persistence_reinitialization_and_database_integrity(env):
    _, clients, folder = env
    c, h = clients['admin']
    c.post('/api/businesses', json=business(), headers=h)
    restarted = create_app({'TESTING': True, 'INSTANCE_DIR': str(folder)})
    other = restarted.test_client()
    other.set_cookie('app_session', c.get_cookie('app_session').value)
    assert other.get('/api/state').json['businesses'][0]['code'] == 'UJI-01'
    db = connect(folder)
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    db.close()
