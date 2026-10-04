#!/usr/bin/env python3
"""Build unhook BOFs from source and make a reproducible Armory archive."""

import argparse
import gzip
import io
import json
import pathlib
import re
import subprocess
import tarfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE_FILES = ("extension.json", "unhook.x64.o", "unhook.x86.o", "LICENSE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", args.version):
        parser.error("version must be a strict vMAJOR.MINOR.PATCH tag")

    source = json.loads((ROOT / "extension.json").read_text(encoding="utf-8"))
    if source.get("version") != "0.0.0":
        parser.error("source extension.json must retain its 0.0.0 placeholder")

    # This is the same source build used by the BOF end-to-end workflow.
    subprocess.run(["bash", "scripts/prepare-sliver-bof-e2e.sh"], cwd=ROOT, check=True)

    source["version"] = args.version
    manifest = (json.dumps(source, indent=4, ensure_ascii=False) + "\n").encode("utf-8")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name in PACKAGE_FILES:
            data = manifest if name == "extension.json" else (ROOT / name).read_bytes()
            if not data:
                raise ValueError(f"empty package file: {name}")
            # Sliver's package validator expects canonical root entries with ./.
            info = tarfile.TarInfo(f"./{name}")
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))

    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(tar_bytes.getvalue())
    print(f"Packaged {output} ({args.version})")


if __name__ == "__main__":
    main()
