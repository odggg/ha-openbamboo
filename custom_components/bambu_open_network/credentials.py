"""Provision the Orca plugin fork's signing material into HA's standard folder."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import threading

FILES = ("slicer_key.pem", "slicer_cert.pem", "slicer_crl.pem")
MAX_PEM = 256 * 1024


def valid_material(folder, *, refresh_before=timedelta(days=7)):
    """Check dates, CRL freshness and matching key; never return PEM contents."""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        paths = [Path(folder) / name for name in FILES]
        if any(p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_PEM
               for p in paths):
            return False
        key = serialization.load_pem_private_key(paths[0].read_bytes(), password=None)
        certs = x509.load_pem_x509_certificates(paths[1].read_bytes())
        crl = x509.load_pem_x509_crl(paths[2].read_bytes())
        now = datetime.now(timezone.utc)
        expiry = now + refresh_before
        if not certs or any(not (c.not_valid_before_utc <= now
                                and c.not_valid_after_utc > expiry) for c in certs):
            return False
        if crl.last_update_utc > now or not crl.next_update_utc or crl.next_update_utc <= expiry:
            return False
        public = lambda obj: obj.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return public(key.public_key()) == public(certs[0].public_key())
    except Exception:
        return False


class CredentialManager:
    def __init__(self, command, folder, config_root):
        self.command = list(command)
        self.folder = Path(folder).resolve()
        self.config_root = Path(config_root).resolve()
        self.status = "not_checked"
        self._lock = threading.Lock()

    def ensure(self):
        """Return True only after a validated refresh; caller reloads workers."""
        if not self._lock.acquire(blocking=False):
            return False
        try:
            return self._ensure()
        finally:
            self._lock.release()

    def _ensure(self):
        if not self.folder.is_relative_to(self.config_root):
            self.status = "invalid_folder"
            return False
        if valid_material(self.folder):
            self.status = "ready"
            return False
        originals = {}
        try:
            self.folder.mkdir(parents=True, mode=0o700, exist_ok=True)
            for name in FILES:
                p = self.folder / name
                if p.is_symlink() or (p.exists() and p.stat().st_size > MAX_PEM):
                    raise ValueError("Invalid credential target")
                originals[name] = p.read_bytes() if p.exists() else None
            env = {k: v for k, v in os.environ.items() if not k.startswith("OBN_")}
            env.update({"OBN_LOG_LEVEL": "off", "OBN_LOG_STDERR": "0",
                        "OBN_LOG_TO_FILE": "0"})
            bundle = Path(self.command[0]).parent / "ca-bundle.pem"
            if bundle.is_file():
                env.update({"SSL_CERT_FILE": str(bundle), "CURL_CA_BUNDLE": str(bundle)})
            result = subprocess.run(
                self.command + ["--provision-credentials"],
                input=json.dumps({"credentials_directory": str(self.folder)}) + "\n",
                text=True, encoding="utf-8", stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=45, env=env,
            )
            if result.returncode or json.loads(result.stdout) != {"ok": True}:
                raise ValueError("Credential endpoint unavailable")
            if not valid_material(self.folder, refresh_before=timedelta()):
                raise ValueError("Returned credentials invalid")
            for name in FILES:
                (self.folder / name).chmod(0o600)
            self.status = "ready"
            return True
        except Exception:
            # Multi-file provisioning may fail partway through. Restore each
            # prior file; never replace working material with a partial set.
            for name, original in originals.items():
                p = self.folder / name
                try:
                    if original is None:
                        p.unlink(missing_ok=True)
                    else:
                        temp = self.folder / (name + ".rollback")
                        with open(temp, "wb") as stream:
                            stream.write(original)
                        temp.chmod(0o600)
                        temp.replace(p)
                except OSError:
                    pass
            self.status = "provision_failed"
            return False
