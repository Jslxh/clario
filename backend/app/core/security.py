import hmac
import hashlib
import base64
import json
import time
import uuid
from typing import Optional, Dict, Any, List

from app.core.config import settings


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with deterministic salt formatting."""
    if salt is None:
        salt = base64.b64encode(uuid.uuid4().bytes).decode("utf-8")
    
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    hashed_str = base64.b64encode(dk).decode("utf-8")
    return f"{salt}${hashed_str}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against salt$hash string."""
    try:
        parts = hashed_password.split("$", 1)
        if len(parts) != 2:
            return False
        salt, _ = parts
        expected = hash_password(plain_password, salt=salt)
        return hmac.compare_digest(expected, hashed_password)
    except Exception:
        return False


def create_access_token(
    subject: str,
    email: str,
    roles: List[str],
    department: Optional[str] = None,
    expires_delta_seconds: Optional[int] = None,
) -> str:
    """Create a signed HMAC-SHA256 bearer token."""
    now = int(time.time())
    expires = now + (expires_delta_seconds or (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))

    payload = {
        "sub": subject,
        "email": email,
        "roles": roles,
        "department": department,
        "iat": now,
        "exp": expires,
    }

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    
    signature = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")

    return f"{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed HMAC-SHA256 bearer token."""
    try:
        parts = token.split(".", 1)
        if len(parts) != 2:
            return None
        
        payload_b64, sig_b64 = parts
        
        # Verify signature
        expected_sig = hmac.new(
            settings.JWT_SECRET.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")
        
        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            return None

        # Pad base64 if needed
        padding = "=" * (4 - (len(payload_b64) % 4)) if (len(payload_b64) % 4) != 0 else ""
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None
