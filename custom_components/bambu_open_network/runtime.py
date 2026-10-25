"""Select and validate the bundled, isolated musl runtime."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

from .const import OBN_COMMIT, PROTOCOL_VERSION

class RuntimeUnavailable(RuntimeError):
    """A release is incomplete or not supported on this machine."""

def architecture(machine: str | None = None) -> str:
    value = (machine or platform.machine()).lower()
    result = {"x86_64": "amd64", "amd64": "amd64",
              "aarch64": "aarch64", "arm64": "aarch64"}.get(value)
    if not result:
        raise RuntimeUnavailable(f"Unsupported architecture: {value}")
    return result

def runtime_command(base: Path | None = None) -> list[str]:
    if platform.system() != "Linux":
        raise RuntimeUnavailable("Home Assistant must run on Linux (amd64 or aarch64).")
    root = (base or Path(__file__).parent / "bin") / architecture()
    loader, worker = root / "loader", root / "obn-ha-worker"
    metadata = root / "runtime.json"
    if not all(p.is_file() for p in (loader, worker, metadata)):
        raise RuntimeUnavailable(
            "Native runtime missing. Install the built HACS release, not the source archive."
        )
    try:
        data = json.loads(metadata.read_text())
        if data["protocol"] != PROTOCOL_VERSION or data["obn_commit"] != OBN_COMMIT:
            raise ValueError("Wrong native runtime revision")
        if data["architecture"] != architecture():
            raise ValueError("Wrong native architecture")
        for name, expected in data["sha256"].items():
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError("Invalid runtime manifest path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Native runtime checksum mismatch: {name}")
        required = {"loader", "obn-ha-worker", "lib/libbambu_networking.so"}
        if not required.issubset(data["sha256"]):
            raise ValueError("Incomplete runtime manifest")
    except (KeyError, ValueError, OSError) as err:
        raise RuntimeUnavailable("Invalid native runtime manifest") from err
    # ZIP/HACS does not preserve execute bits. Never chmod an outside symlink.
    for executable in (loader, worker):
        if executable.is_symlink():
            raise RuntimeUnavailable("Unexpected symlink in runtime")
        executable.chmod(executable.stat().st_mode | 0o500)
    return [str(loader), "--library-path", str(root / "lib"), str(worker)]

def validate_runtime() -> list[str]:
    command = runtime_command()
    try:
        run = subprocess.run(command + ["--self-test"], capture_output=True,
                             text=True, timeout=15, check=True)
        hello = json.loads(run.stdout)
        if hello != {"protocol": PROTOCOL_VERSION, "obn_commit": OBN_COMMIT}:
            raise ValueError("Native protocol mismatch")
    except (OSError, ValueError, subprocess.SubprocessError) as err:
        raise RuntimeUnavailable("Native runtime self-test failed") from err
    return command
