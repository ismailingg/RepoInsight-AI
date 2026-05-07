from backend.utils.crypto import encrypt_key, decrypt_key

def test_encryption_decryption_cycle():
    original = "sk-test-key-12345"
    encrypted = encrypt_key(original)
    
    assert encrypted != original
    assert isinstance(encrypted, str)
    
    decrypted = decrypt_key(encrypted)
    assert decrypted == original

def test_unique_encryption():
    # Fernet adds salt/IV, so encrypting the same text twice should yield different ciphertexts
    text = "test-secret"
    enc1 = encrypt_key(text)
    enc2 = encrypt_key(text)
    
    assert enc1 != enc2
    assert decrypt_key(enc1) == decrypt_key(enc2) == text
