from io import BytesIO
from pathlib import Path
from copy import copy
from openpyxl import load_workbook

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "production_order_template.xlsx"

def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def _norm(v):
    return " ".join(str(v).strip().lower().split())

def build_production_order(payload):
    payload = payload or {}
    if not TEMPLATE.is_file():
        raise FileNotFoundError(f"Production order template not found: {TEMPLATE}")

    # Start from the supplied workbook itself. This preserves its exact
    # dimensions, fonts, borders, number formats, print setup and layout.
    wb = load_workbook(TEMPLATE)
    ws = wb["Sheet1"]

    formula = payload.get("formula", "")
    if isinstance(formula, dict):
        formula = f"{formula.get('N', 0)}-{formula.get('P2O5', formula.get('P', 0))}-{formula.get('K2O', formula.get('K', 0))}"

    batch = _num(payload.get("batch_kg"))
    required = _num(payload.get("required_ton"))
    batches = _num(payload.get("batches"), 1.0) or 1.0

    # Header fields. The cells containing explanatory notes in the original
    # template are deliberately overwritten/cleared in the final document.
    ws["A4"] = f"Date: {payload.get('date') or __import__('datetime').date.today().strftime('%d/%m/%Y')}"
    ws["C6"] = formula
    ws["D6"] = payload.get("color", "")
    ws["C9"] = batch
    ws["D9"] = payload.get("client", "")
    ws["C10"] = payload.get("order_no", "")
    ws["D10"] = payload.get("brand") or payload.get("bag_type", "")
    ws["C11"] = required
    ws["C12"] = batches
    ws["C13"] = "=C9*C12"

    # Raw-material table in the original template has six rows (18:23).
    mats = payload.get("materials") or {}
    raw = [(str(name), _num(kg)) for name, kg in mats.items()
           if _norm(name) not in {
               "red color", "foom silica", "mgso4 33%", "mgso4",
               "aquamine", "fe eddha 6%", "disper chlorophy",
               "te-mix", "te- mix edta", "te mix", "te-mix edta"
           } and _num(kg) > 0]

    if len(raw) > 6:
        extra = len(raw) - 6
        ws.insert_rows(24, extra)
        # Copy the template row 23 formatting/formulas into the inserted rows.
        for r in range(24, 24 + extra):
            for c in range(1, 8):
                src = ws.cell(23, c)
                dst = ws.cell(r, c)
                if src.has_style:
                    dst._style = copy(src._style)
                if src.number_format:
                    dst.number_format = src.number_format
                dst.font = copy(src.font)
                dst.fill = copy(src.fill)
                dst.border = copy(src.border)
                dst.alignment = copy(src.alignment)
                dst.protection = copy(src.protection)
            ws.row_dimensions[r].height = ws.row_dimensions[23].height

    raw_end = 17 + max(6, len(raw))
    subtotal = raw_end + 1

    # Clear the raw-material slots first, then populate them.
    for r in range(18, raw_end + 1):
        for c in range(1, 7):
            ws.cell(r, c).value = None
    for idx, (name, kg_batch) in enumerate(raw, start=18):
        ws.cell(idx, 2).value = name
        ws.cell(idx, 3).value = kg_batch * 1000.0 / batch if batch else 0
        ws.cell(idx, 4).value = f"=C{idx}*$C$9/1000"
        ws.cell(idx, 5).value = f"=D{idx}*$C$12"
        ws.cell(idx, 6).value = None

    ws.cell(subtotal, 2).value = "Sub total:-"
    ws.cell(subtotal, 3).value = f"=SUM(C18:C{raw_end})"
    ws.cell(subtotal, 4).value = f"=C{subtotal}*$C$9/1000"
    ws.cell(subtotal, 5).value = f"=SUM(E18:E{raw_end})"
    ws.cell(subtotal, 6).value = None

    # With the normal six-material case, the additive rows stay exactly at
    # the template's original rows 27:38. If extra raw rows were inserted,
    # all these coordinates shift by the same amount.
    shift = max(0, len(raw) - 6)
    def rr(original_row):
        return original_row + shift

    additive_values = {
        27: _num(payload.get("color_qty")),
        28: 0,
        29: 0,
        30: _num(payload.get("foom_silica")),
        31: 0,
        32: 0,
        33: 0,
        34: 0,
        35: _num(payload.get("te_mix_kg_per_ton")),
        36: 0,
        37: 0,
        38: 0,
    }
    aliases = {}
    for name, kg in mats.items():
        aliases[_norm(name)] = _num(kg)

    additive_values[27] = _num(payload.get("color_qty"), aliases.get("red color", 0))
    additive_values[30] = _num(payload.get("foom_silica"), aliases.get("foom silica", 0))
    additive_values[31] = aliases.get("mgso4 33%", aliases.get("mgso4", 0))
    additive_values[32] = aliases.get("aquamine", 0)
    additive_values[33] = aliases.get("fe eddha 6%", 0)
    additive_values[34] = aliases.get("disper chlorophy", 0)
    additive_values[35] = _num(payload.get("te_mix_kg_per_ton"), aliases.get("te-mix", 0) * 1000.0 / batch if batch else 0)

    for original_row, value in additive_values.items():
        r = rr(original_row)
        ws.cell(r, 3).value = value
        ws.cell(r, 4).value = f"=C{r}*$C$9/1000"
        ws.cell(r, 5).value = f"=D{r}*$C$12"
        ws.cell(r, 6).value = None

    total = rr(39)
    ws.cell(total, 2).value = "Total"
    ws.cell(total, 3).value = f"=SUM(C{subtotal}:C{rr(38)})"
    ws.cell(total, 4).value = f"=C{total}*$C$9/1000"
    ws.cell(total, 5).value = f"=SUM(E{subtotal}:E{rr(38)})"
    ws.cell(total, 6).value = None

    # Remove every instructional annotation from the supplied template.
    for cell in ("C6", "D6", "C9", "D9", "C10", "D10", "C11", "C12",
                 "C27", "C28", "C29", "C30", "C31", "C32", "C33", "C34",
                 "C35", "C36", "C37", "C38"):
        # These are data cells, not the labels. They are already populated
        # above where applicable; this list documents the annotation cells
        # that must never survive in the output.
        pass

    # The original explanatory notes live in C6, D6, C9, D9, D10, C11, C12,
    # C27, C30, C32 and C34. Data was already written to all relevant cells.
    # No annotation text remains because those cells have been overwritten
    # with production values or blank values.

    out = BytesIO()
    wb.save(out)
    return out.getvalue()
