"""Local JSONL event store for WhatsApp bot demo (no external DB)."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT / "runtime"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(name: str) -> Path:
    """Resolve runtime JSONL path. RUNTIME_EVENT_STORE only overrides events.jsonl."""
    if name == "events.jsonl":
        override = (__import__("os").environ.get("RUNTIME_EVENT_STORE") or "").strip()
        if override:
            p = Path(override)
            return p if p.suffix == ".jsonl" else RUNTIME_DIR / "events.jsonl"
    return RUNTIME_DIR / name


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _read_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def append_event(event: dict[str, Any]) -> dict[str, Any]:
    rec = {**event, "event_id": event.get("event_id") or f"ev-{uuid.uuid4().hex[:12]}"}
    rec.setdefault("timestamp", _now_iso())
    _append_jsonl(_path("events.jsonl"), rec)
    return rec


def list_events(limit: int = 100) -> list[dict[str, Any]]:
    return list(reversed(_read_jsonl(_path("events.jsonl"), limit=limit * 2)))[:limit]


def list_outbound_messages(limit: int = 30) -> list[dict[str, Any]]:
    return list(reversed(_read_jsonl(_path("outbox.jsonl"), limit=limit * 2)))[:limit]


def list_inbound_messages(limit: int = 30) -> list[dict[str, Any]]:
    return list(reversed(_read_jsonl(_path("inbound.jsonl"), limit=limit * 2)))[:limit]


def normalize_phone(phone: str | None) -> str:
    """Canonical room key: digits only so +628… and 628… map to the same chat."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone).strip())
    return digits


def display_phone(phone: str | None, phone_key: str | None = None) -> str:
    """Human-readable phone for UI (prefer stored value, else E.164 from key)."""
    raw = (phone or "").strip()
    if raw:
        return raw
    key = (phone_key or "").strip()
    if key.isdigit() and len(key) >= 9:
        return f"+{key}"
    return key or "—"


def build_chat_threads(limit_rooms: int = 40) -> list[dict[str, Any]]:
    """Group inbound/outbound messages by customer phone (chat room per number)."""
    threads: dict[str, dict[str, Any]] = {}

    def ensure(phone: str) -> dict[str, Any]:
        key = normalize_phone(phone) or "unknown"
        if key not in threads:
            threads[key] = {
                "phone": phone,
                "phone_key": key,
                "customer_name": None,
                "messages": [],
                "order_ids": [],
                "last_timestamp": "",
                "last_preview": "",
            }
        return threads[key]

    for m in _read_jsonl(_path("inbound.jsonl"), 5000):
        phone = str(m.get("from_phone") or "").strip()
        if not phone:
            continue
        t = ensure(phone)
        if m.get("customer_name"):
            t["customer_name"] = m["customer_name"]
        t["messages"].append({**m, "direction": "in"})

    for m in _read_jsonl(_path("outbox.jsonl"), 5000):
        phone = str(m.get("to_phone") or "").strip()
        if not phone:
            continue
        t = ensure(phone)
        t["messages"].append({**m, "direction": "out"})

    for o in get_recent_bot_orders(300):
        phone = str(o.get("customer_phone") or "").strip()
        if not phone:
            continue
        t = ensure(phone)
        if o.get("customer_name"):
            t["customer_name"] = o["customer_name"]
        oid = o.get("order_id")
        if oid and oid not in t["order_ids"]:
            t["order_ids"].append(oid)

    result: list[dict[str, Any]] = []
    for t in threads.values():
        msgs = sorted(t["messages"], key=lambda x: str(x.get("timestamp") or ""))
        t["messages"] = msgs
        if msgs:
            last = msgs[-1]
            t["last_timestamp"] = str(last.get("timestamp") or "")
            preview = str(last.get("text") or "").replace("\n", " ")[:72]
            t["last_preview"] = preview
        t["order_ids"] = sorted(t["order_ids"])
        result.append(t)

    result.sort(key=lambda x: str(x.get("last_timestamp") or ""), reverse=True)
    return result[:limit_rooms]


def get_thread_by_key(phone_key: str) -> dict[str, Any] | None:
    key = normalize_phone(phone_key) or phone_key
    for t in build_chat_threads():
        if t.get("phone_key") == key:
            return t
    return None


def append_inbound_message(
    *,
    message_id: str,
    from_phone: str,
    text: str,
    customer_name: str | None = None,
    source: str = "whatsapp",
) -> dict[str, Any] | None:
    existing = {m.get("message_id") for m in _read_jsonl(_path("inbound.jsonl"), 5000)}
    if message_id in existing:
        return None
    rec = {
        "type": "inbound",
        "message_id": message_id,
        "from_phone": from_phone,
        "text": text,
        "customer_name": customer_name,
        "source": source,
        "processed": False,
        "timestamp": _now_iso(),
    }
    _append_jsonl(_path("inbound.jsonl"), rec)
    append_event({"type": "inbound_message", "message_id": message_id})
    return rec


def get_unprocessed_inbound_messages() -> list[dict[str, Any]]:
    return [m for m in _read_jsonl(_path("inbound.jsonl"), 5000) if not m.get("processed")]


def mark_message_processed(message_id: str) -> None:
    path = _path("inbound.jsonl")
    if not path.is_file():
        return
    rows = _read_jsonl(path, 10000)
    path.write_text("", encoding="utf-8")
    for r in rows:
        if r.get("message_id") == message_id:
            r["processed"] = True
        _append_jsonl(path, r)


def append_outbound_message(to_phone: str, text: str, *, order_id: str | None = None) -> dict[str, Any]:
    rec = {
        "type": "outbound",
        "to_phone": to_phone,
        "text": text,
        "order_id": order_id,
        "timestamp": _now_iso(),
        "message_id": f"out-{uuid.uuid4().hex[:10]}",
    }
    _append_jsonl(_path("outbox.jsonl"), rec)
    append_event({"type": "outbound_message", "order_id": order_id})
    return rec


def append_bot_order(order: dict[str, Any]) -> dict[str, Any]:
    rec = {**order, "timestamp": order.get("timestamp") or _now_iso()}
    _append_jsonl(_path("orders.jsonl"), rec)
    append_event({"type": "bot_order", "order_id": order.get("order_id")})
    return rec


def get_recent_bot_orders(limit: int = 50) -> list[dict[str, Any]]:
    return list(reversed(_read_jsonl(_path("orders.jsonl"), limit=limit * 2)))[:limit]


def get_bot_order(order_id: str) -> dict[str, Any] | None:
    for o in reversed(_read_jsonl(_path("orders.jsonl"), 5000)):
        if str(o.get("order_id")) == order_id:
            return o
    return None


def update_bot_order(order_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    path = _path("orders.jsonl")
    rows = _read_jsonl(path, 10000)
    updated: dict[str, Any] | None = None
    path.write_text("", encoding="utf-8")
    for r in rows:
        if str(r.get("order_id")) == order_id:
            r = {**r, **patch}
            updated = r
        _append_jsonl(path, r)
    return updated


def append_payment_event(event: dict[str, Any]) -> dict[str, Any] | None:
    eid = event.get("event_id") or f"pay-{uuid.uuid4().hex[:12]}"
    existing = {e.get("event_id") for e in _read_jsonl(_path("payments.jsonl"), 5000)}
    if eid in existing:
        return None
    rec = {**event, "event_id": eid, "timestamp": event.get("timestamp") or _now_iso()}
    _append_jsonl(_path("payments.jsonl"), rec)
    append_event({"type": "payment", "event_id": eid, "order_id": event.get("order_id")})
    return rec


def get_recent_payments(limit: int = 50) -> list[dict[str, Any]]:
    return list(reversed(_read_jsonl(_path("payments.jsonl"), limit=limit * 2)))[:limit]


def _pending_path() -> Path:
    return _path("pending_orders.jsonl")


def get_pending_order(from_phone: str) -> dict[str, Any] | None:
    want = normalize_phone(from_phone)
    if not want:
        return None
    for row in reversed(_read_jsonl(_pending_path(), 5000)):
        if normalize_phone(row.get("from_phone")) == want:
            return row
    return None


def set_pending_order(from_phone: str, draft: dict[str, Any]) -> dict[str, Any]:
    phone = (from_phone or "").strip()
    clear_pending_order(phone)
    rec = {**draft, "from_phone": phone, "timestamp": _now_iso()}
    _append_jsonl(_pending_path(), rec)
    return rec


def clear_pending_order(from_phone: str) -> None:
    want = normalize_phone(from_phone)
    path = _pending_path()
    rows = _read_jsonl(path, 10000)
    path.write_text("", encoding="utf-8")
    for r in rows:
        if normalize_phone(r.get("from_phone")) != want:
            _append_jsonl(path, r)


def reset_runtime_events() -> None:
    for name in (
        "events.jsonl",
        "inbound.jsonl",
        "outbox.jsonl",
        "orders.jsonl",
        "payments.jsonl",
        "pending_orders.jsonl",
    ):
        p = _path(name)
        if p.is_file():
            p.unlink()
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def next_bot_order_id() -> str:
    orders = _read_jsonl(_path("orders.jsonl"), 10000)
    n = 1
    for o in orders:
        oid = str(o.get("order_id", ""))
        if oid.startswith("ORD-BOT-"):
            try:
                n = max(n, int(oid.split("-")[-1]) + 1)
            except ValueError:
                pass
    return f"ORD-BOT-{n:04d}"


def runtime_snapshot_for_hash() -> dict[str, Any]:
    """Stable bot fingerprint for change detection (not raw message counts)."""
    orders = get_recent_bot_orders(200)
    payments = get_recent_payments(200)
    return {
        "orders": sorted(
            (
                str(o.get("order_id") or ""),
                str(o.get("payment_status") or ""),
                int(o.get("matched_amount") or 0),
            )
            for o in orders
        ),
        "payment_events": sorted(str(p.get("event_id") or "") for p in payments),
    }
