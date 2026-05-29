"""Tab 4 — Session replay with timeline scrubber and play controls."""

from __future__ import annotations

from typing import Any

from agent_builder.dashboard.components.activity_feed import format_event_line
from agent_builder.dashboard.state.store import DashboardStore
from agent_builder.dashboard.theme import DashboardThemeTokens
from agent_builder.replay.player import JUMP_EVENT_TYPES, REPLAY_SPEEDS
from agent_builder.replay.time_format import replay_clock, replay_duration_clock


def build_replay_view(store: DashboardStore, tokens: DashboardThemeTokens) -> Any:
    import flet as ft

    events = store.events
    replayer = store.replayer
    position = replayer.position
    frame = replayer.frame()

    if not events:
        return ft.Container(
            expand=True,
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Replay", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Belum ada events — jalankan agent-builder run …",
                        italic=True,
                        size=13,
                    ),
                ],
            ),
        )

    max_pos = len(events)
    current_clock = replay_clock(events, position)
    end_clock = replay_duration_clock(events)

    def on_scrub(e: Any) -> None:
        store.set_replay_position(int(e.control.value))

    slider = ft.Slider(
        min=0,
        max=max_pos,
        value=position,
        divisions=max_pos if max_pos <= 200 else None,
        label="{value}",
        on_change=on_scrub,
        expand=True,
    )

    def toggle_play(_: Any) -> None:
        store.set_replay_playing(not store.replay_playing)

    play_icon = ft.Icons.PAUSE if store.replay_playing else ft.Icons.PLAY_ARROW
    play_label = "Pause" if store.replay_playing else "Play"

    def step_back(_: Any) -> None:
        store.set_replay_position(replayer.position - 1)

    def step_forward(_: Any) -> None:
        store.set_replay_position(replayer.position + 1)

    def jump_start(_: Any) -> None:
        store.set_replay_position(0)

    def jump_end(_: Any) -> None:
        store.set_replay_position(max_pos)

    speed_dropdown = ft.Dropdown(
        label="Speed",
        width=100,
        value=str(store.replay_speed),
        options=[ft.dropdown.Option(str(s), f"{s}x") for s in REPLAY_SPEEDS],
        on_change=lambda e: store.set_replay_speed(float(str(e.control.value))),
    )

    jump_type = ft.Dropdown(
        label="Jump to",
        width=180,
        options=[ft.dropdown.Option("", "—")]
        + [ft.dropdown.Option(name, name) for name, _ in JUMP_EVENT_TYPES],
    )

    def on_jump_type(_: Any) -> None:
        label = jump_type.value
        if not label:
            return
        for name, event_type in JUMP_EVENT_TYPES:
            if name == label:
                result = replayer.jump_to_next_event_type(event_type)
                if result is not None:
                    store.set_replay_position(replayer.position)
                break
        jump_type.value = ""

    jump_type.on_change = on_jump_type

    bookmark_dropdown = ft.Dropdown(
        label="Bookmarks",
        width=220,
        options=[ft.dropdown.Option(str(b.position), b.label) for b in replayer.bookmarks]
        or [ft.dropdown.Option("", "Tidak ada bookmark")],
    )

    def on_bookmark_jump(e: Any) -> None:
        raw = e.control.value
        if raw:
            store.set_replay_position(int(str(raw)))

    bookmark_dropdown.on_change = on_bookmark_jump

    state_label = str(frame.state.current_state)
    task_label = frame.state.current_task or "—"
    cost_label = f"${frame.cumulative_cost_usd:.4f}"

    event_line = "—"
    if frame.last_event is not None:
        event_line = format_event_line(frame.last_event)
    elif position > 0 and events:
        event_line = format_event_line(events[position - 1])

    bookmark_chips = ft.Row(
        [
            ft.TextButton(
                b.label,
                on_click=lambda _e, pos=b.position: store.set_replay_position(pos),
            )
            for b in replayer.bookmarks[:8]
        ],
        wrap=True,
        spacing=4,
    )

    controls = ft.Column(
        [
            ft.Text("Replay", size=18, weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    ft.IconButton(ft.Icons.SKIP_PREVIOUS, tooltip="Awal", on_click=jump_start),
                    ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Step back", on_click=step_back),
                    ft.ElevatedButton(play_label, icon=play_icon, on_click=toggle_play),
                    ft.IconButton(
                        ft.Icons.CHEVRON_RIGHT,
                        tooltip="Step forward",
                        on_click=step_forward,
                    ),
                    ft.IconButton(ft.Icons.SKIP_NEXT, tooltip="Akhir / live", on_click=jump_end),
                    speed_dropdown,
                    jump_type,
                    bookmark_dropdown,
                ],
                wrap=True,
                spacing=8,
            ),
            ft.Row(
                [
                    ft.Text(current_clock, size=12, width=48),
                    slider,
                    ft.Text(end_clock, size=12, width=48),
                ],
            ),
            ft.Text(
                f"Pos {position}/{max_pos} · {state_label} · task {task_label} · {cost_label}",
                size=12,
                color=tokens.on_surface,
            ),
            ft.Text(event_line, size=12, color=tokens.on_surface),
            ft.Text("Bookmarks", size=12, weight=ft.FontWeight.W_600),
            bookmark_chips,
            ft.Text(
                "Scrub timeline untuk rewind Kanban & Cost. Tab lain ikut posisi replay.",
                size=11,
                italic=True,
                color=tokens.on_surface,
            ),
        ],
        spacing=10,
    )

    return ft.Container(
        expand=True,
        padding=16,
        bgcolor=tokens.surface,
        border_radius=8,
        content=controls,
    )
