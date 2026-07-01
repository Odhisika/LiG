import os
import re
import struct
from django.core.exceptions import ValidationError
from django.conf import settings


ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp',
    'pdf', 'doc', 'docx',
}
MAX_UPLOAD_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)

MAGIC_BYTES = {
    b'\xff\xd8\xff': 'jpg/jpeg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',
    b'%PDF': 'pdf',
}


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower().lstrip('.')
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f'Unsupported file extension: .{ext}. Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}.')


def validate_file_size(value):
    if value.size > MAX_UPLOAD_SIZE:
        raise ValidationError(f'File too large ({(value.size / 1024 / 1024):.1f} MB). Maximum allowed: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f} MB.')


def validate_file_content(value):
    try:
        header = value.read(16)
        value.seek(0)
    except Exception:
        return
    for magic, name in MAGIC_BYTES.items():
        if header.startswith(magic):
            return
    ext = os.path.splitext(value.name)[1].lower().lstrip('.')
    if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf'):
        raise ValidationError(f'File content does not match expected format for .{ext}.')


def validate_image(value):
    validate_file_extension(value)
    validate_file_size(value)
    validate_file_content(value)


ALLOWED_EMAIL_DOMAINS = {
    'gmail.com', 'googlemail.com',
    'yahoo.com', 'yahoo.co.uk', 'yahoo.fr', 'yahoo.de', 'yahoo.co.jp',
    'yahoo.com.au', 'yahoo.co.in', 'yahoo.com.br', 'yahoo.com.mx',
    'yahoo.es', 'yahoo.it', 'yahoo.ca',
    'outlook.com', 'hotmail.com', 'hotmail.co.uk', 'live.com', 'msn.com',
    'proton.me', 'protonmail.com',
    'icloud.com',
    'aol.com',
    'mail.com',
}


def validate_email_domain(email):
    if not email:
        return
    domain = email.split('@')[-1].lower()
    if domain not in ALLOWED_EMAIL_DOMAINS:
        raise ValidationError(
            "Registration is limited to trusted email providers. "
            "Please use Gmail, Yahoo, Outlook/Hotmail, Proton, iCloud, AOL, or Mail.com."
        )


GHANA_PHONE_PREFIXES = {
    '020', '023', '024', '025', '026', '027', '028', '029',
    '037', '050', '053', '054', '055', '056', '057', '059',
}


def validate_ghana_phone_number(value):
    if not value:
        return ''
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', value)
    if cleaned.startswith('+233'):
        if not cleaned[1:].isdigit() or len(cleaned) != 13:
            raise ValidationError("Enter a valid Ghana phone number (e.g. 024XXXXXXX or +23324XXXXXXX).")
        local = '0' + cleaned[4:]
    elif cleaned.startswith('233'):
        if not cleaned.isdigit() or len(cleaned) != 12:
            raise ValidationError("Enter a valid Ghana phone number (e.g. 024XXXXXXX or +23324XXXXXXX).")
        local = '0' + cleaned[3:]
    elif cleaned.startswith('0'):
        if not cleaned.isdigit() or len(cleaned) != 10:
            raise ValidationError("Enter a valid Ghana phone number (e.g. 024XXXXXXX).")
        local = cleaned
    else:
        raise ValidationError("Enter a valid Ghana phone number (e.g. 024XXXXXXX or +23324XXXXXXX).")
    if local[:3] not in GHANA_PHONE_PREFIXES:
        raise ValidationError("Enter a valid Ghana phone number with a recognised mobile network prefix.")
    return local
