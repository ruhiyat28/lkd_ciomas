"""Shared helper functions used across routes."""
import re
import uuid
import logging
import secrets
import string

logger = logging.getLogger(__name__)

def safe_nik(nik_input):
    """Return a valid unique NIK: use provided or generate placeholder."""
    nik = (nik_input or '').strip()
    if not nik:
        return f"NOID-{uuid.uuid4().hex[:12].upper()}"
    return nik


def validate_password(password, min_length=6, require_upper=False, require_digit=False, require_special=False):
    """Validate password strength. Returns list of error messages (empty if valid)."""
    errors = []
    if len(password) < min_length:
        errors.append(f'Password minimal {min_length} karakter.')
    if require_upper and not re.search(r'[A-Z]', password):
        errors.append('Password harus mengandung huruf besar.')
    if require_digit and not re.search(r'[0-9]', password):
        errors.append('Password harus mengandung angka.')
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('Password harus mengandung karakter khusus (!@#$%^&* dll).')
    return errors


def generate_random_password(length=12):
    """Generate a secure random password with mixed character types."""
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    special = '!@#$%^&*'
    # Ensure at least one of each type
    password = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    # Fill the rest
    all_chars = lower + upper + digits + special
    password += [secrets.choice(all_chars) for _ in range(length - 4)]
    # Shuffle
    password_list = list(password)
    for i in range(len(password_list) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password_list[i], password_list[j] = password_list[j], password_list[i]
    return ''.join(password_list)


ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def save_file(file, subfolder, prefix='', max_width=1200, quality=75, force_portrait=False):
    from flask import current_app
    import os
    from werkzeug.utils import secure_filename
    from datetime import datetime
    
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Save original file first
        file.save(path)
        
        # Compress if it's an image
        if ext in ['jpg', 'jpeg', 'png', 'webp']:
            try:
                from PIL import Image, ExifTags
                img = Image.open(path)
                
                # Handle EXIF orientation
                try:
                    exif = img.getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = ExifTags.TAGS.get(tag_id, tag_id)
                            if tag == 'Orientation':
                                orientation = value
                                if orientation == 3:
                                    img = img.rotate(180, expand=True)
                                elif orientation == 6:
                                    img = img.rotate(270, expand=True)
                                elif orientation == 8:
                                    img = img.rotate(90, expand=True)
                                break
                except Exception:
                    pass
                
                # For selfie/foto: force portrait (tall) orientation
                if force_portrait and img.height < img.width:
                    img = img.rotate(90, expand=True)
                
                # Resize if too large
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to RGB if needed (for JPEG)
                if ext in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'P']:
                    img = img.convert('RGB')
                
                # Save with compression
                img.save(path, quality=quality, optimize=True)
                
                logger.info(f"Compressed: {filename} (saved at quality={quality})")
            except Exception as e:
                logger.warning(f"Compression failed for {filename}: {e}")
        
        return f"uploads/{subfolder}/{filename}"
    return None


def get_next_nasabah_id(kode_desa, start_from=1):
    """Generate next nasabah_id (e.g. UT-001) using efficient query.
    
    Args:
        kode_desa: Village code (e.g., 'UT', 'CS')
        start_from: Starting number for the sequence (default 1, use 899 for kader)
    """
    from ..models import Nasabah

    prefix = f"{kode_desa.upper()}-"
    existing = Nasabah.query.with_entities(Nasabah.nasabah_id).filter(
        Nasabah.kode_desa == kode_desa,
        Nasabah.nasabah_id.like(f"{prefix}%")
    ).all()
    
    nums = []
    for (nid,) in existing:
        try:
            parts = nid.split('-')
            if len(parts) > 1:
                num = int(parts[1])
                if num >= start_from:
                    nums.append(num)
        except (ValueError, IndexError):
            pass
    
    next_num = max(nums) + 1 if nums else start_from

    return f"{kode_desa.upper()}-{next_num:03d}"


def generate_signature_qr(signature_filename):
    """
    Generate QR code for a digital signature.
    Returns base64 data URI of the QR code image.
    The QR code contains the full URL to the signature image.
    """
    try:
        import qrcode
        import io
        import base64
        from flask import request

        if not signature_filename:
            logger.debug("QR generation: no signature filename")
            return None

        # Build URL from request context
        scheme = request.scheme or 'https'
        host = request.host or ''
        sig_url = f"{scheme}://{host}/static/{signature_filename}"

        logger.info(f"QR generation for: {sig_url}")

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(sig_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{img_base64}"
    except ImportError:
        logger.warning("qrcode library not installed")
        return None
    except Exception as e:
        logger.warning(f"QR code generation failed: {e}", exc_info=True)
        return None
