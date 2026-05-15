"""Merchant-owned product catalogue — load, match, validate, price orders."""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = ROOT / "data" / "product_catalogue.csv"
FUZZY_THRESHOLD = 78


def _norm(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def load_product_catalogue_from_csv(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or CATALOGUE_PATH
    if not p.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with open(p, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(normalize_catalogue_row(row))
    return rows


def normalize_catalogue_row(row: dict[str, Any]) -> dict[str, Any]:
    aliases_raw = row.get("aliases") or ""
    if isinstance(aliases_raw, list):
        aliases = [str(a).strip() for a in aliases_raw if str(a).strip()]
    else:
        aliases = [a.strip() for a in str(aliases_raw).split("|") if a.strip()]
    name = str(row.get("product_name") or "").strip()
    if name and _norm(name) not in {_norm(a) for a in aliases}:
        aliases.insert(0, name)
    active = str(row.get("is_active", "true")).strip().lower() in {"1", "true", "yes", "y"}
    try:
        price = int(float(str(row.get("unit_price") or "0").replace(",", "")))
    except ValueError:
        price = 0
    sku = str(row.get("sku") or "").strip() or f"SKU-{hashlib.md5(name.encode()).hexdigest()[:6].upper()}"
    return {
        "sku": sku,
        "product_name": name,
        "aliases": aliases,
        "category": str(row.get("category") or "other").strip(),
        "unit_price": price,
        "unit": str(row.get("unit") or "porsi").strip(),
        "is_active": active,
        "stock_optional": str(row.get("stock_optional") or "").strip(),
        "notes": str(row.get("notes") or "").strip(),
    }


def normalize_catalogue_tool(catalogue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_catalogue_row(r) for r in catalogue]


def catalogue_version(catalogue: list[dict[str, Any]]) -> str:
    payload = [
        (r.get("sku"), r.get("product_name"), r.get("unit_price"), r.get("is_active"))
        for r in catalogue
    ]
    return hashlib.sha256(repr(payload).encode()).hexdigest()[:12]


def load_product_catalogue_tool(state: Any) -> list[dict[str, Any]]:
    cat = getattr(state, "product_catalogue", None)
    if cat:
        return normalize_catalogue_tool(cat)
    loaded = load_product_catalogue_from_csv()
    if hasattr(state, "product_catalogue"):
        state.product_catalogue = loaded
        state.catalogue_version = catalogue_version(loaded)
    return loaded


def save_product_catalogue_tool(
    catalogue: list[dict[str, Any]], path: Path | None = None
) -> Path:
    p = path or CATALOGUE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sku",
        "product_name",
        "aliases",
        "category",
        "unit_price",
        "unit",
        "is_active",
        "stock_optional",
        "notes",
    ]
    rows = normalize_catalogue_tool(catalogue)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "sku": r["sku"],
                    "product_name": r["product_name"],
                    "aliases": "|".join(r["aliases"]),
                    "category": r["category"],
                    "unit_price": r["unit_price"],
                    "unit": r["unit"],
                    "is_active": str(r["is_active"]).lower(),
                    "stock_optional": r.get("stock_optional", ""),
                    "notes": r.get("notes", ""),
                }
            )
    return p


def _active_catalogue(catalogue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in catalogue if r.get("is_active", True)]


def _alias_index(catalogue: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for row in catalogue:
        if not row.get("is_active", True):
            continue
        for alias in row.get("aliases") or []:
            key = _norm(alias)
            if key and key not in idx:
                idx[key] = row
    return idx


def match_catalogue_item(
    text: str, catalogue: list[dict[str, Any]], *, min_score: int = FUZZY_THRESHOLD
) -> dict[str, Any]:
    """Match a single item phrase to catalogue row."""
    phrase = _norm(text)
    if not phrase:
        return {
            "status": "UNKNOWN_PRODUCT",
            "match_confidence": 0,
            "raw_text": text,
        }

    idx = _alias_index(catalogue)
    if phrase in idx:
        row = idx[phrase]
        return {
            "status": "MATCHED",
            "match_confidence": 100,
            "sku": row["sku"],
            "product_name": row["product_name"],
            "matched_alias": phrase,
            "unit_price": row["unit_price"],
            "unit": row["unit"],
            "raw_text": text,
        }

    choices = list(idx.keys())
    if not choices:
        return {"status": "UNKNOWN_PRODUCT", "match_confidence": 0, "raw_text": text}

    match = process.extractOne(phrase, choices, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= min_score:
        row = idx[match[0]]
        return {
            "status": "MATCHED",
            "match_confidence": int(match[1]),
            "sku": row["sku"],
            "product_name": row["product_name"],
            "matched_alias": match[0],
            "unit_price": row["unit_price"],
            "unit": row["unit"],
            "raw_text": text,
        }

    return {
        "status": "UNKNOWN_PRODUCT",
        "match_confidence": int(match[1]) if match else 0,
        "raw_text": text,
    }


def calculate_order_total_from_catalogue(
    parsed_items: list[dict[str, Any]], catalogue: list[dict[str, Any]]
) -> dict[str, Any]:
    total = 0
    unknown: list[str] = []
    lines: list[dict[str, Any]] = []
    for it in parsed_items:
        qty = int(it.get("quantity") or 1)
        if it.get("status") == "UNKNOWN_PRODUCT" or not it.get("unit_price"):
            unknown.append(str(it.get("raw_text") or it.get("product_name") or "?"))
            lines.append({**it, "line_total": None, "quantity": qty})
            continue
        line_total = int(it["unit_price"]) * qty
        total += line_total
        lines.append({**it, "line_total": line_total, "quantity": qty})
    return {
        "catalogue_total": total if not unknown else None,
        "items": lines,
        "unknown_products": unknown,
    }


def find_catalogue_item(
    catalogue: list[dict[str, Any]], sku: str
) -> dict[str, Any] | None:
    key = str(sku or "").strip()
    if not key:
        return None
    for row in catalogue:
        if str(row.get("sku") or "").strip() == key:
            return row
    return None


def generate_catalogue_sku(catalogue: list[dict[str, Any]]) -> str:
    existing = {str(r.get("sku") or "") for r in catalogue}
    n = 1
    while True:
        candidate = f"SKU-{n:03d}"
        if candidate not in existing:
            return candidate
        n += 1


def upsert_catalogue_item(
    catalogue: list[dict[str, Any]], row: dict[str, Any]
) -> list[dict[str, Any]]:
    """Insert or replace by sku."""
    normalized = normalize_catalogue_row(row)
    sku = str(normalized.get("sku") or "").strip()
    if not sku:
        normalized["sku"] = generate_catalogue_sku(catalogue)
        sku = normalized["sku"]
    out: list[dict[str, Any]] = []
    replaced = False
    for existing in catalogue:
        if str(existing.get("sku") or "").strip() == sku:
            out.append(normalized)
            replaced = True
        else:
            out.append(existing)
    if not replaced:
        out.append(normalized)
    return normalize_catalogue_tool(out)


def delete_catalogue_item(
    catalogue: list[dict[str, Any]], sku: str
) -> tuple[list[dict[str, Any]], bool]:
    key = str(sku or "").strip()
    if not key:
        return catalogue, False
    out = [r for r in catalogue if str(r.get("sku") or "").strip() != key]
    return out, len(out) < len(catalogue)


def validate_catalogue_tool(catalogue: list[dict[str, Any]]) -> dict[str, Any]:
    warnings: list[str] = []
    skus: set[str] = set()
    for row in normalize_catalogue_tool(catalogue):
        if not row.get("product_name"):
            warnings.append("Row missing product_name")
        if row["sku"] in skus:
            warnings.append(f"Duplicate sku: {row['sku']}")
        skus.add(row["sku"])
        if row.get("unit_price", 0) <= 0:
            warnings.append(f"Invalid price for {row.get('product_name')}")
        if not row.get("aliases"):
            warnings.append(f"No aliases for {row.get('product_name')}")
    return {"ok": len(warnings) == 0, "warnings": warnings, "count": len(catalogue)}


ITEM_QTY_RE = re.compile(
    r"([a-z0-9\s]+?)\s+(\d+)\b",
    re.IGNORECASE,
)


def extract_order_items(text: str, catalogue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse 'nasi goreng 2 es teh 1' style fragments."""
    work = text.lower()
    for pat in (
        r"\b(menu|daftar|help|bantuan|status)\b.*",
        r"\btotal\s+[\d\.\,]+.*",
        r"\s*-\s*[^-]+$",
    ):
        work = re.sub(pat, " ", work)
    work = re.sub(r"\s+", " ", work).strip()

    items: list[dict[str, Any]] = []
    used_spans: list[tuple[int, int]] = []

    active = [r for r in catalogue if r.get("is_active", True)]
    alias_list: list[tuple[str, dict[str, Any]]] = []
    for row in active:
        for alias in sorted(row.get("aliases") or [], key=len, reverse=True):
            alias_list.append((alias.lower(), row))

    for alias, row in alias_list:
        pattern = re.compile(re.escape(alias) + r"\s*(\d+)", re.I)
        for m in pattern.finditer(work):
            span = (m.start(), m.end())
            if any(not (span[1] <= s[0] or span[0] >= s[1]) for s in used_spans):
                continue
            used_spans.append(span)
            qty = int(m.group(1))
            matched = match_catalogue_item(alias, catalogue)
            items.append(
                {
                    "raw_text": m.group(0).strip(),
                    "sku": matched.get("sku"),
                    "product_name": matched.get("product_name") or row["product_name"],
                    "matched_alias": matched.get("matched_alias") or alias,
                    "quantity": qty,
                    "unit_price": matched.get("unit_price") or row["unit_price"],
                    "unit": row.get("unit"),
                    "match_confidence": matched.get("match_confidence", 100),
                    "status": matched.get("status", "MATCHED"),
                    "line_total": (matched.get("unit_price") or row["unit_price"]) * qty,
                }
            )

    if not items:
        for m in ITEM_QTY_RE.finditer(work):
            phrase = m.group(1).strip()
            qty = int(m.group(2))
            matched = match_catalogue_item(phrase, catalogue)
            items.append(
                {
                    "raw_text": m.group(0).strip(),
                    "sku": matched.get("sku"),
                    "product_name": matched.get("product_name"),
                    "matched_alias": matched.get("matched_alias"),
                    "quantity": qty,
                    "unit_price": matched.get("unit_price"),
                    "unit": matched.get("unit"),
                    "match_confidence": matched.get("match_confidence", 0),
                    "status": matched.get("status", "UNKNOWN_PRODUCT"),
                    "line_total": None
                    if matched.get("status") == "UNKNOWN_PRODUCT"
                    else (matched.get("unit_price") or 0) * qty,
                }
            )
    return items


def load_menu_catalog_legacy() -> dict[str, int]:
    """Backward compatibility with menu_price_catalog.json."""
    from tools.parsers import load_menu_catalog

    return load_menu_catalog()
