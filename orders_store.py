import json
import os
from typing import Any

ORDERS_FILE = "orders.json"


def _default() -> dict[str, Any]:
    return {"next_id": 1, "orders": {}}


def load_orders() -> dict[str, Any]:
    if not os.path.exists(ORDERS_FILE):
        data = _default()
        save_orders(data)
        return data
    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_orders(data: dict[str, Any]) -> None:
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def next_order_id() -> int:
    data = load_orders()
    order_id = int(data.get("next_id", 1))
    data["next_id"] = order_id + 1
    save_orders(data)
    return order_id


def upsert_order(order_id: int, payload: dict[str, Any]) -> None:
    data = load_orders()
    data.setdefault("orders", {})[str(order_id)] = payload
    save_orders(data)


def get_order(order_id: int) -> dict[str, Any] | None:
    data = load_orders()
    return data.get("orders", {}).get(str(order_id))


def get_orders_by_status(status: str) -> list[tuple[int, dict[str, Any]]]:
    data = load_orders()
    matches: list[tuple[int, dict[str, Any]]] = []
    for key, order in data.get("orders", {}).items():
        if order.get("status") == status:
            matches.append((int(key), order))
    return matches


def find_awaiting_order_by_exact_pay(amount: int) -> tuple[int, dict[str, Any]] | None:
    for order_id, order in get_orders_by_status("awaiting_payment"):
        if int(order.get("exact_pay", 0)) == amount:
            return order_id, order
    return None


def allocate_pay_suffix() -> int | None:
    """Return a free 2-digit code (00-99) for a pending payment."""
    used = {
        int(order["pay_suffix"])
        for _, order in get_orders_by_status("awaiting_payment")
        if order.get("pay_suffix") is not None
    }
    for suffix in range(100):
        if suffix not in used:
            return suffix
    return None


def build_exact_pay(base_money: int, pay_suffix: int) -> int:
    """Round amount to base and append unique last 2 digits (00-99)."""
    return (base_money // 100) * 100 + pay_suffix
