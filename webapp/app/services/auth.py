"""Authentication service with password hashing and JWT sessions."""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import hmac
import base64
import secrets
import json

from webapp.app.config import settings

# Try to import bcrypt and jose, fall back to simpler methods if not available
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    from jose import jwt, JWTError
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False


# Secret key for JWT (in production, use environment variable)
SECRET_KEY = getattr(settings, 'secret_key', 'splicing-predictor-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (or fallback)."""
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        # Fallback: SHA256 with salt (less secure, but works without dependencies)
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return f"pbkdf2:{salt}:{hash_obj.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if BCRYPT_AVAILABLE and not hashed_password.startswith('pbkdf2:'):
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    elif hashed_password.startswith('pbkdf2:'):
        # Fallback verification
        try:
            _, salt, expected_hash = hashed_password.split(':')
            hash_obj = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return hmac.compare_digest(hash_obj.hex(), expected_hash)
        except Exception:
            return False
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})

    if JOSE_AVAILABLE:
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    else:
        # Fallback: Simple base64 encoded JSON with signature
        payload = json.dumps(to_encode, default=str)
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
        signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{signature}"


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token."""
    try:
        if JOSE_AVAILABLE:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        else:
            # Fallback: Verify simple token
            parts = token.split('.')
            if len(parts) != 2:
                return None

            payload_b64, signature = parts
            expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return None

            payload = json.loads(base64.urlsafe_b64decode(payload_b64))

            # Check expiration
            if 'exp' in payload:
                exp = datetime.fromisoformat(payload['exp']) if isinstance(payload['exp'], str) else datetime.utcfromtimestamp(payload['exp'])
                if exp < datetime.utcnow():
                    return None

            return payload
    except Exception:
        return None


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)
