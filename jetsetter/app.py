"""jetsetter — Interactive TUI for NVIDIA SDK components on Jetson."""
from __future__ import annotations

import asyncio
import subprocess
from typing import List, Optional, Tuple

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Label,
    Log,
    Markdown,
    Rule,
    Static,
)

from .components import COMPONENTS, GROUP_ORDER, Component
from .installer import install_components
from .repo import l4t_version


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_info() -> Tuple[Optional[str], Optional[Tuple[int, int]]]:
    """Returns (model_str, l4t_tuple) — run in a thread."""
    model = None
    try:
        with open("/proc/device-tree/model") as f:
            model = f.read().rstrip("\x00")
    except FileNotFoundError:
        pass
    return model, l4t_version()


def _l4t_str(ver: Optional[Tuple[int, int]]) -> str:
    if ver is None:
        return "unknown"
    return f"{ver[0]}.{ver[1]}"


def _ver_ok(comp: Component, ver: Optional[Tuple[int, int]]) -> bool:
    """True if board L4T meets component minimum."""
    if comp.min_l4t is None or ver is None:
        return True
    req = tuple(int(x) for x in comp.min_l4t.split("."))
    return ver >= req  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# Widgets
# ─────────────────────────────────────────────────────────────────────────────

class BoardPanel(Static):
    def __init__(self) -> None:
        self._model: Optional[str] = None
        self._ver: Optional[Tuple[int, int]] = None
        super().__init__()

    def update_info(self, model: Optional[str], ver: Optional[Tuple[int, int]]) -> None:
        self._model = model
        self._ver = ver
        self.refresh()

    def render(self) -> str:
        if self._model is None:
            return "[yellow]⚠  Board not detected — demo mode[/]\n[dim]No installs will run[/]"
        return (
            f"[bold green]✔  {self._model}[/]\n"
            f"[dim]L4T:[/] R{_l4t_str(self._ver)}   "
            f"[dim]Install method:[/] apt (NVIDIA repo)"
        )


class ComponentRow(Horizontal):
    def __init__(self, comp: Component, ver: Optional[Tuple[int, int]]) -> None:
        self.comp = comp
        self._ver = ver
        self._ok = _ver_ok(comp, ver)
        super().__init__(id=f"row-{comp.id}", classes="comp-row")

    def compose(self) -> ComposeResult:
        label = self.comp.name
        if not self._ok:
            label += f" [dim](needs L4T ≥ {self.comp.min_l4t})[/]"
        yield Checkbox(label, value=False, id=f"chk-{self.comp.id}", disabled=not self._ok)
        yield Label(self.comp.description, classes="comp-desc")

    @property
    def is_checked(self) -> bool:
        return self.query_one(Checkbox).value  # type: ignore


class GroupHeader(Static):
    def __init__(self, name: str) -> None:
        super().__init__(f"\n[bold cyan]{name}[/]", classes="group-header")


# ─────────────────────────────────────────────────────────────────────────────
# Install screen
# ─────────────────────────────────────────────────────────────────────────────

class InstallScreen(Screen):
    BINDINGS = [Binding("q", "app.pop_screen", "Back")]

    def __init__(self, board: Optional[str], ver: Optional[Tuple[int, int]], selected: List[Component]) -> None:
        self.board = board
        self.ver = ver
        self.selected = selected
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Log(id="install-log", highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(Log)
        self.run_worker(self._run(log), exclusive=True, thread=False)

    async def _run(self, log: Log) -> None:
        log.write_line("[bold cyan]jetsetter install started[/]")
        log.write_line("")
        if self.board is None:
            log.write_line("[yellow]⚠  No board detected — dry run[/]")
            for c in self.selected:
                log.write_line(f"  would install: {c.name} → {', '.join(c.packages)}")
            log.write_line("")
            log.write_line("[yellow]Dry run complete. Press Q to go back.[/]")
            return

        async for line in install_components(self.selected):
            log.write_line(line)

        log.write_line("")
        log.write_line("[bold green]✔  Done. Press Q to go back.[/]")


# ─────────────────────────────────────────────────────────────────────────────
# Summary screen
# ─────────────────────────────────────────────────────────────────────────────

class SummaryScreen(Screen):
    BINDINGS = [
        Binding("i", "install", "Install"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, board: Optional[str], ver: Optional[Tuple[int, int]], selected: List[Component]) -> None:
        self.board = board
        self.ver = ver
        self.selected = selected
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        lines = ["# Install Summary\n"]
        if self.board:
            lines.append(f"**Board:** {self.board}  ")
            lines.append(f"**L4T:** R{_l4t_str(self.ver)}\n")
        else:
            lines.append("**Board:** Not detected (dry run)\n")

        # Count packages
        all_pkgs = list(dict.fromkeys(
            pkg for c in self.selected for pkg in c.packages + c.recommends
        ))
        lines.append(f"**Components:** {len(self.selected)}   **Packages:** {len(all_pkgs)}\n")

        # Group by group
        groups: dict[str, List[Component]] = {}
        for c in self.selected:
            groups.setdefault(c.group, []).append(c)

        for group, comps in groups.items():
            lines.append(f"## {group}")
            for c in comps:
                lines.append(f"- **{c.name}**")
                lines.append(f"  `{' '.join(c.packages)}`")
                if c.notes:
                    lines.append(f"  _{c.notes}_")

        lines.append("\n---")
        lines.append("Press **I** to install or **Esc** to go back.")
        yield ScrollableContainer(Markdown("\n".join(lines)))
        yield Footer()

    def action_install(self) -> None:
        self.app.push_screen(InstallScreen(self.board, self.ver, self.selected))


# ─────────────────────────────────────────────────────────────────────────────
# Main screen
# ─────────────────────────────────────────────────────────────────────────────

class MainScreen(Screen):
    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
        Binding("a", "select_all", "All"),
        Binding("n", "select_none", "None"),
        Binding("enter", "review", "Review & Install"),
    ]

    def __init__(self) -> None:
        self._board: Optional[str] = None
        self._ver: Optional[Tuple[int, int]] = None
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical():
            yield BoardPanel()
            yield Static("[bold]Select SDK components to install:[/]\n", classes="section-label")
            with ScrollableContainer(id="comp-list"):
                pass
            with Horizontal(id="action-bar"):
                yield Button("Review & Install →", id="btn-review", variant="primary")
                yield Button("Select All",         id="btn-all",    variant="default")
                yield Button("Clear",              id="btn-none",   variant="default")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._init(), exclusive=False, thread=False)

    async def _init(self) -> None:
        """Detect board and populate component list in parallel."""
        board_task = asyncio.create_task(asyncio.to_thread(_detect_info))
        rows_task  = asyncio.create_task(self._populate())
        (self._board, self._ver), _ = await asyncio.gather(board_task, rows_task)

        panel = self.query_one(BoardPanel)
        panel.update_info(self._board, self._ver)

    async def _populate(self) -> None:
        """Mount group headers + component rows."""
        container = self.query_one("#comp-list")

        # Order components by GROUP_ORDER, then alphabetically within group
        ordered: dict[str, List[Component]] = {g: [] for g in GROUP_ORDER}
        for comp in COMPONENTS:
            ordered.setdefault(comp.group, []).append(comp)

        for group in GROUP_ORDER:
            comps = ordered.get(group, [])
            if not comps:
                continue
            await container.mount(GroupHeader(group))
            for comp in comps:
                await container.mount(ComponentRow(comp, self._ver))

    def _selected(self) -> List[Component]:
        return [r.comp for r in self.query(ComponentRow) if r.is_checked]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-review":
            self.action_review()
        elif event.button.id == "btn-all":
            self.action_select_all()
        elif event.button.id == "btn-none":
            self.action_select_none()

    def action_select_all(self) -> None:
        for chk in self.query(Checkbox):
            if not chk.disabled:
                chk.value = True

    def action_select_none(self) -> None:
        for chk in self.query(Checkbox):
            chk.value = False

    def action_review(self) -> None:
        selected = self._selected()
        if not selected:
            self.notify("Select at least one component.", severity="warning")
            return
        self.app.push_screen(SummaryScreen(self._board, self._ver, selected))


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
Screen { background: $surface; }

BoardPanel {
    height: 3;
    padding: 0 2;
    background: $panel;
    border-bottom: solid $primary;
}

.section-label { padding: 1 2 0 2; }

#comp-list {
    height: 1fr;
    padding: 0 2;
}

.group-header {
    color: $accent;
    padding: 0 0 0 1;
}

.comp-row {
    height: 3;
    align: left middle;
}

.comp-row Checkbox { width: 38; }

.comp-desc {
    color: $text-muted;
    padding: 0 2;
}

#action-bar {
    height: 5;
    padding: 1 2;
    align: left middle;
    background: $panel;
    border-top: solid $primary;
}

#action-bar Button { margin-right: 2; }

#install-log {
    height: 1fr;
    padding: 1 2;
}
"""


class JetsonSetterApp(App):
    CSS = CSS
    TITLE = "jetsetter"
    SUB_TITLE = "NVIDIA Component Installer"

    def on_mount(self) -> None:
        self.push_screen(MainScreen())


def main() -> None:
    JetsonSetterApp().run()


if __name__ == "__main__":
    main()
