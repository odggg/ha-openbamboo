"""Record all bundled runtime checksums; used by the loader and packaging gate."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(root.rglob("*")) if p.is_file() and p.name != "runtime.json"}
(root / "runtime.json").write_text(json.dumps({
    "protocol": 4,
    "obn_repository": "persano/open-bamboo-networking",
    "obn_commit": "85c2b52445721bccc49534e82f52650037189d4f",
    "architecture": sys.argv[2],
    "sha256": files,
}, indent=2) + "\n")
