"""Test the real ELF worker's protocol and teardown without a printer."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
runtime = root / "custom_components/bambu_open_network/bin" / sys.argv[1]
for name in ("loader", "obn-ha-worker"):
    if not os.access(runtime / name, os.X_OK):
        (runtime / name).chmod(0o755)
command = [str(runtime / "loader"), "--library-path", str(runtime / "lib"),
           str(runtime / "obn-ha-worker")]
out = subprocess.run(command + ["--self-test"], capture_output=True, text=True, check=True, timeout=10)
assert json.loads(out.stdout)["protocol"] == 3
out = subprocess.run(command + ["--provision-credentials"],
    input=json.dumps({"credentials_directory": "relative-target"}) + "\n",
    capture_output=True, text=True, timeout=10)
assert out.returncode == 1 and json.loads(out.stdout) == {"ok": False}
# Invalid methods must return an error and must not silently accept a publish.
out = subprocess.run(command, input=json.dumps({
    "id": 1, "method": "publish", "params": {"payload": "{}"}}) + "\n",
    capture_output=True, text=True, check=True, timeout=10)
assert json.loads(out.stdout) == {"id": 1, "rc": -19}
# Initialize an offline LAN target with certificate verification enabled.
# This exercises OBN create/configure/connect/destroy and JSON stdin/EOF.
with tempfile.TemporaryDirectory() as state:
    Path(state, "obn.conf").write_text(
        "block_cloud = 1\nlog_stderr = 0\nlog_level = error\nmqtt_keep_connection = 0\n")
    request = {"id": 2, "method": "init", "params": {
        "serial": "TESTOFFLINE", "host": "127.0.0.1", "local": True,
        "username": "bblp", "password": "dummy", "state_directory": state,
        "ca_file": "", "country": "US"}}
    out = subprocess.run(command, input=json.dumps(request) + "\n",
                         capture_output=True, text=True, timeout=25)
    events = [json.loads(line) for line in out.stdout.splitlines()]
    assert any(event.get("id") == 2 or event.get("event") == "error" for event in events)
print("Native protocol smoke passed; printer behavior is not tested.")
