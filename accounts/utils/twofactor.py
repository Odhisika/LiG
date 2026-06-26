import hmac
import hashlib
import struct
import time
import base64
import os
import qrcode
import io
from base64 import b32encode


def generate_totp_secret():
    return b32encode(os.urandom(20)).decode('utf-8')


def totp(secret, digits=6, interval=30):
    key = base64.b32decode(secret, casefold=True)
    counter = struct.pack('>Q', int(time.time()) // interval)
    h = hmac.new(key, counter, hashlib.sha1).digest()
    offset = h[-1] & 0x0f
    truncated = struct.unpack('>I', h[offset:offset + 4])[0] & 0x7fffffff
    return str(truncated % 10 ** digits).zfill(digits)


def verify_totp(secret, code, digits=6, window=1):
    if not code or not code.isdigit():
        return False
    current = int(time.time()) // 30
    for i in range(-window, window + 1):
        counter = struct.pack('>Q', current + i)
        key = base64.b32decode(secret, casefold=True)
        h = hmac.new(key, counter, hashlib.sha1).digest()
        offset = h[-1] & 0x0f
        truncated = struct.unpack('>I', h[offset:offset + 4])[0] & 0x7fffffff
        expected = str(truncated % 10 ** digits).zfill(digits)
        if hmac.compare_digest(expected, code):
            return True
    return False


def generate_backup_codes(count=8):
    codes = []
    for _ in range(count):
        code = os.urandom(5).hex()[:10]
        codes.append({'code': code, 'used': False})
    return codes


def get_totp_uri(secret, email, issuer='LiG Admin'):
    return f'otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30'


def generate_qr_code(secret, email):
    uri = get_totp_uri(secret, email)
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
