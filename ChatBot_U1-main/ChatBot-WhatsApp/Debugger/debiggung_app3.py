import hmac
import hashlib
import base64

public_key = "BEEEABEE-69CC-41E3-82E1-B958F0AB0D9D"
private_key = "BEEEABEE-69CC-41E3-82E1-B958F0AB0D9D"
method = "POST"
endpoint = "/integrationapi/complain/RegisterCall"
timestamp = "1733484618"

raw_data = f"{public_key}{method}{endpoint}{timestamp}"
hash_digest = hmac.new(
    private_key.encode("utf-8"),
    raw_data.encode("utf-8"),
    hashlib.sha256
).digest()

signature = base64.b64encode(hash_digest).decode()
print(f"Raw Data: {raw_data}")
print(f"Generated Signature: {signature}")