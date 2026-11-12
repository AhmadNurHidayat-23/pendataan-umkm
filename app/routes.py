import csv
import io
from flask import Blueprint, g, request, jsonify, Response
from core.auth import require, data
from core.validate import choice
from . import models, service
api = Blueprint('api', __name__)

@api.get('/api/state')
@require()
def state():
    return jsonify(models.state(g.db, request.args))

@api.route('/api/<kind>', methods=['POST'])
@api.route('/api/<kind>/<int:id>', methods=['PUT', 'DELETE'])
@require()
def save(kind, id=None):
    if kind in ('categories', 'regions', 'programs') and g.user['role'] != 'Admin':
        from core.security import Problem
        raise Problem('Data induk dan program hanya dikelola Admin.', 403)
    if kind not in models.TABLES or kind == 'enrollments':
        from core.security import Problem
        raise Problem('Alamat tidak tersedia.', 404)
    if request.method == 'DELETE':
        service.remove(g.db, kind, id)
    elif kind == 'businesses':
        service.save_business(g.db, data(), id)
    elif kind == 'programs':
        service.save_program(g.db, data(), id)
    else:
        service.save_master(g.db, kind, data(), id)
    return jsonify(message='Perubahan disimpan.')

@api.post('/api/businesses/<int:id>/restore')
@require(('Admin',))
def restore(id):
    models.find(g.db, 'businesses', id)
    with g.db:
        g.db.execute('UPDATE businesses SET archived=0 WHERE id=?', (id,))
    return jsonify(message='Usaha dipulihkan. Ubah status menjadi Aktif bila diperlukan.')

@api.route('/api/programs/<int:id>/participants', methods=['GET', 'POST'])
@require()
def participants(id):
    if request.method == 'GET':
        return jsonify(models.program_participants(g.db, id))
    service.enroll(g.db, id, data())
    return jsonify(message='Peserta ditambahkan.'), 201

@api.route('/api/enrollments/<int:id>', methods=['PUT', 'DELETE'])
@require()
def enrollment(id):
    models.find(g.db, 'enrollments', id)
    if request.method == 'DELETE':
        service.remove(g.db, 'enrollments', id)
    else:
        status = choice(data().get('status'), ('Terdaftar', 'Hadir'), 'Status peserta')
        with g.db:
            g.db.execute('UPDATE enrollments SET status=? WHERE id=?', (status, id))
    return jsonify(message='Data peserta diperbarui.')

@api.get('/api/export')
@require()
def export():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Kode', 'Usaha', 'Pelaku usaha demonstrasi', 'Kategori', 'Wilayah', 'Alamat', 'Skala', 'Status', 'Program diikuti'])
    for b in models.businesses(g.db, request.args):
        values = [b['code'], b['name'], b['owner'], b['category'], b['region'], b['address'], b['scale'], b['status'], b['training_count']]
        writer.writerow(["'" + str(v) if str(v).startswith(('=', '+', '-', '@')) else v for v in values])
    return Response('\ufeff' + output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=laporan-umkm.csv'})
