from pathlib import Path
import ast
import hashlib
import json
import zipfile

root = Path.cwd()
destination = root.parent / "Bambu_Open_Network_v0.2.0_Cloud_Login_Source.zip"
files = []
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(root)
    if any(part in {"__pycache__", ".test-tmp", "dist", ".git", "bin", "vendor"} for part in rel.parts):
        continue
    if path.suffix == ".py":
        ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
    if path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
    files.append(path)
with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, Path("ha-bambu-open-network") / path.relative_to(root))
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    names = archive.namelist()
    for expected in ("README.md", "PUBLISH_DE.md", ".github/workflows/release.yml",
                     "native/main.cpp", "custom_components/bambu_open_network/upstream_contract.json",
                     "custom_components/bambu_open_network/brand/icon.png"):
        assert "ha-bambu-open-network/" + expected in names
    assert not any("slicer_key.pem" in name for name in names)
print(json.dumps({"path": str(destination), "files": len(files), "bytes": destination.stat().st_size,
                  "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
