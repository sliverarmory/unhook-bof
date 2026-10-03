#!/usr/bin/env bash
set -euo pipefail

if ! command -v x86_64-w64-mingw32-gcc >/dev/null ||
   ! command -v i686-w64-mingw32-gcc >/dev/null; then
  # The reusable workflow's planner runs on ubuntu-24.04.
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends \
    gcc-mingw-w64-x86-64 gcc-mingw-w64-i686
fi

x86_64-w64-mingw32-gcc --version
i686-w64-mingw32-gcc --version

make clean
make

test -s unhook.x64.o
test -s unhook.x86.o
