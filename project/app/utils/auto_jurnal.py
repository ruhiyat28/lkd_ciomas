"""
Auto-jurnal untuk transaksi Dana Bergulir.
Setiap pencairan dan pembayaran angsuran otomatis menciptakan jurnal akuntansi.

Standar: Kepmendesa 136/2022 basis akrual.
"""
import logging
from datetime import date
from ..models import db, JurnalUmum, JurnalDetail, AkunCOA
from .coa_seed import (
    AKUN_PIUTANG_PINJAMAN, AKUN_PENDAPATAN_JASA,
    AKUN_KAS,
    get_akun_by_kode
)

logger = logging.getLogger(__name__)


def _get_no_jurnal(tipe_prefix):
    """Generate nomor jurnal unik: JU/YYYY/MM/XXXX."""
    today = date.today()
    prefix = f"JU-{tipe_prefix}/{today.year}/{today.month:02d}/"
    count = JurnalUmum.query.filter(JurnalUmum.no_jurnal.like(f'{prefix}%')).count() + 1
    return f"{prefix}{count:04d}"


def _buat_jurnal(no, tanggal, keterangan, referensi, tipe, baris, created_by=None):
    """Helper buat jurnal + detail rows."""
    total_debit  = sum(b[2] for b in baris)
    total_kredit = sum(b[3] for b in baris)
    if total_debit != total_kredit:
        raise ValueError(f"Jurnal tidak balance: D={total_debit} K={total_kredit}")

    j = JurnalUmum(
        no_jurnal    = no,
        tanggal      = tanggal,
        keterangan   = keterangan,
        referensi    = referensi,
        tipe         = tipe,
        status       = 'posted',
        total_debit  = total_debit,
        total_kredit = total_kredit,
        created_by   = created_by,
    )
    db.session.add(j)
    db.session.flush()

    for akun_kode, ket_baris, debit, kredit in baris:
        akun = get_akun_by_kode(akun_kode)
        if not akun:
            continue  # skip jika COA belum di-seed
        db.session.add(JurnalDetail(
            jurnal_id  = j.id,
            akun_id    = akun.id,
            keterangan = ket_baris,
            debit      = debit,
            kredit     = kredit,
        ))
    return j


def jurnal_pencairan(pinjaman, created_by=None):
    """
    Saat pinjaman dicairkan:
      Dr. 1.1.03 Piutang Pinjaman      xxx
        Cr. 1.1.01 Kas                     xxx
    """
    try:
        no  = _get_no_jurnal('PCR')
        ket = f"Pencairan pinjaman {pinjaman.spk} — {pinjaman.nasabah.nama}"
        baris = [
            (AKUN_PIUTANG_PINJAMAN, ket, pinjaman.jumlah_pinjaman, 0),
            (AKUN_KAS,              ket, 0, pinjaman.jumlah_pinjaman),
        ]
        j = _buat_jurnal(no, pinjaman.tanggal_cair or date.today(),
                         ket, pinjaman.spk, 'pencairan', baris, created_by)
        db.session.commit()
        return j
    except Exception as e:
        db.session.rollback()
        logger.error('Jurnal pencairan gagal untuk %s: %s', pinjaman.spk, e)
        return None


def jurnal_pembayaran(pembayaran, created_by=None):
    """
    Saat angsuran diterima (basis akrual):
      Dr. 1.1.01 Kas                   total_bayar
        Cr. 1.1.03 Piutang Pinjaman       bayar_pokok
        Cr. 4.1.01 Pendapatan Jasa         bayar_jasa
    """
    try:
        p   = pembayaran.pinjaman
        no  = _get_no_jurnal('AGS')
        ket = f"Angsuran {p.spk} ke-{pembayaran.angsuran_ke or '?'} — {p.nasabah.nama}"
        baris = [
            (AKUN_KAS,              ket, pembayaran.jumlah_bayar, 0),
            (AKUN_PIUTANG_PINJAMAN, ket, 0, pembayaran.bayar_pokok),
            (AKUN_PENDAPATAN_JASA,  ket, 0, pembayaran.bayar_jasa),
        ]
        j = _buat_jurnal(no, pembayaran.tanggal_bayar,
                         ket, pembayaran.no_kuitansi, 'angsuran', baris, created_by)
        db.session.commit()
        return j
    except Exception as e:
        db.session.rollback()
        logger.error('Jurnal pembayaran gagal untuk %s: %s', pembayaran.no_kuitansi, e)
        return None
