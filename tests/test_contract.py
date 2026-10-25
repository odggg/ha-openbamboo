import support
"""Validate inspection hashes against functions extracted from actual upstream source."""
import ast
import importlib
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest

ROOT = Path(__file__).resolve().parents[1]
if "custom_components.bambu_open_network" not in sys.modules:
    pkg = ModuleType("custom_components.bambu_open_network")
    pkg.__path__ = [str(ROOT / "custom_components/bambu_open_network")]
    sys.modules.setdefault("custom_components", ModuleType("custom_components"))
    sys.modules["custom_components.bambu_open_network"] = pkg
patch = importlib.import_module("custom_components.bambu_open_network.patch")

def extract(path, classname, names):
    source = path.read_text()
    cls = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef)
               and node.name == classname)
    result = "class " + classname + ":\n"
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            result += "".join(source.splitlines(keepends=True)[start-1:node.end_lineno]) + "\n"
    return result

class ContractTests(unittest.TestCase):
    def test_reviewed_upstream_methods_match_inspect_contract(self):
        source = extract(ROOT / "tests/fixtures/upstream_bambu_client.py.txt", "BambuClient",
                         {"connect", "try_connection"})
        source += extract(ROOT / "tests/fixtures/upstream_print_fun.py.txt", "PrintFun",
                          {"mqtt_signature_required"})
        with tempfile.TemporaryDirectory() as tmp:
            filename = Path(tmp) / "reviewed_upstream.py"
            filename.write_text(source)
            spec = importlib.util.spec_from_file_location("reviewed_upstream", filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            patch.check_contract(module, module)
            module.BambuClient.connect = self.test_reviewed_upstream_methods_match_inspect_contract
            with self.assertRaises(patch.IncompatibleUpstream):
                patch.check_contract(module, module)
