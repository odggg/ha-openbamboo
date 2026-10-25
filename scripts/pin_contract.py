"""Extract the reviewed upstream interface from preserved source fixtures.

This is a maintainer operation, never run automatically during installation.
Review upstream changes before regenerating the contract.
"""
import ast
import hashlib
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]

def method(path, classname, name):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == classname)
    node = next(node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    start = min([node.lineno] + [item.lineno for item in node.decorator_list])
    segment = "".join(source.splitlines(keepends=True)[start-1:node.end_lineno])
    return hashlib.sha256(textwrap.dedent(segment).encode()).hexdigest()

contracts = {
    "BambuClient.connect": method(ROOT / "tests/fixtures/upstream_bambu_client.py.txt", "BambuClient", "connect"),
    "BambuClient.try_connection": method(ROOT / "tests/fixtures/upstream_bambu_client.py.txt", "BambuClient", "try_connection"),
    "PrintFun.mqtt_signature_required": method(ROOT / "tests/fixtures/upstream_print_fun.py.txt", "PrintFun", "mqtt_signature_required"),
}
(ROOT / "custom_components/bambu_open_network/upstream_contract.json").write_text(
    json.dumps(contracts, indent=2) + "\n", encoding="utf-8")
