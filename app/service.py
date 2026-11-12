from core.security import Problem
from core.validate import text, integer, choice, date
from core.db import transaction
from .models import find

def save_master(db, kind, data, id=None):
    if kind not in ('categories', 'regions'):
        raise Problem('Jenis data tidak valid.')
    name = text(data.get('name'), 'Nama kategori / wilayah', 80)
    if id:
        find(db, kind, id)
    with db:
        if id:
            db.execute(f'UPDATE {kind} SET name=? WHERE id=?', (name, id))
        else:
            db.execute(f'INSERT INTO {kind}(name) VALUES(?)', (name,))

def save_business(db, data, id=None):
    if id and find(db, 'businesses', id)['archived']:
        raise Problem('Pulihkan usaha dari arsip terlebih dahulu.')
    category = integer(data.get('category_id'), 'Kategori', 1)
    region = integer(data.get('region_id'), 'Wilayah', 1)
    find(db, 'categories', category)
    find(db, 'regions', region)
    values = (text(data.get('code'), 'Kode usaha', 40).upper(), text(data.get('name'), 'Nama usaha'),
              text(data.get('owner'), 'Nama pelaku usaha demonstrasi', 100), category, region,
              text(data.get('address'), 'Alamat wilayah usaha', 200), choice(data.get('scale'), ('Mikro', 'Kecil', 'Menengah'), 'Skala usaha'),
              choice(data.get('status'), ('Aktif', 'Tidak Aktif'), 'Status usaha'))
    with db:
        if id:
            db.execute('UPDATE businesses SET code=?,name=?,owner=?,category_id=?,region_id=?,address=?,scale=?,status=? WHERE id=?', (*values, id))
        else:
            db.execute('INSERT INTO businesses(code,name,owner,category_id,region_id,address,scale,status) VALUES(?,?,?,?,?,?,?,?)', values)

def save_program(db, data, id=None):
    if id:
        find(db, 'programs', id)
    values = (text(data.get('name'), 'Nama program'), text(data.get('description'), 'Uraian pembinaan', 1500),
              date(data.get('date')), text(data.get('location'), 'Lokasi pembinaan', 160))
    with db:
        if id:
            db.execute('UPDATE programs SET name=?,description=?,date=?,location=? WHERE id=?', (*values, id))
        else:
            db.execute('INSERT INTO programs(name,description,date,location) VALUES(?,?,?,?)', values)

def enroll(db, program_id, data):
    business = integer(data.get('business_id'), 'Usaha peserta', 1)
    with transaction(db):
        find(db, 'programs', program_id)
        if find(db, 'businesses', business)['archived']:
            raise Problem('Usaha dalam arsip tidak dapat didaftarkan.')
        if db.execute('SELECT id FROM enrollments WHERE business_id=? AND program_id=?', (business, program_id)).fetchone():
            raise Problem('Usaha ini sudah terdaftar pada program tersebut.', 409)
        db.execute('INSERT INTO enrollments(program_id,business_id) VALUES(?,?)', (program_id, business))

def remove(db, kind, id):
    find(db, kind, id)
    with db:
        if kind == 'businesses':
            db.execute("UPDATE businesses SET archived=1,status='Tidak Aktif' WHERE id=?", (id,))
        else:
            db.execute(f'DELETE FROM {kind} WHERE id=?', (id,))
