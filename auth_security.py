"""
Authentication & Security Module for Metrolab (SIH-26035)
Implements JWT tokens with HMAC-SHA256 signature, payload claims verification,
and secure token issuance/validation.
"""

import hmac
import hashlib
import base64
import json
import time
import os

SECRET_KEY = os.environ.get("METROLAB_JWT_SECRET", "metrolab-sih26035-secure-jwt-hmac-sha256-key-2026")

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def _b64url_decode(data_str: str) -> bytes:
    padding = 4 - (len(data_str) % 4)
    if padding < 4:
        data_str += '=' * padding
    return base64.urlsafe_b64decode(data_str.encode('ascii'))

def create_jwt_token(payload: dict, expires_in_seconds: int = 86400) -> str:
    """Creates an HMAC-SHA256 signed JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    header_b64 = _b64url_encode(header_json)

    full_payload = dict(payload)
    now = int(time.time())
    full_payload["iat"] = now
    full_payload["exp"] = now + expires_in_seconds

    payload_json = json.dumps(full_payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = _b64url_encode(payload_json)

    message = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_jwt_token(token: str) -> dict:
    """Verifies HMAC-SHA256 signature and expiry of a JWT token. Returns payload dict or None."""
    if not token or not isinstance(token, str):
        return None

    parts = token.split('.')
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts

    try:
        message = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))

        if "exp" in payload and time.time() > payload["exp"]:
            return None

        return payload
    except Exception:
        return None
