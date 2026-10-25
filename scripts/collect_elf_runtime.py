"""Collect the exact ELF dependency closure without executing the target binary."""
from __future__ import annotations
from collections import deque
import os
from pathlib import Path
import shutil
import sys
from elftools.elf.elffile import ELFFile

def collect(worker: Path, output: Path):
    libdir = output / "lib"
    libdir.mkdir(parents=True, exist_ok=True)
    pending = deque([worker.resolve()])
    inspected = set()
    copied = {}
    loader = None
    count = 0
    while pending:
        binary = pending.popleft()
        real = binary.resolve(strict=True)
        if real in inspected:
            continue
        inspected.add(real)
        with real.open("rb") as stream:
            elf = ELFFile(stream)
            search = []
            needed = []
            for segment in elf.iter_segments():
                if segment.header.p_type == "PT_INTERP":
                    interpreter = Path(segment.get_interp_name())
                    if loader is None:
                        shutil.copyfile(interpreter, output / "loader")
                        loader = interpreter
                        pending.append(interpreter)
            for section in elf.iter_sections():
                if section.header.sh_type != "SHT_DYNAMIC":
                    continue
                for tag in section.iter_tags():
                    kind = tag.entry.d_tag
                    if kind == "DT_NEEDED":
                        needed.append(tag.needed)
                    elif kind in ("DT_RUNPATH", "DT_RPATH"):
                        raw = tag.runpath if kind == "DT_RUNPATH" else tag.rpath
                        for entry in raw.split(":"):
                            entry = entry.replace("${ORIGIN}", str(real.parent)).replace(
                                "$ORIGIN", str(real.parent))
                            if entry:
                                search.append(Path(entry))
        search += [Path("/lib"), Path("/usr/lib"), Path("/usr/local/lib")]
        for name in needed:
            found = next((directory / name for directory in search
                          if (directory / name).is_file()), None)
            if found is None:
                raise RuntimeError(f"Unresolved ELF dependency {name} from {binary.name}")
            resolved = found.resolve(strict=True)
            if name in copied and copied[name] != resolved:
                raise RuntimeError(f"Conflicting libraries named {name}")
            if name not in copied:
                shutil.copyfile(resolved, libdir / name)
                copied[name] = resolved
                count += 1
            pending.append(resolved)
    if loader is None or not (libdir / "libbambu_networking.so").is_file():
        raise RuntimeError("Missing musl loader or Open Bamboo library")
    (output / "loader").chmod(0o755)
    print(f"Collected loader and {count} shared libraries")

if __name__ == "__main__":
    collect(Path(sys.argv[1]), Path(sys.argv[2]))
