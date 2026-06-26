import os
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
