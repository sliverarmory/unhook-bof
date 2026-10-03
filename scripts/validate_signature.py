#!/usr/bin/env python3
"""Verify Minisign and its trusted manifest against downloaded package bytes."""

import argparse
import base64
import pathlib
import subprocess
import tarfile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--signature", type=pathlib.Path, required=True)
    parser.add_argument("--public-key", required=True)
    args = parser.parse_args()
    subprocess.run(
        ["minisign", "-Vm", str(args.archive), "-x", str(args.signature), "-P", args.public_key],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    lines = args.signature.read_text(encoding="ascii").splitlines()
    trusted = [line.removeprefix("trusted comment: ") for line in lines
               if line.startswith("trusted comment: ")]
    if len(trusted) != 1:
        raise ValueError("signature must have exactly one trusted comment")
    manifest = base64.b64decode(trusted[0], validate=True)
    with tarfile.open(args.archive, "r:gz") as archive:
        members = [item for item in archive if item.name == "./extension.json" and item.isfile()]
        if len(members) != 1:
            raise ValueError("archive must have exactly one root extension.json")
        item = archive.extractfile(members[0])
        if item is None:
            raise ValueError("cannot read archived extension.json")
        archived_manifest = item.read()
    if manifest != archived_manifest:
        raise ValueError("signed trusted manifest differs from archived manifest bytes")
    print("Minisign and exact trusted manifest bytes verified")


if __name__ == "__main__":
    main()
