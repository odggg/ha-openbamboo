"""Fail closed if a HACS release is missing either native architecture."""
import hashlib
import json
from pathlib import Path
import sys
import shutil
import zipfile

root = Path(__file__).resolve().parents[1]
component = root / "custom_components/bambu_open_network"
manifest = json.loads((component / "manifest.json").read_text())
if "OWNER/" in manifest["documentation"]:
    raise SystemExit("Configure the real repository before packaging.")
for arch in ("amd64", "aarch64"):
    directory = component / "bin" / arch
    info = json.loads((directory / "runtime.json").read_text())
    for name, digest in info["sha256"].items():
        path = directory / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit("Runtime checksum mismatch: " + name)
    if not {"loader", "obn-ha-worker", "lib/libbambu_networking.so"}.issubset(info["sha256"]):
        raise SystemExit("Native bundle incomplete: " + arch)
if not (root / "vendor/open-bamboo-networking/CMakeLists.txt").is_file():
    raise SystemExit("Exact OBN corresponding source missing.")
shutil.copytree(root / "LICENSES", component / "licenses", dirs_exist_ok=True)
shutil.copyfile(root / "LICENSE", component / "LICENSE")
shutil.copyfile(root / "NOTICE.md", component / "NOTICE.md")
for forbidden in ("slicer_key.pem", "slicer_cert.pem", "slicer_crl.pem"):
    if any(component.rglob(forbidden)):
        raise SystemExit("Provisioned credentials must not be packaged: " + forbidden)

dist = root / "dist"
dist.mkdir(exist_ok=True)
# HACS zip_release expects component contents at the ZIP root.
with zipfile.ZipFile(dist / "bambu_open_network.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(component.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            archive.write(path, path.relative_to(component))
with zipfile.ZipFile(dist / "bambu_open_network-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for parent in ("native", "scripts", "vendor", "LICENSES", "tests"):
        for path in sorted((root / parent).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(root))
    for name in ("LICENSE", "NOTICE.md", "README.md"):
        archive.write(root / name, name)
    for path in sorted(component.rglob("*")):
        if path.is_file() and not any(part in ("__pycache__", "bin") for part in path.relative_to(component).parts):
            archive.write(path, path.relative_to(root))
    for path in sorted((root / ".github").rglob("*.yml")):
        archive.write(path, path.relative_to(root))
print("Packaged HACS integration and corresponding source.")
