"""Offline credential endpoint fixture: generates fresh, test-only signing material."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

mode = sys.argv[1]
target = Path(json.loads(sys.stdin.readline())["credentials_directory"])
if mode == "failed":
    (target / "slicer_cert.pem").write_text("partial broken response")
    print(json.dumps({"ok": False}))
    sys.exit(1)
if mode == "invalid":
    for name in ("slicer_key.pem", "slicer_cert.pem", "slicer_crl.pem"):
        (target / name).write_text("not credentials")
    print(json.dumps({"ok": True}))
    sys.exit(0)
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "OFFLINE TEST ONLY")])
now = datetime.now(timezone.utc)
cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256()))
crl = (x509.CertificateRevocationListBuilder().issuer_name(name)
       .last_update(now - timedelta(minutes=1))
       .next_update(now + timedelta(days=30)).sign(key, hashes.SHA256()))
(target / "slicer_key.pem").write_bytes(key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()))
(target / "slicer_cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
(target / "slicer_crl.pem").write_bytes(crl.public_bytes(serialization.Encoding.PEM))
print(json.dumps({"ok": True}))
