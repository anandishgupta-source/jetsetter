"""NVIDIA apt repository setup — adds CUDA and JetPack repos if missing."""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import AsyncIterator, Optional, Tuple


# Detect L4T version and pick the right repo key / URL
_REPO_KEYRING = "/usr/share/keyrings/nvidia-jetson-archive-keyring.gpg"
_SOURCES_FILE = "/etc/apt/sources.list.d/nvidia-l4t-apt-source.list"


def l4t_version() -> Optional[Tuple[int, int]]:
    """Return (major, minor) L4T version or None."""
    try:
        with open("/etc/nv_tegra_release") as f:
            m = re.search(r"R(\d+).*REVISION: (\d+)", f.read())
            if m:
                return int(m.group(1)), int(m.group(2))
    except FileNotFoundError:
        pass
    return None


async def ensure_nvidia_repo() -> AsyncIterator[str]:
    """
    Ensure NVIDIA L4T / CUDA apt repos are configured.
    Idempotent — skips if already set up.
    """
    if Path(_SOURCES_FILE).exists():
        yield "[dim]  NVIDIA apt repo already configured[/]"
        return

    ver = l4t_version()
    if ver is None:
        yield "[yellow]  ⚠ Could not detect L4T version — skipping repo setup[/]"
        return

    major, minor = ver
    yield f"  Detected L4T R{major}.{minor} — adding NVIDIA apt repo..."

    # Add NVIDIA keyring
    async for line in _run_cmd([
        "bash", "-c",
        "apt-key adv --fetch-keys https://repo.download.nvidia.com/jetson/jetson-ota-public.asc"
    ], sudo=True):
        yield f"  [dim]{line}[/]"

    # Write sources list
    repo_url = f"https://repo.download.nvidia.com/jetson/common r{major}.{minor} main"
    t194_url = f"https://repo.download.nvidia.com/jetson/t194 r{major}.{minor} main"   # Xavier / Orin

    sources = f"deb {repo_url}\ndeb {t194_url}\n"
    write_cmd = ["bash", "-c", f"echo '{sources}' > {_SOURCES_FILE}"]
    async for line in _run_cmd(write_cmd, sudo=True):
        yield f"  [dim]{line}[/]"

    yield "  Running apt-get update..."
    async for line in _run_cmd(["apt-get", "update", "-q"], sudo=True):
        yield f"  [dim]{line}[/]"

    yield "[green]  ✔ NVIDIA apt repo ready[/]"


async def _run_cmd(cmd, sudo: bool = False) -> AsyncIterator[str]:
    if sudo and os.geteuid() != 0:
        cmd = ["sudo"] + cmd
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    assert proc.stdout
    async for raw in proc.stdout:
        yield raw.decode(errors="replace").rstrip()
    await proc.wait()
