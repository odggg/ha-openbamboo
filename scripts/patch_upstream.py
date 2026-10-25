"""Keep certificate network IO in the HA-managed provisioner, never LAN workers."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
path = root / "src/agent.cpp"
source = path.read_text()
start = source.index("void Agent::ensure_app_cert_material_()\n{")
end = source.index("bool Agent::app_cert_fetch_running()", start)
source = source[:start] + """void Agent::ensure_app_cert_material_()
{
    // ha-openbamboo provisions/renews persistent credentials in an isolated
    // subprocess, then restarts printer workers. Never fetch into their
    // ephemeral session directories or let a LAN-only session contact cloud.
}

""" + source[end:]
path.write_text(source)
print("Applied HA-managed credential provisioning patch.")
