"""Tab — Kontrol: run, resume, doctor, pengaturan (ganti CLI utama)."""

from __future__ import annotations

from typing import Any

from agent_builder.config import get_settings
from agent_builder.core.event_bus import EventBus
from agent_builder.dashboard.components.settings_panel import (
    launch_build_in_terminal,
    launch_cli_command,
)
from agent_builder.dashboard.services.doctor import run_doctor_checks
from agent_builder.dashboard.services.job_runner import resume_build, start_new_build
from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens


def build_control_view(
    store: DashboardStore,
    tokens: DashboardThemeTokens,
    page: Any,
) -> Any:
    import flet as ft

    settings = get_settings()
    session = store.session
    status_msg = ft.Text(store.job_message or "Siap.", size=13, color=tokens.on_surface)
    progress = ft.ProgressRing(visible=store.job_running, width=22, height=22)

    prompt_field = ft.TextField(
        label="Prompt aplikasi baru",
        hint_text='Contoh: "Expense tracker Flet dengan chart"',
        multiline=True,
        min_lines=2,
        max_lines=5,
        expand=True,
        disabled=store.job_running,
    )
    budget_field = ft.TextField(
        label="Budget USD",
        value=str(settings.budget_usd or ""),
        width=140,
        disabled=store.job_running,
    )

    session_info = ft.Text(_session_summary(session), size=12, selectable=True)

    doctor_column = ft.Column(spacing=4)

    def refresh_doctor() -> None:
        rows = run_doctor_checks(store.workspace, settings)
        doctor_column.controls = [
            ft.Text(
                f"{'✓' if row.ok else '✗'} {row.name}: {row.detail}",
                size=12,
                color="#059669" if row.ok else "#DC2626",
            )
            for row in rows
        ]
        if page:
            doctor_column.update()

    def _event_bus() -> EventBus:
        bus = EventBus(events_store=store.workspace.events_store())
        store.attach_event_bus(bus)
        return bus

    async def _run_job(coro: Any) -> None:
        store.set_job_running(True, "Menjalankan…")
        try:
            ok, message = await coro
            store.set_job_running(False, message, error=not ok)
            store.refresh()
            refresh_doctor()
        except Exception as exc:  # noqa: BLE001 — surface to UI
            store.set_job_running(False, f"Error: {exc}", error=True)

    def start_build_in_app(_: Any) -> None:
        budget_val = _parse_budget(budget_field.value)
        if budget_val is False:
            status_msg.value = "Budget harus angka valid."
            status_msg.update()
            return
        bus = _event_bus()

        async def _task() -> None:
            await _run_job(
                start_new_build(
                    store.workspace,
                    prompt_field.value or "",
                    budget_usd=budget_val if isinstance(budget_val, float) else None,
                    event_bus=bus,
                ),
            )

        page.run_task(_task)

    def resume_in_app(_: Any) -> None:
        bus = _event_bus()

        async def _task() -> None:
            await _run_job(resume_build(store.workspace, event_bus=bus))

        page.run_task(_task)

    def run_build_terminal(_: Any) -> None:
        budget_val = _parse_budget(budget_field.value)
        if budget_val is False:
            status_msg.value = "Budget harus angka valid."
            status_msg.update()
            return
        status_msg.value = launch_build_in_terminal(
            prompt_field.value or "",
            budget=budget_val if isinstance(budget_val, float) else None,
        )
        status_msg.update()

    def resume_terminal(_: Any) -> None:
        status_msg.value = launch_cli_command("resume")
        status_msg.update()

    def doctor_terminal(_: Any) -> None:
        status_msg.value = launch_cli_command("doctor")
        status_msg.update()

    can_resume = session is not None and not session.is_terminal()

    cfg_lines = [
        f"Workspace: {store.workspace.root.resolve()}",
        f"Log: {settings.log_level} · Sandbox: {settings.sandbox_layer}",
        "Ubah permanen via file .env di root project",
    ]

    view = ft.Column(
        [
            ft.Text("Kontrol", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([progress, status_msg], spacing=10),
            ft.Container(
                bgcolor=tokens.surface_variant,
                border_radius=8,
                padding=12,
                content=ft.Column(
                    [
                        ft.Text("Session", size=14, weight=ft.FontWeight.W_600),
                        session_info,
                    ],
                ),
            ),
            ft.Text("Build baru", size=14, weight=ft.FontWeight.W_600),
            prompt_field,
            ft.Row(
                [
                    budget_field,
                    ft.ElevatedButton(
                        "Mulai build",
                        icon=ft.Icons.PLAY_ARROW,
                        on_click=start_build_in_app,
                        disabled=store.job_running,
                    ),
                    ft.OutlinedButton(
                        "Terminal",
                        on_click=run_build_terminal,
                        disabled=store.job_running,
                    ),
                ],
                wrap=True,
            ),
            ft.Divider(),
            ft.Text("Lanjutkan / diagnosa", size=14, weight=ft.FontWeight.W_600),
            ft.Row(
                [
                    ft.ElevatedButton(
                        "Lanjutkan session",
                        icon=ft.Icons.REFRESH,
                        on_click=resume_in_app,
                        disabled=store.job_running or not can_resume,
                    ),
                    ft.OutlinedButton(
                        "Resume (terminal)",
                        on_click=resume_terminal,
                        disabled=store.job_running or not can_resume,
                    ),
                    ft.OutlinedButton(
                        "Doctor (terminal)",
                        on_click=doctor_terminal,
                        disabled=store.job_running,
                    ),
                    ft.TextButton(
                        "Refresh cek",
                        on_click=lambda _: refresh_doctor(),
                    ),
                ],
                wrap=True,
            ),
            ft.Container(
                bgcolor=tokens.surface_variant,
                border_radius=8,
                padding=12,
                content=ft.Column(
                    [
                        ft.Text("Environment check", size=13, weight=ft.FontWeight.W_600),
                        doctor_column,
                    ],
                ),
            ),
            ft.Text("\n".join(cfg_lines), size=11, color=tokens.on_surface, opacity=0.8),
        ],
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )

    refresh_doctor()
    return ft.Container(expand=True, padding=8, content=view)


def _session_summary(session: Any) -> str:
    if session is None:
        return "Belum ada session — mulai build baru di atas."
    prompt = (session.user_prompt or "")[:80]
    return (
        f"ID: {session.session_id[:12]}…\n"
        f"State: {session.current_state}\n"
        f"Task: {session.current_task or '—'}\n"
        f"Selesai: {len(session.completed_tasks)} · Gagal: {len(session.failed_tasks)}\n"
        f"Prompt: {prompt or '—'}"
    )


def _parse_budget(raw: str | None) -> float | None | bool:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return False
