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
