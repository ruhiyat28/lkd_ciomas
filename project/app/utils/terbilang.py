def terbilang(angka):
    """Konversi angka ke teks Indonesia"""
    angka = int(angka)
    if angka < 0:
        return "minus " + terbilang(-angka)
    if angka == 0:
        return "nol"

    satuan = ['', 'satu', 'dua', 'tiga', 'empat', 'lima',
              'enam', 'tujuh', 'delapan', 'sembilan', 'sepuluh',
              'sebelas', 'dua belas', 'tiga belas', 'empat belas',
              'lima belas', 'enam belas', 'tujuh belas', 'delapan belas', 'sembilan belas']

    PULUHAN = ['', 'se', 'dua ', 'tiga ', 'empat ', 'lima ',
               'enam ', 'tujuh ', 'delapan ', 'sembilan ']

    def _ratusan(n):
        if n == 0:
            return ''
        if n < 20:
            return satuan[n]
        if n < 100:
            puluh = n // 10
            sisa = n % 10
            return PULUHAN[puluh] + 'puluh' + ((' ' + satuan[sisa]) if sisa else '')
        ratus = n // 100
        sisa = n % 100
        prefix = 'seratus' if ratus == 1 else satuan[ratus] + ' ratus'
        return prefix + (' ' + _ratusan(sisa) if sisa else '')

    def _jutaan(n):
        if n == 0:
            return ''
        if n < 1000:
            return _ratusan(n)
        if n < 1_000_000:
            ribuan = n // 1000
            sisa = n % 1000
            prefix = 'seribu' if ribuan == 1 else _ratusan(ribuan) + ' ribu'
            return prefix + (' ' + _ratusan(sisa) if sisa else '')
        if n < 1_000_000_000:
            jutaan = n // 1_000_000
            sisa = n % 1_000_000
            return _ratusan(jutaan) + ' juta' + (' ' + _jutaan(sisa) if sisa else '')
        miliaran = n // 1_000_000_000
        sisa = n % 1_000_000_000
        return _ratusan(miliaran) + ' miliar' + (' ' + _jutaan(sisa) if sisa else '')

    result = _jutaan(angka)
    return result.strip().capitalize() if result else 'nol'
