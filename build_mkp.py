#!/usr/bin/env python3
"""Build the Hetzner Storage Box CheckMK extension package (MKP).

Run from the repository root:

    python3 build_mkp.py

Produces hetzner_storagebox-<VERSION>.mkp in the current directory.

The MKP format is a gzipped tar containing:
  info                   - legacy Python-repr metadata (still read by some CMK versions)
  info.json              - JSON metadata (primary, required by CMK 2.3+)
  cmk_addons_plugins.tar - inner tar with all plugin files under hetzner_storagebox/
"""

import io
import json
import os
import stat
import tarfile
import time

PACKAGE_NAME = "hetzner_storagebox"
VERSION = "0.3.0"
OUTPUT = f"{PACKAGE_NAME}-{VERSION}.mkp"

# (source path relative to repo root, archive path inside cmk_addons_plugins.tar)
ADDON_FILES: list[tuple[str, str]] = [
    ("cmk_addons/plugins/hetzner_storagebox/agent_based/hetzner_storagebox.py",
     "hetzner_storagebox/agent_based/hetzner_storagebox.py"),
    ("cmk_addons/plugins/hetzner_storagebox/graphing/hetzner_storagebox.py",
     "hetzner_storagebox/graphing/hetzner_storagebox.py"),
    ("cmk_addons/plugins/hetzner_storagebox/libexec/agent_hetzner_storagebox",
     "hetzner_storagebox/libexec/agent_hetzner_storagebox"),
    ("cmk_addons/plugins/hetzner_storagebox/rulesets/hetzner_storagebox.py",
     "hetzner_storagebox/rulesets/hetzner_storagebox.py"),
    ("cmk_addons/plugins/hetzner_storagebox/server_side_calls/hetzner_storagebox.py",
     "hetzner_storagebox/server_side_calls/hetzner_storagebox.py"),
]

INFO: dict = {
    "title": "Hetzner Storage Box Monitoring",
    "name": PACKAGE_NAME,
    "description": (
        'Checkmk special agent for monitoring Hetzner Storage Boxes via the Hetzner Console API.\n'
        'Fork of 47k/checkmk-hetzner-storagebox by Manuel "Overlord" Michalski '
        "(original author through v0.1.3).\n"
        "\n"
        f"Version {VERSION}:\n"
        "- Fixed Checkmk 2.5 compatibility: the result-cache rule editor used a "
        "private legacy form-spec bridge API that was removed in 2.5, which broke "
        "loading the ruleset entirely. Replaced with a native CascadingSingleChoice; "
        "old stored rules migrate automatically.\n"
    ),
    "version": VERSION,
    "version.packaged": "build_mkp.py",
    "version.min_required": "2.4.0",
    "version.usable_until": None,
    "author": "Tony Boston (tboston@csitlab.org)",
    "download_url": "https://github.com/TonyBostonTB/checkmk-hetzner-storagebox",
    "files": {
        "cmk_addons_plugins": [arc for _, arc in ADDON_FILES],
    },
}

# Permissions for the agent script: rwxr-xr-x
_EXEC_MODE = (
    stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
)


def _add_file(tar: tarfile.TarFile, src: str, arc: str) -> None:
    ti = tar.gettarinfo(src, arcname=arc)
    if "libexec" in arc:
        ti.mode = _EXEC_MODE
    with open(src, "rb") as fh:
        tar.addfile(ti, fh)


def _build_inner_tar(files: list[tuple[str, str]]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as t:
        for src, arc in files:
            if not os.path.exists(src):
                print(f"  WARNING: {src} not found, skipping")
                continue
            _add_file(t, src, arc)
            print(f"  + {arc}")
    return buf.getvalue()


def _bytes_entry(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    ti = tarfile.TarInfo(name=name)
    ti.size = len(data)
    ti.mtime = int(time.time())
    tar.addfile(ti, io.BytesIO(data))


def main() -> None:
    print(f"Building {OUTPUT} ...")

    addon_bytes = _build_inner_tar(ADDON_FILES)

    info_json = json.dumps(INFO, indent=2, ensure_ascii=False).encode()
    info_legacy = repr(INFO).encode()

    with tarfile.open(OUTPUT, "w:gz") as outer:
        _bytes_entry(outer, "info", info_legacy)
        _bytes_entry(outer, "info.json", info_json)
        _bytes_entry(outer, "cmk_addons_plugins.tar", addon_bytes)

    size_kb = os.path.getsize(OUTPUT) / 1024
    print(f"\nDone: {OUTPUT} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
