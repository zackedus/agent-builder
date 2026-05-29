# Cursor AI Developer Team Template

Template ini dipakai untuk membuat Cursor AI bekerja seperti tim developer:
- Orchestrator / Tech Lead
- Product Manager
- Business Analyst
- Logic & Algorithm Engineer
- Solution Architect
- Frontend Engineer
- Backend Engineer
- Database Engineer
- Integration Engineer
- QA Engineer
- Security Engineer
- DevOps Engineer
- Code Reviewer
- Refactor Engineer
- Documentation Engineer

## Cara pakai

1. Copy semua isi folder ini ke root project.
2. Buka project di Cursor.
3. Tunggu indexing selesai.
4. Jalankan prompt awal:

```txt
Baca AGENTS.md, docs/INDEX.md, docs/module_map.md, docs/coding_standard.md,
.cursor/team/agent_roster.md, .cursor/team/communication_protocol.md,
.cursor/memory/project_brief.md, .cursor/memory/active_context.md,
dan .cursor/memory/feature_registry.json.

Lakukan project scan ringan tanpa mengubah kode.
Identifikasi stack, arsitektur, package manager, struktur folder, command build/lint/test,
modul utama, dan potensi duplikasi.
Update docs/module_map.md dan .cursor/memory/active_context.md jika perlu.
```

## Prompt untuk task besar

```txt
Gunakan AI Developer Team Workflow.

Tugas:
[ISI TUGAS]

Langkah kerja:
1. Bertindak sebagai Orchestrator dulu.
2. Buat TASK-[id].md di .cursor/team/tasks/.
3. Pilih agent yang diperlukan.
4. Jalankan analisa berurutan.
5. Jangan coding sebelum plan selesai untuk task medium/besar.
6. Setiap agent wajib membuat handoff singkat.
7. Jalankan check/test relevan.
8. Ringkas hasil akhir dengan file berubah, risiko, dan status review.
```

## Prompt khusus logic/perhitungan

```txt
Gunakan AI Developer Team Workflow.

Tugas:
[ISI TUGAS]

Karena task ini melibatkan logic/perhitungan/data processing, wajib jalankan:
Orchestrator → PM/BA jika perlu → Logic & Algorithm Engineer → Architect → Engineer terkait → QA → Code Reviewer → Documentation.

Jangan coding sebelum Logic & Algorithm Engineer membuat LOGIC-HANDOFF.
```
