"""Keep test scratch inside this checkout; normalize Windows-only 0700 ACL behavior."""
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TEST_TMP = ROOT / ".test-tmp"
TEST_TMP.mkdir(exist_ok=True)
tempfile.tempdir = str(TEST_TMP)
if sys.platform == "win32":
    # Python's Windows 0700 special DACL does not grant this execution
    # environment's restricted token access. Production targets Linux only.
    original_mkdir = os.mkdir
    def test_mkdir(path, mode=0o777, *, dir_fd=None):
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(TEST_TMP.resolve()):
            return original_mkdir(path, mode, dir_fd=dir_fd)
        return original_mkdir(path, 0o777, dir_fd=dir_fd)
    os.mkdir = test_mkdir
