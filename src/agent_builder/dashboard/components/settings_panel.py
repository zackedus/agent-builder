"""Settings and run-build panel for the dashboard."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_builder.config import get_settings
from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def _spawn_cli(cmd: list[str]) -> str:
    kwargs: dict[str, Any] = {"cwd": str(Path.cwd())}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    try:
        subprocess.Popen(cmd, **kwargs)  # noqa: S603
    except OSError as exc:
        return f"Gagal menjalankan: {exc}"
    return "Perintah dibuka di terminal terpisah."


def launch_cli_command(subcommand: str, *args: str) -> str:
    """Spawn ``agent-builder <subcommand>`` in a new console."""
    cmd = [sys.executable, "-m", "agent_builder.cli", subcommand, *args]
    return _spawn_cli(cmd)


def launch_build_in_terminal(prompt: str, *, budget: float | None = None) -> str:
    """Spawn ``agent-builder run`` in a new console (Windows) or background process."""
    prompt = prompt.strip()
    if not prompt:
        return "Prompt tidak boleh kosong."

    cmd = [sys.executable, "-m", "agent_builder.cli", "run", prompt]
    if budget is not None and budget > 0:
        cmd.extend(["--budget", str(budget)])
    message = _spawn_cli(cmd)
    return f"{message} Dashboard akan update otomatis (poll)."


def build_settings_dialog(
    store: DashboardStore,
    tokens: DashboardThemeTokens,
    *,
    on_close: Callable[[], None],
) -> Any:
    import flet as ft

    settings = get_settings()
    ws_path = store.workspace.root.resolve()
    status_msg = ft.Text("", size=12, color=tokens.on_surface)

    prompt_field = ft.TextField(
        label="Prompt build baru",
        hint_text='Contoh: "Buat expense tracker dengan Flet"',
        multiline=True,
        min_lines=2,
        max_lines=4,
        expand=True,
    )
    budget_field = ft.TextField(
        label="Budget USD (opsional)",
        value=str(settings.budget_usd or ""),
        width=160,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def run_build(_: Any) -> None:
        budget_val: float | None = None
        raw_budget = (budget_field.value or "").strip()
        if raw_budget:
            try:
                budget_val = float(raw_budget)
            except ValueError:
                status_msg.value = "Budget harus angka."
                status_msg.update()
                return
        message = launch_build_in_terminal(prompt_field.value or "", budget=budget_val)
        status_msg.value = message
        status_msg.update()

    if settings.anthropic_configured():
        anthropic = "[OK] API key terdeteksi"
    else:
        anthropic = "[!] Set ANTHROPIC_API_KEY di .env"

    if settings.budget_usd:
        budget_line = f"Budget default: ${settings.budget_usd:.2f}"
    else:
        budget_line = "Budget default: (tidak diset)"

    info_lines = [
        f"Workspace: {ws_path}",
        budget_line,
        f"Log level: {settings.log_level}",
        f"sandbox: {settings.sandbox_layer}",
        f"Anthropic: {anthropic}",
        "",
        "Tab Kontrol: run / resume / doctor dari UI.",
        "Atau gunakan terminal jika perlu log penuh.",
        "",
        "Env: salin .env.example → .env",
    ]

    return ft.AlertDialog(
        modal=True,
        title=ft.Text("Pengaturan & menjalankan build"),
        content=ft.Container(
            width=520,
            content=ft.Column(
                [
                    ft.Text("\n".join(info_lines), size=12, selectable=True),
                    ft.Divider(),
                    ft.Text("Jalankan build dari dashboard", size=13, weight=ft.FontWeight.W_600),
                    prompt_field,
                    ft.Row([budget_field]),
                    status_msg,
                ],
                tight=True,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
        actions=[
            ft.TextButton("Tutup", on_click=lambda _: on_close()),
            ft.ElevatedButton("Jalankan build", icon=ft.Icons.PLAY_ARROW, on_click=run_build),
        ],
    )
