from core.validate import require_row
TABLES = ('regions', 'categories', 'businesses', 'programs', 'enrollments')

def find(db, kind, id):
    return require_row(db, kind, id, TABLES)

def businesses(db, filters):
    clauses, args = ['b.archived=?'], [1 if filters.get('archived') == '1' else 0]
    q = str(filters.get('q', '')).strip()[:120]
    if q:
        clauses.append('(instr(lower(b.name),lower(?))>0 OR instr(lower(b.owner),lower(?))>0 OR instr(lower(b.code),lower(?))>0)')
        args.extend([q, q, q])
    for key in ('category_id', 'region_id', 'scale', 'status'):
        if filters.get(key):
            clauses.append(f'b.{key}=?')
            args.append(filters[key])
    return [dict(r) for r in db.execute('''SELECT b.*,c.name category,r.name region,
        (SELECT count(*) FROM enrollments e WHERE e.business_id=b.id) training_count FROM businesses b
        JOIN categories c ON c.id=b.category_id JOIN regions r ON r.id=b.region_id WHERE '''
        + ' AND '.join(clauses) + ' ORDER BY b.name', args)]

def program_participants(db, id):
    find(db, 'programs', id)
    return [dict(r) for r in db.execute('''SELECT e.*,b.name business,b.code,b.owner FROM enrollments e
        JOIN businesses b ON b.id=e.business_id WHERE program_id=? ORDER BY b.name''', (id,))]

def state(db, filters):
    rows = businesses(db, filters)
    programs = [dict(r) for r in db.execute('''SELECT p.*,(SELECT count(*) FROM enrollments e WHERE e.program_id=p.id) participants
        FROM programs p ORDER BY p.date DESC,p.id DESC''')]
    return {'businesses': rows, 'programs': programs,
            'categories': [dict(r) for r in db.execute('SELECT * FROM categories ORDER BY name')],
            'regions': [dict(r) for r in db.execute('SELECT * FROM regions ORDER BY name')],
            'allBusinesses': [dict(r) for r in db.execute('SELECT id,name,code FROM businesses WHERE archived=0 ORDER BY name')],
            'summary': {'total': len(rows), 'active': sum(b['status'] == 'Aktif' for b in rows),
                        'inactive': sum(b['status'] == 'Tidak Aktif' for b in rows), 'training': sum(b['training_count'] for b in rows)},
            'groups': [{'name': name, 'count': sum(b['category'] == name for b in rows)} for name in sorted({b['category'] for b in rows})]}
