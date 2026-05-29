# Cursor AI Developer Team Prompts

## Initial Project Scan

```txt
Baca AGENTS.md, docs/INDEX.md, docs/module_map.md, docs/coding_standard.md,
.cursor/team/agent_roster.md, .cursor/team/communication_protocol.md,
.cursor/memory/project_brief.md, .cursor/memory/active_context.md,
dan .cursor/memory/feature_registry.json.

Lakukan project scan ringan tanpa mengubah kode.

Identifikasi:
1. Bahasa utama.
2. Framework utama.
3. Package manager.
4. Struktur folder.
5. Arsitektur yang digunakan.
6. Routing/API pattern.
7. State management atau service pattern.
8. Database/data access pattern.
9. Auth/permission pattern jika ada.
10. Testing/lint/build command.
11. Modul utama yang sudah ada.
12. Potensi duplicate module/service/helper.
13. Potensi logic/perhitungan yang perlu dipisahkan.

Setelah itu:
- Update docs/module_map.md jika kosong atau belum akurat.
- Update .cursor/memory/active_context.md.
- Jangan ubah fitur dulu.
```

## New Feature

```txt
Gunakan AI Developer Team Workflow.

Tugas:
[ISI TUGAS]

Langkah kerja:
1. Bertindak sebagai Orchestrator dulu.
2. Buat TASK-[id].md di .cursor/team/tasks/.
3. Pilih agent yang diperlukan.
4. Jalankan analisa berurutan:
   - Product Manager jika perlu scope fitur.
   - Business Analyst jika ada aturan bisnis.
   - Logic & Algorithm Engineer jika ada logic/perhitungan/data processing.
   - Solution Architect untuk desain teknis.
   - Engineer terkait untuk implementasi.
   - QA untuk test.
   - Security jika ada auth/data/API/file/env.
   - Code Reviewer untuk final review.
   - Documentation Engineer untuk update docs.
5. Setiap agent wajib membuat handoff singkat.
6. Jangan coding sebelum plan disetujui untuk task medium/besar.
7. Jangan buat duplikasi fitur/service/module.
8. Jalankan check/test yang relevan.
9. Ringkas hasil akhir dengan file berubah, risiko, dan status review.
```

## Logic Heavy Task

```txt
Bertindak sebagai Logic & Algorithm Engineer Agent.

Baca:
- .cursor/agents/14-logic-algorithm-engineer.md
- docs/module_map.md
- .cursor/memory/feature_registry.json

Tugas:
[ISI TUGAS]

Analisa:
1. Logic yang dibutuhkan.
2. Existing logic yang mirip.
3. Input dan output.
4. Formula atau algoritma.
5. Edge case.
6. Rounding/precision jika ada.
7. Efisiensi algoritma.
8. Lokasi logic yang paling tepat.
9. Test case minimal.
10. Risiko jika logic salah.

Jangan coding dulu.
Buat LOGIC-HANDOFF-[task-id].
```

## Bug Fix

```txt
Fix bug berikut dengan perubahan minimal dan aman:

[PASTE ERROR / BUG]

Aturan:
1. Cari root cause, bukan cuma hilangkan error.
2. Cek implementasi existing yang terkait.
3. Jangan buat service/helper baru jika sudah ada.
4. Jangan ubah arsitektur.
5. Jangan ubah behavior lain yang tidak terkait.
6. Tambahkan validasi/error handling jika akar masalahnya parsing/input/API/database.
7. Jalankan lint/typecheck/test yang relevan.
8. Ringkas file yang berubah, alasan, risiko, dan command yang dijalankan.
```

## Code Review

```txt
Bertindak sebagai Code Reviewer Agent.
Baca .cursor/agents/11-code-reviewer.md.
Review semua perubahan pada branch saat ini.
Cari duplikasi, pelanggaran arsitektur, file tidak relevan, error handling yang kurang, logic yang belum disetujui, dan test yang belum dijalankan.
```
