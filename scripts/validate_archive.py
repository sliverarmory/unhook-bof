#!/usr/bin/env python3
"""Validate the exact Unhook BOF archive contract before signing or release."""

import argparse
import json
import pathlib
import struct
import tarfile


ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = {"extension.json", "unhook.x64.o", "unhook.x86.o", "LICENSE"}
MACHINES = {"unhook.x64.o": 0x8664, "unhook.x86.o": 0x014C}


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def has_entrypoint(data: bytes, name: str) -> bool:
    require(len(data) >= 20, f"{name}: truncated COFF header")
    symbols_offset, count = struct.unpack_from("<II", data, 8)
    end = symbols_offset + count * 18
    require(0 < count < 100000 and end + 4 <= len(data), f"{name}: invalid COFF symbol table")
    string_size = struct.unpack_from("<I", data, end)[0]
    require(string_size >= 4 and end + string_size <= len(data), f"{name}: invalid COFF string table")
    index = 0
    while index < count:
        item = data[symbols_offset + 18 * index : symbols_offset + 18 * (index + 1)]
        raw_name = item[:8]
        if raw_name[:4] == b"\0\0\0\0":
            offset = struct.unpack_from("<I", raw_name, 4)[0]
            start = end + offset
            require(4 <= offset < string_size, f"{name}: invalid symbol string offset")
            symbol = data[start : end + string_size].split(b"\0", 1)[0]
        else:
            symbol = raw_name.split(b"\0", 1)[0]
        storage_class = item[16]
        aux_count = item[17]
        if storage_class == 2 and symbol in (b"go", b"_go"):
            return True
        index += 1 + aux_count
    return False


def read_archive(path: pathlib.Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            require(member.isfile(), f"unexpected non-file entry: {member.name}")
            require(member.name.startswith("./") and member.name[2:] in NAMES,
                    f"unexpected archive member: {member.name}")
            name = member.name[2:]
            require(name not in result, f"duplicate archive member: {member.name}")
            extracted = archive.extractfile(member)
            require(extracted is not None, f"cannot read archive member: {member.name}")
            result[name] = extracted.read()
    require(set(result) == NAMES, f"archive members differ from {sorted(NAMES)}")
    return result


def validate(path: pathlib.Path, version: str) -> dict[str, bytes]:
    entries = read_archive(path)
    source = json.loads((ROOT / "extension.json").read_text(encoding="utf-8"))
    require(source.get("version") == "0.0.0", "source manifest must retain version placeholder 0.0.0")
    require(source.get("bof_executor") == "reflektor", "BOF must explicitly select reflektor")
    require("depends_on" not in source, "coff-loader dependency must be absent")
    require(source.get("command_name") == "unhook-bof", "command_name changed")
    require(source.get("repo_url") == "https://github.com/sliverarmory/unhook-bof", "repo_url changed")
    require(source.get("entrypoint") == "go", "entrypoint changed")
    require(source.get("files") == [
        {"os": "windows", "arch": "amd64", "path": "unhook.x64.o"},
        {"os": "windows", "arch": "386", "path": "unhook.x86.o"},
    ], "BOF targets changed")
    source["version"] = version
    actual = json.loads(entries["extension.json"].decode("utf-8"))
    require(actual == source, "archived manifest differs from version-stamped source manifest")
    require(entries["LICENSE"] == (ROOT / "LICENSE").read_bytes(), "LICENSE differs from source")
    for name, machine in MACHINES.items():
        data = entries[name]
        require(len(data) >= 20 and struct.unpack_from("<H", data)[0] == machine,
                f"{name}: wrong COFF target architecture")
        require(has_entrypoint(data, name), f"{name}: missing external go entrypoint")
    print(f"Archive valid: {path} ({version}; Windows amd64 and 386)")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    validate(args.archive, args.version)


if __name__ == "__main__":
    main()
