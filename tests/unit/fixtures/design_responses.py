"""Sample design.json payloads for parser tests (F4.2.5)."""

FORM_DESIGN_JSON = """
{
  "screen_id": "expense_form",
  "title": "Tambah Pengeluaran",
  "layout": "column",
  "widgets": [
    {"type": "TextField", "id": "amount_input", "label": "Nominal (Rp)"},
    {"type": "Dropdown", "id": "category", "label": "Kategori", "options": ["Makan", "Transport"]},
    {"type": "ElevatedButton", "id": "submit_btn", "label": "Simpan"}
  ],
  "navigation": {"back_to": "home", "next_on_success": "home"}
}
"""

LIST_DESIGN_JSON = """
{
  "screen_id": "todo_list",
  "title": "Daftar Todo",
  "layout": "column",
  "widgets": [
    {"type": "AppBar", "id": "app_bar", "label": "Todos"},
    {"type": "ListView", "id": "task_list", "label": "Tasks"},
    {"type": "ElevatedButton", "id": "add_btn", "label": "Tambah"}
  ]
}
"""

NAVIGATION_DESIGN_JSON = """
{
  "screen_id": "app_shell",
  "title": "Navigasi Utama",
  "layout": "row",
  "widgets": [
    {"type": "NavigationRail", "id": "nav_rail", "label": "Menu"},
    {"type": "Column", "id": "content_area", "label": "Konten"}
  ],
  "navigation": {"back_to": null, "next_on_success": "todo_list"}
}
"""

CHART_DESIGN_JSON = """
{
  "screen_id": "sales_dashboard",
  "title": "Dashboard Penjualan",
  "layout": "column",
  "widgets": [
    {"type": "Text", "id": "chart_title", "label": "Penjualan Bulanan"},
    {"type": "LineChart", "id": "sales_chart", "label": "Grafik"}
  ]
}
"""
