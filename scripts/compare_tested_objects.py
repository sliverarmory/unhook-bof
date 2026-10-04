#!/usr/bin/env python3
"""Require the release archive to contain the exact BOF bytes that passed E2E."""

import argparse
import hashlib
import pathlib

from validate_archive import read_archive


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--tested-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    archive = read_archive(args.archive)
    for name in ("unhook.x64.o", "unhook.x86.o"):
        matches = list(args.tested_dir.rglob(name))
        if len(matches) != 1:
            raise ValueError(f"expected exactly one tested {name}; found {len(matches)}")
        tested = matches[0].read_bytes()
        if archive[name] != tested:
            raise ValueError(f"{name} differs from the successful E2E run artifact")
        print(f"{name}: tested and packaged SHA-256 {hashlib.sha256(tested).hexdigest()}")


if __name__ == "__main__":
    main()
