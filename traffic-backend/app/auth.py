from datetime import datetime, timedelta, timezone
import os

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

ALGORITHM = os.getenv(
    "ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "30"
    )
)


# SECRET_KEY is required for JWT security
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not configured in the environment."
    )


# ============================================================
# PASSWORD HASHING
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    bcrypt only supports passwords up to 72 bytes,
    so the password is limited to the first 72 characters.
    """

    pwd_bytes = password[:72].encode("utf-8")

    salt = bcrypt.gensalt()

    hashed = bcrypt.hashpw(
        pwd_bytes,
        salt
    )

    return hashed.decode("utf-8")


# ============================================================
# PASSWORD VERIFICATION
# ============================================================

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Verify a plain-text password against its bcrypt hash.
    """

    try:
        pwd_bytes = plain_password[:72].encode("utf-8")

        return bcrypt.checkpw(
            pwd_bytes,
            hashed_password.encode("utf-8")
        )

    except (ValueError, TypeError):
        return False


# ============================================================
# JWT ACCESS TOKEN
# ============================================================

def create_access_token(data: dict) -> str:
    """
    Create a JWT access token with an expiration time.
    """

    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update({
        "exp": expire
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ============================================================
# JWT TOKEN VERIFICATION
# ============================================================

def verify_token(token: str) -> dict | None:
    """
    Verify and decode a JWT token.

    Returns:
        payload dictionary if valid
        None if invalid or expired
    """

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:
        return None