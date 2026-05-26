from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user
from ..models import Pinjaman, Nasabah, Pembayaran, Pengaturan, AkunCOA, RekeningTabungan, TransaksiTabungan
from config import Config
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from .. import db
import json

laporan_bp = Blueprint('laporan', __name__)

# ── Helper: rekap per desa ────────────────────────────────────
def _rekap_per_desa(pinjaman_list):
    """Group pinjaman aktif by desa, return list of dicts."""
    desa_map = {k: {'kode': k, 'nama': n, 'pinjaman': []} for k, n in Config.DESA_LIST}
    for p in pinjaman_list:
        kode = p.nasabah.kode_desa
        if kode in desa_map:
            desa_map[kode]['pinjaman'].append(p)

    rows = []
    for kode, d in desa_map.items():
        if not d['pinjaman']:
            continue
        pl = d['pinjaman']
        total_alokasi   = sum(p.jumlah_pinjaman for p in pl)
        total_pokok_tgt = sum(p.get_target_angsuran()[0] for p in pl)
        total_realisasi = sum(p.get_realisasi_pembayaran()[0] for p in pl)
        total_saldo     = sum(p.get_saldo_pokok() for p in pl)
        total_tunggak   = sum(p.get_tunggakan()[0] + p.get_tunggakan()[1] for p in pl)
        tk_persen = (total_realisasi / total_pokok_tgt * 100) if total_pokok_tgt > 0 else 100

        rows.append({
            'kode'      : kode,
            'nama'      : d['nama'],
            'jml'       : len(pl),
            'alokasi'   : total_alokasi,
            'target'    : total_pokok_tgt,
            'realisasi' : total_realisasi,
            'saldo'     : total_saldo,
            'tunggak'   : total_tunggak,
            'tk_persen' : tk_persen,
        })
    rows.sort(key=lambda x: x['kode'])
    return rows


# ── PERKEMBANGAN — rekap per desa ────────────────────────────
@laporan_bp.route('/perkembangan')
@login_required
def perkembangan():
    desa_filter = request.args.get('desa', '')
    if current_user.is_kader():
        desa_filter = current_user.kode_desa

    cetak       = request.args.get('cetak')

    q = Pinjaman.query.join(Nasabah).filter(Pinjaman.status.in_(['cair','lunas']))
    if desa_filter:
        q = q.filter(Nasabah.kode_desa == desa_filter)
    elif current_user.is_kader():
        # Fallback safety
        q = q.filter(Nasabah.kode_desa == current_user.kode_desa)
    
    pinjaman_list = q.all()

    if desa_filter:
        # Mode detail: tampilkan per nasabah
        rows = []
        for p in pinjaman_list:
            tp, tj     = p.get_realisasi_pembayaran()
            tgt_p, _   = p.get_target_angsuran()
            saldo      = p.get_saldo_pokok()
            pct_target = (tp / tgt_p * 100) if tgt_p > 0 else 100
            pct_lunas  = (tp / p.jumlah_pinjaman * 100) if p.jumlah_pinjaman > 0 else 0
            rows.append({'p': p, 'total_pokok': tp, 'target_pokok': tgt_p,
                          'saldo': saldo, 'persen_target': pct_target, 'persen': pct_lunas})

        total_alokasi   = sum(r['p'].jumlah_pinjaman for r in rows)
        total_terbayar  = sum(r['total_pokok'] for r in rows)
        total_saldo     = sum(r['saldo'] for r in rows)

        tmpl = 'print/laporan_perkembangan.html' if cetak else 'laporan/perkembangan_detail.html'
        return render_template(tmpl, rows=rows,
            total_pinjaman=total_alokasi, total_terbayar=total_terbayar, total_saldo=total_saldo,
            desa_filter=desa_filter, desa_list=Config.DESA_LIST, tanggal_cetak=date.today(),
            nama_desa=dict(Config.DESA_LIST).get(desa_filter, desa_filter))
    else:
        # Mode rekap per desa
        rekap = _rekap_per_desa(pinjaman_list)
        total_jml      = sum(r['jml']       for r in rekap)
        total_alokasi  = sum(r['alokasi']   for r in rekap)
        total_target   = sum(r['target']    for r in rekap)
        total_realisasi= sum(r['realisasi'] for r in rekap)
        total_saldo    = sum(r['saldo']     for r in rekap)
        total_tunggak  = sum(r['tunggak']   for r in rekap)

        tmpl = 'print/laporan_perkembangan_rekap.html' if cetak else 'laporan/perkembangan.html'
        return render_template(tmpl, rekap=rekap,
            total_jml=total_jml, total_alokasi=total_alokasi,
            total_target=total_target, total_realisasi=total_realisasi,
            total_saldo=total_saldo, total_tunggak=total_tunggak,
            desa_list=Config.DESA_LIST, tanggal_cetak=date.today())


# ── KOLEKTIBILITAS — rekap per desa ──────────────────────────
@laporan_bp.route('/kolektibilitas')
@login_required
def kolektibilitas():
    desa_filter = request.args.get('desa', '')
    if current_user.is_kader():
        desa_filter = current_user.kode_desa

    cetak       = request.args.get('cetak')

    q = Pinjaman.query.join(Nasabah).filter(Pinjaman.status == 'cair')
    if desa_filter:
        q = q.filter(Nasabah.kode_desa == desa_filter)
    elif current_user.is_kader():
        q = q.filter(Nasabah.kode_desa == current_user.kode_desa)

    pinjaman_list = q.all()

    KOLEK_CADANGAN = Config.KOLEK_CADANGAN
    KOLEK_LABELS   = {1:'Lancar',2:'Kurang Lancar',3:'Diragukan',4:'Macet Ringan',5:'Macet'}

    # Summary kolek keseluruhan (untuk kartu compact)
    summary_total = {k: {'count':0,'saldo':0,'cadangan':0} for k in range(1,6)}

    if desa_filter:
        # Detail per nasabah
        rows = []
        for p in pinjaman_list:
            kolek, kolek_lbl = p.get_kolektibilitas()
            saldo   = p.get_saldo_pokok()
            cadangan= saldo * KOLEK_CADANGAN[kolek]
            _, _, bn = p.get_tunggakan()
            rows.append({'p': p, 'kolek': kolek, 'kolek_label': kolek_lbl,
                          'saldo': saldo, 'bulan_nunggak': bn, 'cadangan': cadangan})
            summary_total[kolek]['count']   += 1
            summary_total[kolek]['saldo']   += saldo
            summary_total[kolek]['cadangan']+= cadangan
        rows.sort(key=lambda x: (x['kolek'], x['p'].nasabah.nama))
        total_saldo    = sum(r['saldo']    for r in rows)
        total_cadangan = sum(r['cadangan'] for r in rows)

        tmpl = 'print/laporan_kolektibilitas.html' if cetak else 'laporan/kolektibilitas_detail.html'
        return render_template(tmpl, rows=rows, summary=summary_total,
            KOLEK_LABELS=KOLEK_LABELS, KOLEK_CADANGAN=KOLEK_CADANGAN,
            total_saldo=total_saldo, total_cadangan=total_cadangan,
            desa_filter=desa_filter, desa_list=Config.DESA_LIST,
            tanggal_cetak=date.today(),
            nama_desa=dict(Config.DESA_LIST).get(desa_filter, desa_filter))
    else:
        # Rekap per desa
        desa_map = {k: {'kode':k,'nama':n,'jml':0,'saldo':0,
                         **{f'k{i}':0 for i in range(1,6)},
                         'cadangan':0} for k,n in Config.DESA_LIST}

        for p in pinjaman_list:
            kode = p.nasabah.kode_desa
            if kode not in desa_map: continue
            kolek, _ = p.get_kolektibilitas()
            saldo     = p.get_saldo_pokok()
            cadangan  = saldo * KOLEK_CADANGAN[kolek]
            desa_map[kode]['jml']            += 1
            desa_map[kode]['saldo']          += saldo
            desa_map[kode][f'k{kolek}']      += saldo
            desa_map[kode]['cadangan']        += cadangan
            summary_total[kolek]['count']    += 1
            summary_total[kolek]['saldo']    += saldo
            summary_total[kolek]['cadangan'] += cadangan

        rekap = [d for d in desa_map.values() if d['jml'] > 0]
        rekap.sort(key=lambda x: x['kode'])
        total_saldo    = sum(r['saldo']    for r in rekap)
        total_cadangan = sum(r['cadangan'] for r in rekap)

        tmpl = 'print/laporan_kolektibilitas_rekap.html' if cetak else 'laporan/kolektibilitas.html'
        return render_template(tmpl,
            rekap=rekap, summary=summary_total,
            KOLEK_LABELS=KOLEK_LABELS, KOLEK_CADANGAN=KOLEK_CADANGAN,
            total_saldo=total_saldo, total_cadangan=total_cadangan,
            desa_list=Config.DESA_LIST, tanggal_cetak=date.today())


# ── MONITORING TUNGGAKAN ─────────────────────────────────────
@laporan_bp.route('/tunggakan')
@login_required
def tunggakan():
    desa_filter = request.args.get('desa', '')
    if current_user.is_kader():
        desa_filter = current_user.kode_desa

    q = Pinjaman.query.join(Nasabah).filter(Pinjaman.status == 'cair')
    if desa_filter:
        q = q.filter(Nasabah.kode_desa == desa_filter)
    elif current_user.is_kader():
        q = q.filter(Nasabah.kode_desa == current_user.kode_desa)

    rows = []
    for p in q.all():
        tp, tj, bn = p.get_tunggakan()
        if bn > 0:
            kolek, klbl = p.get_kolektibilitas()
            rows.append({'p': p, 'tunggak_pokok': tp, 'tunggak_jasa': tj,
                          'total_tunggak': tp+tj, 'bulan_nunggak': bn,
                          'kolek': kolek, 'kolek_label': klbl})
    rows.sort(key=lambda x: (-x['bulan_nunggak'], -x['total_tunggak']))
    total_tunggak = sum(r['total_tunggak'] for r in rows)

    # Summary by kolek
    kolek_summary = {2: {'jml': 0, 'total': 0}, 3: {'jml': 0, 'total': 0}, 4: {'jml': 0, 'total': 0}, 5: {'jml': 0, 'total': 0}}
    for r in rows:
        k = r['kolek']
        if k in kolek_summary:
            kolek_summary[k]['jml'] += 1
            kolek_summary[k]['total'] += r['total_tunggak']

    # Pengaturan WA
    from ..models import Pengaturan
    wa_pengirim = Pengaturan.get('wa_pengirim', '')

    lembaga={'nama':Pengaturan.get('nama_lembaga'),'direktur':Pengaturan.get('direktur')}
    tmpl = 'print/laporan_tunggakan.html' if request.args.get('cetak')=='1' else 'laporan/tunggakan.html'
    return render_template(tmpl, rows=rows, lembaga=lembaga,
        total_tunggak=total_tunggak, desa_filter=desa_filter,
        desa_list=Config.DESA_LIST, wa_pengirim=wa_pengirim,
        kolek_summary=kolek_summary)



