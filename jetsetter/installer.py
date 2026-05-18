"""Parallel apt installer for SDK components."""
from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator, List

from .components import Component
from .repo import ensure_nvidia_repo


# Max parallel apt-get install workers
# (apt itself serialises writes to dpkg, but fetching can be parallel)
_MAX_WORKERS = int(os.environ.get("JETSETTER_JOBS", 4))


async def install_components(
    components: List[Component],
) -> AsyncIterator[str]:
    """
    Yield log lines while installing selected SDK components.

    Parallelism:
      Step 1 — repo setup (serial prerequisite)
      Step 2 — parallel apt-get install, one worker per component group
               (groups are safe to parallelise; within a group packages
                go in one apt call to respect dependency order)
      Step 3 — post-install checks in parallel
    """

    # ── Step 1: ensure NVIDIA repo ────────────────────────────────────────────
    yield "── Step 1: Checking NVIDIA apt repository ───────────────"
    async for line in ensure_nvidia_repo():
        yield line

    # ── Step 2: parallel group installs ───────────────────────────────────────
    yield ""
    yield f"── Step 2: Installing components (parallel groups, {_MAX_WORKERS} workers) ──"

    # Group components by their group field
    groups: dict[str, List[Component]] = {}
    for comp in components:
        groups.setdefault(comp.group, []).append(comp)

    queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()
    sem = asyncio.Semaphore(_MAX_WORKERS)

    async def _install_group(group: str, comps: List[Component]) -> None:
        async with sem:
            pkgs: List[str] = []
            for c in comps:
                pkgs.extend(c.packages)
                pkgs.extend(c.recommends)
            pkgs = list(dict.fromkeys(pkgs))  # dedup, preserve order

            await queue.put((group, f"  [bold]▶ [{group}][/] installing {len(pkgs)} packages..."))

            cmd = ["apt-get", "install", "-y", "--no-install-recommends"] + pkgs
            if os.geteuid() != 0:
                cmd = ["sudo"] + cmd

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip()
                await queue.put((group, f"  [{group}] {line}"))
            await proc.wait()

            rc = proc.returncode
            if rc == 0:
                await queue.put((group, f"  [green]✔ [{group}] done[/]"))
            else:
                await queue.put((group, f"  [red]✗ [{group}] apt exited {rc}[/]"))

        await queue.put((group, None))  # sentinel

    workers = [
        asyncio.create_task(_install_group(g, c))
        for g, c in groups.items()
    ]
    total = len(workers)
    finished = 0

    while finished < total:
        group, line = await queue.get()
        if line is None:
            finished += 1
        else:
            yield line

    await asyncio.gather(*workers)

    # ── Step 3: parallel post-install checks ──────────────────────────────────
    yield ""
    yield "── Step 3: Post-install checks ──────────────────────────"

    check_tasks = [
        asyncio.create_task(_check_component(c))
        for c in components
    ]
    results = await asyncio.gather(*check_tasks)

    for comp, (ok, detail) in zip(components, results):
        icon = "[green]✔[/]" if ok else "[yellow]?[/]"
        yield f"  {icon} {comp.name}: {detail}"

    yield ""
    yield "[bold green]✔  Install complete![/]"
    yield ""

    # Print any notes
    for comp in components:
        if comp.notes:
            yield f"[dim]{comp.name}:[/] {comp.notes}"


async def _check_component(comp: Component) -> tuple[bool, str]:
    """Quick dpkg check that the first package is installed."""
    if not comp.packages:
        return True, "no packages"
    pkg = comp.packages[0]
    proc = await asyncio.create_subprocess_exec(
        "dpkg", "-s", pkg,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    if proc.returncode == 0:
        return True, f"{pkg} installed"
    return False, f"{pkg} not found — check apt output above"
