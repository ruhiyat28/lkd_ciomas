from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from ..models import db, User, Pinjaman, Nasabah, Pembayaran, JurnalUmum

user_bp = Blueprint('user_mgmt', __name__)

def get_next_kader_username(kode_desa):
    prefix = f"{kode_desa.upper()}-"
    existing = User.query.filter(
        User.username.like(f"{prefix}%"),
        User.role == 'kader_desa'
    ).order_by(User.username.desc()).first()
    
    if existing:
        try:
            last_num = int(existing.username.split('-')[1])
            return f"{prefix}{last_num + 1}"
        except (ValueError, IndexError):
            pass
    
    return f"{prefix}899"

@user_bp.route('/api/next-kader-username/<kode_desa>')
@login_required
def next_kader_username(kode_desa):
    if current_user.role != 'admin':
        abort(403)
    return {'username': get_next_kader_username(kode_desa)}

@user_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin':
        abort(403)
    users = User.query.filter(User.role != 'nasabah').order_by(User.username).all()
    return render_template('user/index.html', users=users)

@user_bp.route('/tambah', methods=['GET', 'POST'])
@login_required
def tambah():
    if current_user.role != 'admin':
        abort(403)
    
    pembina_list = User.query.filter(
        User.role.in_(['admin', 'manajer_lkd', 'kredit', 'tata_usaha', 'staf', 'keuangan', 'kasir']),
        User.aktif == True
    ).order_by(User.nama_lengkap).all()
    
    if request.method == 'POST':
        role = request.form.get('role', 'kredit')
        username = request.form.get('username', '').strip()
        
        if role == 'kader_desa':
            kode_desa = request.form.get('kode_desa', '').strip()
            if not username:
                username = get_next_kader_username(kode_desa)
        
        if User.query.filter_by(username=username).first():
            flash('Username sudah digunakan.', 'danger')
        else:
            u = User(
                username=username,
                nama_lengkap=request.form.get('nama_lengkap', ''),
                role=role,
                kode_desa=request.form.get('kode_desa', None) if role == 'kader_desa' else None,
                pembina_id=request.form.get('pembina_id', None) if role == 'kader_desa' else None,
            )
            u.set_password(request.form.get('password', ''))
            db.session.add(u)
            db.session.commit()
            flash(f'User {username} berhasil dibuat.', 'success')
            return redirect(url_for('user_mgmt.index'))
    
    return render_template('user/form.html', user=None, pembina_list=pembina_list)

@user_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    if current_user.role != 'admin':
        abort(403)
    u = User.query.get_or_404(id)
    
    pembina_list = User.query.filter(
        User.role.in_(['admin', 'manajer_lkd', 'kredit', 'tata_usaha', 'staf', 'keuangan', 'kasir']),
        User.aktif == True
    ).order_by(User.nama_lengkap).all()
    
    if request.method == 'POST':
        u.nama_lengkap = request.form.get('nama_lengkap', '')
        u.role = request.form.get('role', 'kredit')
        if u.role == 'kader_desa':
            u.kode_desa = request.form.get('kode_desa', None)
            u.pembina_id = request.form.get('pembina_id', None)
        else:
            u.kode_desa = None
            u.pembina_id = None
        u.aktif = 'aktif' in request.form
        pw = request.form.get('password', '')
        if pw:
            u.set_password(pw)
        db.session.commit()
        flash('User diperbarui.', 'success')
        return redirect(url_for('user_mgmt.index'))
    
    return render_template('user/form.html', user=u, pembina_list=pembina_list)

@user_bp.route('/hapus/<int:id>', methods=['POST'])
@login_required
def hapus(id):
    if current_user.role != 'admin':
        abort(403)
    u = User.query.get_or_404(id)
    if u.id == current_user.id:
        flash('Tidak bisa menghapus akun sendiri.', 'danger')
    else:
        from ..models import Pinjaman, Nasabah, Pembayaran, JurnalUmum
        Pinjaman.query.filter_by(created_by=u.id).update({'created_by': None})
        Pinjaman.query.filter_by(verified_by=u.id).update({'verified_by': None})
        Pinjaman.query.filter_by(acc_by=u.id).update({'acc_by': None})
        Nasabah.query.filter_by(created_by=u.id).update({'created_by': None})
        Pembayaran.query.filter_by(created_by=u.id).update({'created_by': None})
        JurnalUmum.query.filter_by(created_by=u.id).update({'created_by': None})
        db.session.commit()
        db.session.delete(u)
        db.session.commit()
        flash(f'User {u.username} ({u.nama_lengkap}) beserta referensi datanya berhasil dihapus.', 'success')
    return redirect(url_for('user_mgmt.index'))
