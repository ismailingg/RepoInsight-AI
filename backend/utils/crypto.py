import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# APP_SECRET must be a valid Fernet key
# Generate once with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
_raw = os.getenv("APP_SECRET", "")

if not _raw:
    raise RuntimeError(
        "APP_SECRET is not set in .env\n"
        "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

try:
    _fernet = Fernet(_raw.encode() if isinstance(_raw, str) else _raw)
except Exception:
    raise RuntimeError(
        "APP_SECRET is not a valid Fernet key.\n"
        "Generate a fresh one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )


def encrypt_key(plaintext: str) -> str:
    """
    Encrypt an API key before storing in PostgreSQL.
    Returns a URL-safe base64 encoded ciphertext string.
    """
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """
    Decrypt an API key retrieved from PostgreSQL.
    Returns the original plaintext key.
    """
    return _fernet.decrypt(ciphertext.encode()).decode()