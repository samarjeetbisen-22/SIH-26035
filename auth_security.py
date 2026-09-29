"""
Authentication & Security Module for Metrolab (SIH-26035)
Implements JWT tokens with HMAC-SHA256 signature, payload claims verification,
secure token revocation, and secure token issuance/validation.
"""

import hmac
import hashlib
import base64
import json
import time
import os
import secrets

ENVIRONMENT = os.environ.get("METROLAB_ENV", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

# In production, require METROLAB_JWT_SECRET to be explicitly configured.
# In development, provide a secure development key fallback.
SECRET_KEY = os.environ.get("METROLAB_JWT_SECRET")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError("FATAL SECURITY ERROR: METROLAB_JWT_SECRET environment variable must be set in production mode!")
    else:
        SECRET_KEY = "metrolab-sih26035-secure-jwt-hmac-sha256-key-2026"

_REVOKED_TOKEN_HASHES = set()

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def _b64url_decode(data_str: str) -> bytes:
    padding = 4 - (len(data_str) % 4)
    if padding < 4:
        data_str += '=' * padding
    return base64.urlsafe_b64decode(data_str.encode('ascii'))

def revoke_token(token: str) -> bool:
    """Revokes a JWT token so it can no longer be used for authentication."""
    if not token or not isinstance(token, str):
        return False
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    _REVOKED_TOKEN_HASHES.add(token_hash)
    try:
        parts = token.split('.')
        exp = int(time.time()) + 86400
        if len(parts) == 3:
            payload_bytes = _b64url_decode(parts[1])
            payload = json.loads(payload_bytes.decode('utf-8'))
            exp = payload.get("exp", exp)
        import db
        db.revoke_token(token_hash, exp)
    except Exception:
        pass
    return True

def is_token_revoked(token: str) -> bool:
    """Checks whether a token has been revoked / logged out."""
    if not token or not isinstance(token, str):
        return True
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    if token_hash in _REVOKED_TOKEN_HASHES:
        return True
    try:
        import db
        if db.is_token_revoked(token_hash):
            _REVOKED_TOKEN_HASHES.add(token_hash)
            return True
    except Exception:
        pass
    return False

def create_jwt_token(payload: dict, expires_in_seconds: int = 86400) -> str:
    """Creates an HMAC-SHA256 signed JWT token with unique jti nonce."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    header_b64 = _b64url_encode(header_json)

    full_payload = dict(payload)
    now = int(time.time())
    full_payload["iat"] = now
    full_payload["exp"] = now + expires_in_seconds
    full_payload["jti"] = secrets.token_hex(8)

    payload_json = json.dumps(full_payload, separators=(',', ':')).encode('utf-8')
    payload_b64 = _b64url_encode(payload_json)

    message = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_jwt_token(token: str) -> dict:
    """Verifies HMAC-SHA256 signature, expiry, algorithm, and revocation state of a JWT token."""
    if not token or not isinstance(token, str):
        return None

    if is_token_revoked(token):
        return None

    parts = token.split('.')
    if len(parts) != 3:
        return None

    header_b64, payload_b64, sig_b64 = parts

    try:
        header_bytes = _b64url_decode(header_b64)
        header = json.loads(header_bytes.decode('utf-8'))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None

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
