# PROMPTS.md — Template Prompt untuk Cursor AI

> **Tujuan file ini:** Koleksi prompt template siap pakai untuk skenario umum di project ini. Copy-paste, edit placeholder `{...}`, lalu kirim ke Cursor AI.
>
> **Cara pakai:** Cari section sesuai skenario → copy template → ganti placeholder → paste ke Cursor chat. Beberapa template butuh kamu attach file (gunakan `@filename` di Cursor).

---

## Daftar Isi Cepat

1. [Memulai Sesi Baru](#1-memulai-sesi-baru)
2. [Mulai Task Baru](#2-mulai-task-baru)
3. [Continue Task In-Progress](#3-continue-task-in-progress)
4. [Resolve Blocker](#4-resolve-blocker)
5. [Code Review Request](#5-code-review-request)
6. [Refactoring](#6-refactoring)
7. [Bug Fix](#7-bug-fix)
8. [Generate Test](#8-generate-test)
9. [Generate Prompt untuk Agent (Meta)](#9-generate-prompt-untuk-agent-meta)
10. [Architecture Decision](#10-architecture-decision)
11. [Akhiri Sesi](#11-akhiri-sesi)
12. [Quick Snippets](#12-quick-snippets)

---

## 1. Memulai Sesi Baru

**Kapan pakai:** Setiap kali buka Cursor untuk lanjutkan project. WAJIB selalu jalankan ini dulu.

```
Aku mau lanjutkan kerja project Agent Team Builder.

Tolong:
1. Baca @.cursorrules untuk paham konvensi project
2. Baca @PROGRESS.md section 1 (Resume Context) untuk paham state terkini
3. Baca @PROGRESS.md section 2 (Current Sprint) untuk paham task aktif
4. Cek apakah ada blocker aktif di section 1
5. Lapor ke aku status sekarang dalam 3-4 kalimat

Setelah itu tanya aku: sesi ini fokus task mana? Jangan langsung coding sampai aku konfirmasi.
```

---

## 2. Mulai Task Baru

**Kapan pakai:** Saat akan mengerjakan task baru dari roadmap di PROGRESS.md.

```
Aku mau mulai task {TASK_ID} — {TASK_TITLE}.

Sebelum coding:
1. Baca section relevan di @ARCHITECTURE.md untuk paham requirement
2. Baca existing code yang berkaitan (cek di src/agent_builder/{module_path})
3. Lapor pemahaman kamu dalam bentuk:
   - Apa yang akan dibuat (1-2 kalimat)
   - File mana yang akan dibuat/diedit
   - Dependencies / module lain yang akan di-touch
   - Test plan (test apa yang akan ditulis)
   - Estimasi LoC (kasaran)

Setelah aku konfirmasi rencananya, baru mulai coding.

Penting: ikuti semua aturan di @.cursorrules section 5 (Coding Standards).
```

**Contoh terisi:**
```
Aku mau mulai task F1.4.1 — implement Anthropic Claude client wrapper.

Sebelum coding:
1. Baca section relevan di @ARCHITECTURE.md untuk paham requirement
[... lanjut sama]
```

---

## 3. Continue Task In-Progress

**Kapan pakai:** Lanjutkan task yang sudah dimulai di sesi sebelumnya (status `[~]`).

```
Lanjutkan task {TASK_ID} yang status-nya in-progress.

Tolong:
1. Baca @PROGRESS.md untuk ingat konteks terakhir
2. Cek git log terbaru — lihat commit terkait task ini
3. Cek file yang sudah dibuat/diedit di branch ini
4. Identify apa yang belum selesai berdasarkan acceptance criteria
5. Lapor ke aku:
   - Apa yang sudah selesai
   - Apa yang masih kurang
   - Apakah ada pendekatan yang berubah sejak sesi terakhir

Setelah aku approve, lanjut coding.
```

---

## 4. Resolve Blocker

**Kapan pakai:** Saat task `[!]` blocked dan butuh investigation.

```
Task {TASK_ID} status blocked. Detail blocker ada di @PROGRESS.md section 1.

Tolong:
1. Baca blocker description
2. Reproduce masalah (jalankan test/script yang fail)
3. Investigate root cause — JANGAN langsung kasih solusi
4. Lapor:
   - Apa root cause (1-2 paragraf, dengan referensi line code)
   - Minimal 2 opsi solusi dengan trade-off masing-masing
   - Rekomendasi kamu + alasan

Tunggu aku decide opsi mana sebelum implement.
```

---

## 5. Code Review Request

**Kapan pakai:** Sebelum commit/PR, minta self-review dari Cursor.

```
Aku baru selesai implement {DESCRIPTION}. File yang berubah:
@{file1} @{file2} @{file3}

Tolong review dengan kriteria:
1. Adherence ke @.cursorrules (style, type hints, async patterns)
2. Test coverage — apakah ada edge case yang miss?
3. Error handling — apakah ada path yang silent fail?
4. Performance — ada code yang inefficient?
5. Security — ada risk (eval/exec, SQL injection, dll)?
6. Consistency dengan modul lain yang sudah ada
7. Naming / readability

Output format:
- Issues per severity: 🔴 Critical, 🟡 Should-fix, 🟢 Nice-to-have
- Untuk setiap issue: file:line, deskripsi, suggested fix

Kalau semua oke, kasih "✅ Ready to commit".
```

---

## 6. Refactoring

**Kapan pakai:** Saat butuh restructure code tanpa ubah behavior.

```
Aku mau refactor {TARGET} — saat ini masalahnya {PROBLEM}.

Goal refactoring:
- {GOAL_1}
- {GOAL_2}

Constraint:
- TIDAK boleh ubah public API (signature method/class yang di-import dari luar)
- TIDAK boleh ubah behavior (semua existing test harus tetap pass)
- Setiap step refactor harus tetap dalam state working (test green)

Tolong:
1. Analisis kondisi saat ini — apa yang problematic
2. Propose refactoring plan dalam tahapan kecil (max 5 step)
3. Untuk setiap step: apa yang berubah, kenapa, dampak ke modul lain
4. Tunggu aku approve plan, baru execute step-by-step

JANGAN refactor sekaligus. JANGAN ubah lebih dari yang diminta.
```

---

## 7. Bug Fix

**Kapan pakai:** Ada bug, mau di-fix dengan disiplin.

```
Ada bug: {BUG_DESCRIPTION}

Reproduce step:
1. {STEP_1}
2. {STEP_2}
3. Expected: {EXPECTED}
4. Actual: {ACTUAL}

Tolong:
1. Reproduce di local — jalankan step di atas, capture output
2. Identify root cause (BUKAN cuma symptom)
3. Tulis FAILING TEST yang capture bug ini dulu (red phase)
4. Setelah test fail di-konfirmasi, baru fix bug (green phase)
5. Lalu refactor kalau perlu (refactor phase)
6. Update PROGRESS.md section 9 (Risk Register) kalau ini risk yang muncul ulang

Tunggu konfirmasi di setiap fase sebelum lanjut.
```

---

## 8. Generate Test

**Kapan pakai:** Butuh test untuk module yang sudah ada / baru.

```
Generate test untuk @{file_path}.

Spesifikasi:
- Test framework: pytest + pytest-asyncio
- Mocking: pytest-mock untuk LLM calls (JANGAN call real API di unit test)
- Coverage target: minimal 80% untuk file ini
- Test naming: test_<function>_<scenario>_<expected>

Kategori test yang aku perlu:
1. Happy path (normal usage)
2. Edge cases (empty input, max input, dll)
3. Error handling (invalid input, network fail, dll)
4. Concurrency (kalau ada async)

Output di tests/unit/test_{module_name}.py

Setelah generate, jalankan dan pastikan semua pass. Kalau ada yang fail karena bug di source, lapor jangan auto-fix.
```

---

## 9. Generate Prompt untuk Agent (Meta)

**Kapan pakai:** Saat butuh tulis prompt template untuk agent kita (Planner, Coder, dll).

```
Aku butuh prompt template untuk {AGENT_NAME} agent di project ini.

Konteks agent ini (dari @ARCHITECTURE.md §{section}):
- Input: {INPUT_DESCRIPTION}
- Output: {OUTPUT_DESCRIPTION}
- Model yang akan dipakai: {MODEL}
- Constraints: {CONSTRAINTS}

Requirement prompt:
1. System prompt jelas — define role, capability, dan limit agent
2. Few-shot examples (minimal 2) untuk shape output
3. Output format strict (JSON schema atau struktur spesifik)
4. Instruction untuk handle edge cases
5. Tidak ada hallucinated capabilities

Struktur file (simpan di src/agent_builder/llm/prompts/{agent_name}.txt):

---
SYSTEM:
{system prompt}

EXAMPLES:
{contoh 1}
{contoh 2}

INSTRUCTION:
{instruksi untuk task ini}

OUTPUT FORMAT:
{schema/structure}
---

Tunjukin draft dulu, aku review baru save ke file.
```

---

## 10. Architecture Decision

**Kapan pakai:** Saat ada keputusan teknis baru yang impact arsitektur.

```
Aku perlu decide tentang: {DECISION_TOPIC}

Konteks:
- {CONTEXT_1}
- {CONTEXT_2}

Constraint:
- {CONSTRAINT_1}
- {CONSTRAINT_2}

Tolong:
1. Identify 3-4 opsi yang viable (BUKAN cuma 2 — biar ada nuansa)
2. Untuk setiap opsi: pros, cons, implementation effort, long-term maintenance impact
3. Mapping ke prinsip arsitektur kita (@ARCHITECTURE.md §2)
4. Rekomendasi + alasan kuat
5. Implications kalau decide opsi tertentu (apa yang berubah di code base sekarang?)

JANGAN cuma pilih default opsi. Tunjukin trade-off jujur.

Setelah aku decide, update @PROGRESS.md section 6 (Decision Log) dengan entry baru.
```

---

## 11. Akhiri Sesi

**Kapan pakai:** Sebelum tutup Cursor, WAJIB lakukan ini.

```
Aku mau akhiri sesi ini.

Tolong:
1. Summary apa yang dikerjakan sesi ini (task ID, files changed, kode tersedia)
2. Update @PROGRESS.md:
   - Section 1 (Resume Context): status sekarang, apa baru selesai, next action
   - Section 3 (Phase Tracking): centang task yang selesai
   - Section 5 (Session Log): append entry baru dengan format yang sudah ada
3. Cek git status — kalau ada uncommitted changes, propose commit message
4. Identify open items yang harus dihandle sesi berikutnya
5. Kalau ada blocker baru, catat di section 1

Output: konfirmasi PROGRESS.md sudah ter-update + draft commit message.
```

---

## 12. Quick Snippets

Snippet pendek untuk kebutuhan cepat. Copy-paste, edit, kirim.

### Cek state cepat

```
Cek @PROGRESS.md, lapor task aktif dan blocker (kalau ada). Max 3 kalimat.
```

### Cari implementasi

```
Cari di codebase: di mana {FUNCTION_NAME} di-define dan di-call?
Tampilkan dalam format: definition di X, callers: Y, Z, ...
```

### Explain code

```
Explain @{file_path} dalam 5 kalimat. Fokus: tanggung jawab utama, dependency, dan pattern yang dipakai.
```

### Pilih nama

```
Aku butuh nama untuk {THING} — yang melakukan {WHAT}.
Kasih 5 opsi naming yang idiomatic Python + alasan singkat per opsi.
```

### Pre-commit check

```
Aku mau commit perubahan terakhir. Tolong:
1. `ruff check .` — kalau ada error, fix
2. `ruff format .` — apply
3. `mypy src/` — kalau ada error, lapor (jangan auto-fix sembarangan)
4. `pytest tests/unit/` — pastikan green
5. Suggest commit message sesuai format @.cursorrules §6
```

### Generate docstring

```
Generate docstring untuk @{file_path} — gunakan Google style.
Untuk setiap public function/class:
- 1 baris summary
- Args description
- Returns description
- Raises (kalau ada)
- Example (untuk fungsi non-trivial)

Existing docstring jangan di-overwrite kecuali aku approve.
```

### Compare 2 file

```
Compare @{file1} dan @{file2}. Identify:
- Duplikasi kode (kalau ada)
- Konvensi yang inkonsisten
- Opportunity untuk extract shared util
Output dalam tabel.
```

### Debug "kenapa ini gak jalan"

```
Aku run {COMMAND} dan dapet error berikut:

```
{PASTE ERROR}
```

Sebelum kasih fix:
1. Explain dulu apa arti error ini (untuk aku belajar)
2. Trace ke kode mana yang trigger (file:line)
3. Tunjukin minimum 2 kemungkinan root cause
4. Tunggu aku konfirmasi sebelum apply fix

JANGAN langsung edit kode tanpa konfirmasi.
```

### Update dependency

```
Aku mau add dependency: {PACKAGE_NAME} versi {VERSION}.

Tolong:
1. Cek apakah sudah ada alternatif yang sudah ter-install di @pyproject.toml
2. Cek security advisories untuk package ini (kalau bisa)
3. Cek apakah masih maintained (last commit, last release)
4. Cek lisensi — kompatibel dengan project kita?
5. Kalau OK, update @pyproject.toml dan install
6. Update @PROGRESS.md kalau ini dependency major
```

---

## Catatan Tambahan

### Tentang "Tunggu konfirmasi" pattern

Banyak template di file ini ada instruksi "tunggu aku konfirmasi dulu". Ini sengaja, karena:

1. **Mencegah Cursor over-eager** — tanpa ini, Cursor sering langsung apply changes besar sekaligus
2. **Memberi kamu kontrol** — kamu yang putuskan direction, AI yang execute
3. **Mengurangi cost** — kalau approach salah, ketahuan di tahap planning bukan setelah 500 baris kode

Trade-off: lebih lambat per round, tapi lebih akurat overall.

### Tentang token cost

Saat kerja di Cursor, hindari:
- Paste full file kalau bisa reference dengan `@filename`
- Re-paste konteks yang sudah ada di history
- Minta output yang verbose ("explain like I'm 5" + 1000 baris kode)

Prefer:
- `@file:start-end` untuk reference partial
- "Lapor dalam 3 kalimat" untuk summary
- Iterative refinement (small steps) over big-bang

### Tentang konsistensi

Kalau Cursor mulai inkonsisten dengan rules di `.cursorrules`, ingatkan:
```
Cek lagi @.cursorrules §X — kayaknya kamu skip aturan tentang Y.
```

Atau update `.cursorrules` kalau aturannya yang outdated.

---

**Versi:** 1.0 (2026-05-29)
**Cara update:** Tambah section baru kalau ada skenario yang sering muncul tapi belum ter-cover. Hapus section yang tidak pernah dipakai.
