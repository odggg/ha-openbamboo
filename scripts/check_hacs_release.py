"""Check the real release asset HACS will install before/after publication."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("metadata", type=Path)
parser.add_argument("--tag", required=True)
parser.add_argument("--assets", type=Path)
parser.add_argument("--previous", type=Path)
parser.add_argument("--regular", action="store_true")
args = parser.parse_args()
release = json.loads(args.metadata.read_text())
assert release["tag_name"] == args.tag, "Unexpected release version"
assert not release["draft"], "Draft release cannot be installed by HACS"
assets = {item["name"]: item for item in release["assets"]}
required = {"bambu_open_network.zip", "bambu_open_network-source.zip"}
assert required.issubset(assets), "Missing integration/corresponding-source ZIP"
for name in required:
    item = assets[name]
    assert item["state"] == "uploaded" and item["size"] > 0, "Incomplete asset"
    assert item["digest"].startswith("sha256:"), "Missing asset digest"
    if args.assets:
        path = args.assets / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["digest"][7:], "Asset digest mismatch"
if args.assets:
    with zipfile.ZipFile(args.assets / "bambu_open_network.zip") as package:
        manifest = json.loads(package.read("manifest.json"))
        assert manifest["domain"] == "bambu_open_network"
        assert "v" + manifest["version"] == args.tag
        for arch in ("amd64", "aarch64"):
            assert f"bin/{arch}/runtime.json" in package.namelist()
        assert not any(Path(name).name in (
            "slicer_key.pem", "slicer_cert.pem", "slicer_crl.pem") for name in package.namelist())
if args.previous:
    previous = json.loads(args.previous.read_text())
    assert release["id"] == previous["id"], "Release was replaced"
    assert {a["name"]: a["digest"] for a in release["assets"]} == {
        a["name"]: a["digest"] for a in previous["assets"]}, "Release assets changed"
if args.regular:
    assert not release["prerelease"], "Release still marked prerelease"
print(f"{args.tag}: valid HACS release; regular={not release['prerelease']}.")
