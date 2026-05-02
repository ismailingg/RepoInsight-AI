# test_crypto.py
from backend.utils.crypto import encrypt_key, decrypt_key

original = "sk-test-key-12345"
encrypted = encrypt_key(original)
decrypted = decrypt_key(encrypted)

print(f"Original:  {original}")
print(f"Encrypted: {encrypted[:40]}...")
print(f"Decrypted: {decrypted}")
print(f"Match: {original == decrypted}")