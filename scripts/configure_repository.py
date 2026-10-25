"""Set real repository metadata before publishing this new project."""
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
repository = sys.argv[1] if len(sys.argv) == 2 else ""
if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or repository.startswith("OWNER/"):
    raise SystemExit("Usage: python scripts/configure_repository.py OWNER/REPOSITORY")
manifest = root / "custom_components/bambu_open_network/manifest.json"
data = json.loads(manifest.read_text())
data["documentation"] = "https://github.com/" + repository
data["issue_tracker"] = "https://github.com/" + repository + "/issues"
data["codeowners"] = ["@" + repository.split("/")[0]]
manifest.write_text(json.dumps(data, indent=2) + "\n")
print("Configured repository:", repository)
