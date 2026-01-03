#!/usr/bin/env python3
"""
Phase 2 - Student E2E Integration Tests (Event-Driven Microservices)

Run:
  python tests/phase2_e2e_student.py

Optional env:
  ORDER_BASE=http://localhost:8001
  INVENTORY_BASE=http://localhost:8002
  PAYMENT_BASE=http://localhost:8003
  TIMEOUT_SECONDS=45
  POLL_INTERVAL=1
  DEBUG=1
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Set

import requests


# =========================
# Simple CLI UI (ANSI)
# =========================

class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

    BOX_LINE = "─"
    BOX_VERT = "│"
    BOX_TL = "┌"
    BOX_TR = "┐"
    BOX_BL = "└"
    BOX_BR = "┘"


def banner():
    title = " Distributed Systems - Phase 2 STUDENT E2E Tests "
    line = Style.BOX_LINE * len(title)
    print()
    print(f"{Style.CYAN}{Style.BOX_TL}{line}{Style.BOX_TR}{Style.RESET}")
    print(
        f"{Style.CYAN}{Style.BOX_VERT}{Style.RESET}"
        f"{Style.BOLD}{title}{Style.RESET}"
        f"{Style.CYAN}{Style.BOX_VERT}{Style.RESET}"
    )
    print(f"{Style.CYAN}{Style.BOX_BL}{line}{Style.BOX_BR}{Style.RESET}")
    print()


def section_title(text: str):
    line = Style.BOX_LINE * (len(text) + 2)
    print(f"\n{Style.BLUE}{Style.BOX_TL}{line}{Style.BOX_TR}{Style.RESET}")
    print(
        f"{Style.BLUE}{Style.BOX_VERT} "
        f"{Style.BOLD}{text}{Style.RESET}"
        f"{Style.BLUE} {Style.BOX_VERT}{Style.RESET}"
    )
    print(f"{Style.BLUE}{Style.BOX_BL}{line}{Style.BOX_BR}{Style.RESET}")


def info(msg: str):
    print(f"{Style.CYAN}ℹ {msg}{Style.RESET}")


def warn(msg: str):
    print(f"{Style.YELLOW}⚠ {msg}{Style.RESET}")


def ok(msg: str):
    print(f"{Style.GREEN}✔ {msg}{Style.RESET}")


def fail(msg: str):
    print(f"{Style.RED}✘ {msg}{Style.RESET}")


# =========================
# Config
# =========================

ORDER_BASE = os.getenv("ORDER_BASE", "http://localhost:8001")
INVENTORY_BASE = os.getenv("INVENTORY_BASE", "http://localhost:8002")
PAYMENT_BASE = os.getenv("PAYMENT_BASE", "http://localhost:8003")

TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "45"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1"))
DEBUG = os.getenv("DEBUG", "0").strip() in {"1", "true", "True", "YES", "yes"}

# Phase-2 expected API paths (edit only if your routes differ)
INVENTORY_CREATE_PATH = "/api/v1/stock/items"
INVENTORY_GET_PATH = "/api/v1/stock/items/{sku}"

ORDER_CREATE_PATH = "/api/v1/orders"
ORDER_GET_PATH = "/api/v1/orders/{order_id}"

PAYMENT_LIST_PATH = "/api/v1/payments/{order_id}"

# Test data
ITEM_SKU = "P-1001"
PRODUCT_NAME = "Test Product"
INITIAL_QUANTITY = 10

# Soft status sets (accept equivalent names)
ORDER_SUCCESS_STATUSES: Set[str] = {"COMPLETED", "CONFIRMED", "SUCCESS", "DONE"}
ORDER_FAIL_NO_STOCK_STATUSES: Set[str] = {"CANCELLED_NO_STOCK", "FAILED_STOCK", "REJECTED", "FAILED"}
ORDER_FAIL_PAYMENT_STATUSES: Set[str] = {"PAYMENT_FAILED", "CANCELLED_PAYMENT_FAILED", "FAILED"}

PAYMENT_SUCCESS_STATUSES: Set[str] = {"SUCCESS", "COMPLETED", "SUCCEEDED"}
PAYMENT_FAIL_STATUSES: Set[str] = {"FAILED", "REJECTED", "DECLINED"}


def debug(msg: str):
    if DEBUG:
        print(f"{Style.GRAY}… {msg}{Style.RESET}")


# =========================
# Models
# =========================

@dataclass
class TestResult:
    name: str
    success: bool
    details: str = ""
    scenario: str = ""


# =========================
# HTTP helpers
# =========================

def http(method: str, url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("timeout", 8)
    debug(f"{method} {url} kwargs={_safe_kwargs(kwargs)}")
    return requests.request(method, url, **kwargs)


def _safe_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(kwargs)
    return safe


def wait_for_health(base_url: str, service_name: str, timeout: int = 30) -> bool:
    url = f"{base_url}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = http("GET", url)
            if resp.status_code == 200:
                ok(f"{service_name} is healthy.")
                return True
        except Exception as e:
            debug(f"{service_name} not ready: {e}")
        time.sleep(1)
    fail(f"{service_name} did not become healthy in {timeout} seconds.")
    return False


def assert_status(resp: requests.Response, expected: int, ctx: str):
    if resp.status_code != expected:
        raise AssertionError(f"{ctx}: expected HTTP {expected}, got {resp.status_code}, body={resp.text}")


# =========================
# API calls
# =========================

def get_inventory_item(sku: str) -> Dict[str, Any]:
    url = INVENTORY_BASE + INVENTORY_GET_PATH.format(sku=sku)
    resp = http("GET", url)
    assert_status(resp, 200, f"GET inventory item {sku}")
    return resp.json()


def seed_inventory(scenario: str) -> TestResult:
    section_title("Seeding Inventory")
    try:
        payload = {"item_sku": ITEM_SKU, "name": PRODUCT_NAME, "quantity": INITIAL_QUANTITY}
        url = INVENTORY_BASE + INVENTORY_CREATE_PATH
        info(f"POST {url} → item_sku={ITEM_SKU}, quantity={INITIAL_QUANTITY}")
        resp = http("POST", url, json=payload)

        if resp.status_code not in (200, 201):
            fail(f"Unexpected status {resp.status_code}: {resp.text}")
            return TestResult("Seed Inventory", False, f"Unexpected status {resp.status_code}: {resp.text}", scenario)

        item = get_inventory_item(ITEM_SKU)
        qty = item.get("quantity")
        success = (qty == INITIAL_QUANTITY)
        msg = f"Expected quantity {INITIAL_QUANTITY}, got {qty} (item={item})"
        (ok if success else fail)(msg)
        return TestResult("Seed Inventory", success, msg, scenario)

    except Exception as e:
        fail(f"Exception while seeding inventory: {e}")
        return TestResult("Seed Inventory", False, str(e), scenario)


def create_order(quantity: int, amount: float, scenario: str, order_tag: str) -> (TestResult, Optional[int]):
    section_title(f"Create Order {order_tag}")
    try:
        payload = {
            "order_id": order_tag,
            "item_sku": ITEM_SKU,
            "quantity": quantity,
            "amount": amount,
            "payment_method": "card",
            "idempotency_key": f"student-{order_tag}-{uuid.uuid4()}",
        }
        url = ORDER_BASE + ORDER_CREATE_PATH
        info(f"POST {url} with quantity={quantity}, amount={amount}")
        resp = http("POST", url, json=payload)

        if resp.status_code not in (200, 201, 202):
            fail(f"Unexpected status {resp.status_code}: {resp.text}")
            return TestResult(f"Create Order {order_tag}", False, f"Unexpected status {resp.status_code}: {resp.text}", scenario), None

        data: Dict[str, Any] = {}
        try:
            data = resp.json()
        except Exception:
            data = {}

        order_db_id = data.get("id")
        if isinstance(order_db_id, int):
            ok(f"Order {order_tag} created with id={order_db_id} (HTTP {resp.status_code})")
            return TestResult(f"Create Order {order_tag}", True, f"Order accepted; id={order_db_id}", scenario), order_db_id

        warn(f"Order {order_tag} accepted but response has no numeric 'id'. Response={data}")
        return TestResult(f"Create Order {order_tag}", True, "Order accepted (no numeric id returned).", scenario), None

    except Exception as e:
        fail(f"Exception while creating order {order_tag}: {e}")
        return TestResult(f"Create Order {order_tag}", False, str(e), scenario), None


def get_order(order_id: int) -> Dict[str, Any]:
    url = ORDER_BASE + ORDER_GET_PATH.format(order_id=order_id)
    resp = http("GET", url)
    assert_status(resp, 200, f"GET order {order_id}")
    return resp.json()


def wait_for_order_status(order_id: int, expected: Set[str], scenario: str) -> TestResult:
    section_title(f"Wait For Order {order_id} Status")
    info(f"Waiting up to {TIMEOUT_SECONDS}s for order {order_id} to reach one of: {sorted(expected)}")
    start = time.time()
    last: Optional[str] = None

    while time.time() - start < TIMEOUT_SECONDS:
        try:
            o = get_order(order_id)
            st = str(o.get("status", ""))
            if st != last:
                print(f"    {Style.GRAY}Current status: {st}{Style.RESET}")
                last = st
            if st in expected:
                ok(f"Order {order_id} reached final status: {st}")
                return TestResult(f"Order {order_id} Status", True, f"Final status={st}", scenario)
        except Exception as e:
            debug(f"Order poll error: {e}")

        time.sleep(POLL_INTERVAL)

    fail(f"Timeout. Last status={last}")
    return TestResult(f"Order {order_id} Status", False, f"Timeout waiting for {sorted(expected)}. Last={last}", scenario)


def list_payments(order_id: int) -> List[Dict[str, Any]]:
    url = PAYMENT_BASE + PAYMENT_LIST_PATH.format(order_id=order_id)
    resp = http("GET", url)
    assert_status(resp, 200, f"GET payments for order {order_id}")
    data = resp.json()
    return data if isinstance(data, list) else [data]


def wait_for_payment(order_id: int, expected: Set[str], scenario: str) -> TestResult:
    section_title(f"Wait For Payment {order_id}")
    info(f"Waiting up to {TIMEOUT_SECONDS}s for payment status in: {sorted(expected)}")
    start = time.time()
    last: Optional[str] = None

    while time.time() - start < TIMEOUT_SECONDS:
        try:
            payments = list_payments(order_id)
            if payments:
                payments_sorted = sorted(payments, key=lambda p: p.get("id", 0))
                p = payments_sorted[-1]
                st = str(p.get("status", ""))
                if st != last:
                    print(f"    {Style.GRAY}Current payment status: {st}{Style.RESET}")
                    last = st
                if st in expected:
                    ok(f"Payment for order {order_id} reached status: {st}")
                    return TestResult(f"Payment {order_id}", True, f"Payment status={st}, payment={p}", scenario)
        except Exception as e:
            debug(f"Payment poll error: {e}")

        time.sleep(POLL_INTERVAL)

    fail(f"Timeout waiting for payment. Last={last}")
    return TestResult(f"Payment {order_id}", False, f"Timeout waiting for payment statuses {sorted(expected)}. Last={last}", scenario)


# =========================
# Scenarios
# =========================

def scenario_happy_path() -> List[TestResult]:
    scenario = "Scenario 1 - Happy Path"
    section_title(scenario)
    results: List[TestResult] = []

    results.append(seed_inventory(scenario))
    if not results[-1].success:
        return results

    create_res, order_id = create_order(quantity=3, amount=150.0, scenario=scenario, order_tag="O1")
    results.append(create_res)
    if not create_res.success:
        return results

    if order_id is None:
        warn("Skipping async checks because no numeric order id returned.")
        results.append(TestResult("Order Poll Skipped", False, "No numeric order id in create response.", scenario))
        return results

    results.append(wait_for_order_status(order_id, ORDER_SUCCESS_STATUSES, scenario))

    section_title("Verify Inventory Quantity After Order")
    try:
        item = get_inventory_item(ITEM_SKU)
        qty = item.get("quantity")
        expected = INITIAL_QUANTITY - 3
        success = (qty == expected)
        msg = f"Expected quantity {expected}, got {qty} (item={item})"
        (ok if success else fail)(msg)
        results.append(TestResult("Inventory Quantity After Happy Path", success, msg, scenario))
    except Exception as e:
        results.append(TestResult("Inventory Quantity After Happy Path", False, str(e), scenario))

    results.append(wait_for_payment(order_id, PAYMENT_SUCCESS_STATUSES, scenario))
    return results


def scenario_insufficient_stock() -> List[TestResult]:
    scenario = "Scenario 2 - Insufficient Stock"
    section_title(scenario)
    results: List[TestResult] = []

    results.append(seed_inventory(scenario))
    if not results[-1].success:
        return results

    create_res, order_id = create_order(quantity=INITIAL_QUANTITY + 5, amount=999.0, scenario=scenario, order_tag="O2")
    results.append(create_res)
    if not create_res.success:
        return results

    if order_id is None:
        warn("Skipping async checks because no numeric order id returned.")
        results.append(TestResult("Order Poll Skipped", False, "No numeric order id in create response.", scenario))
        return results

    results.append(wait_for_order_status(order_id, ORDER_FAIL_NO_STOCK_STATUSES, scenario))

    section_title("Verify Inventory Quantity Unchanged")
    try:
        item = get_inventory_item(ITEM_SKU)
        qty = item.get("quantity")
        expected = INITIAL_QUANTITY
        success = (qty == expected)
        msg = f"Expected quantity to remain {expected}, got {qty} (item={item})"
        (ok if success else fail)(msg)
        results.append(TestResult("Inventory Quantity After No-Stock", success, msg, scenario))
    except Exception as e:
        results.append(TestResult("Inventory Quantity After No-Stock", False, str(e), scenario))

    return results


def scenario_payment_failure_compensation() -> List[TestResult]:
    scenario = "Scenario 3 - Payment Failure & Compensation"
    section_title(scenario)
    results: List[TestResult] = []

    results.append(seed_inventory(scenario))
    if not results[-1].success:
        return results

    create_res, order_id = create_order(quantity=4, amount=400.0, scenario=scenario, order_tag="O3")
    results.append(create_res)
    if not create_res.success:
        return results

    if order_id is None:
        warn("Skipping async checks because no numeric order id returned.")
        results.append(TestResult("Order Poll Skipped", False, "No numeric order id in create response.", scenario))
        return results

    results.append(wait_for_order_status(order_id, ORDER_FAIL_PAYMENT_STATUSES, scenario))

    section_title("Verify Inventory Rolled Back (Compensation)")
    try:
        item = get_inventory_item(ITEM_SKU)
        qty = item.get("quantity")
        expected = INITIAL_QUANTITY
        success = (qty == expected)
        msg = f"Expected quantity {expected} after compensation, got {qty} (item={item})"
        (ok if success else fail)(msg)
        results.append(TestResult("Inventory Quantity After Payment Fail", success, msg, scenario))
    except Exception as e:
        results.append(TestResult("Inventory Quantity After Payment Fail", False, str(e), scenario))

    results.append(wait_for_payment(order_id, PAYMENT_FAIL_STATUSES, scenario))
    return results


# =========================
# Summary
# =========================

def print_results(results: List[TestResult]):
    print(f"\n{Style.BOLD}================ TEST RESULTS ================ {Style.RESET}")
    passed = 0
    per_scenario: Dict[str, Dict[str, int]] = {}

    for r in results:
        icon = "✅" if r.success else "❌"
        color = Style.GREEN if r.success else Style.RED
        print(f"{color}{icon} {r.name}{Style.RESET}")
        if r.details:
            print(f"    {Style.DIM}{r.details}{Style.RESET}")

        if r.success:
            passed += 1

        if r.scenario:
            per_scenario.setdefault(r.scenario, {"total": 0, "passed": 0})
            per_scenario[r.scenario]["total"] += 1
            if r.success:
                per_scenario[r.scenario]["passed"] += 1

    total = len(results)
    failed = total - passed
    print(f"{Style.BOLD}==============================================={Style.RESET}")
    print(f"Total tests: {total}  |  Passed: {Style.GREEN}{passed}{Style.RESET}  |  Failed: {Style.RED}{failed}{Style.RESET}")
    print(f"{Style.BOLD}===============================================\n{Style.RESET}")

    if per_scenario:
        print(f"{Style.BOLD}Scenario breakdown:{Style.RESET}")
        for scen, agg in per_scenario.items():
            t = agg["total"]
            p = agg["passed"]
            f = t - p
            color = Style.GREEN if f == 0 else (Style.YELLOW if p > 0 else Style.RED)
            print(f"  {color}- {scen}: {p}/{t} passed{Style.RESET}")

    if failed > 0:
        print(f"\n{Style.YELLOW}{Style.BOLD}Troubleshooting hints:{Style.RESET}")
        print(f"{Style.YELLOW}- If orders stay PENDING: consumers may not be running, or RabbitMQ routing is wrong.{Style.RESET}")
        print(f"{Style.YELLOW}- Check RabbitMQ UI: http://localhost:15672 (guest/guest).{Style.RESET}")
        print(f"{Style.YELLOW}- Check logs: docker compose logs -f order_service inventory_service payment_service rabbitmq.{Style.RESET}")
        print()


def main():
    banner()
    info("Waiting for all services to become healthy...")

    if not wait_for_health(ORDER_BASE, "order_service"):
        sys.exit(1)
    if not wait_for_health(INVENTORY_BASE, "inventory_service"):
        sys.exit(1)
    if not wait_for_health(PAYMENT_BASE, "payment_service"):
        sys.exit(1)

    all_results: List[TestResult] = []
    all_results.extend(scenario_happy_path())
    all_results.extend(scenario_insufficient_stock())
    all_results.extend(scenario_payment_failure_compensation())

    print_results(all_results)


if __name__ == "__main__":
    main()
