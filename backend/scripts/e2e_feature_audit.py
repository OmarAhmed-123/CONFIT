import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database.session import SessionLocal
from database.models import AppRole, User, UserRole


BASE_URL = "http://127.0.0.1:8000"
PASSWORD = "ConfitTest123"


@dataclass
class CheckResult:
    role: str
    feature: str
    method: str
    path: str
    status: int
    ok: bool
    detail: str = ""


def ensure_user(email: str, name: str) -> str:
    login_payload = {"email": email, "password": PASSWORD}
    r = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload, timeout=60)
    if r.status_code == 200:
        token = r.json().get("token") or ""
        if token:
            return token

    reg_payload = {
        "name": name,
        "email": email,
        "password": PASSWORD,
    }
    requests.post(f"{BASE_URL}/api/auth/register", json=reg_payload, timeout=60)
    r2 = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload, timeout=60)
    r2.raise_for_status()
    token = r2.json().get("token") or ""
    if not token:
        raise RuntimeError(f"Could not get token for {email}")
    return token


def set_role(email: str, role: AppRole) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return
        rows = db.query(UserRole).filter(UserRole.user_id == user.id).all()
        if rows:
            for row in rows:
                row.role = role
        else:
            db.add(UserRole(user_id=user.id, role=role))
        db.commit()
    finally:
        db.close()


def call(
    role: str,
    feature: str,
    method: str,
    path: str,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
) -> CheckResult:
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=90)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=body or {}, timeout=90)
        elif method == "PUT":
            r = requests.put(url, headers=headers, json=body or {}, timeout=90)
        else:
            raise ValueError(f"Unsupported method: {method}")
        return CheckResult(
            role=role,
            feature=feature,
            method=method,
            path=path,
            status=r.status_code,
            ok=r.status_code == 200,
            detail=r.text[:240] if r.status_code != 200 else "",
        )
    except Exception as e:
        return CheckResult(role, feature, method, path, status=0, ok=False, detail=str(e))


def main() -> None:
    customer_email = "customer.e2e@confit.com"
    owner_email = "owner.e2e@confit.com"
    admin_email = "admin.e2e@confit.com"

    customer_token = ensure_user(customer_email, "E2E Customer")
    owner_token = ensure_user(owner_email, "E2E Owner")
    admin_token = ensure_user(admin_email, "E2E Admin")

    set_role(owner_email, AppRole.brand_manager)
    set_role(admin_email, AppRole.admin)

    # refresh tokens after role update
    owner_token = ensure_user(owner_email, "E2E Owner")
    admin_token = ensure_user(admin_email, "E2E Admin")

    checks: List[CheckResult] = []

    # Customer flows
    checks.extend(
        [
            call("customer", "auth_me", "GET", "/api/auth/me", customer_token),
            call("customer", "products", "GET", "/api/products/featured?limit=3&gender=women"),
            call("customer", "orders", "GET", "/api/orders", customer_token),
            call("customer", "notifications_customer", "GET", "/api/notifications/customer", customer_token),
            call("customer", "notification_prefs_get", "GET", "/api/notification-preferences", customer_token),
            call("customer", "analytics_overview", "GET", "/api/analytics/overview", customer_token),
            call(
                "customer",
                "stylist_chat",
                "POST",
                "/api/stylist/chat",
                customer_token,
                {"message": "Need a smart casual look", "occasion": "casual", "budget": "$120"},
            ),
            call("customer", "tryon_capabilities", "GET", "/api/tryon/capabilities"),
        ]
    )

    # Store owner flows
    checks.extend(
        [
            call("owner", "stores", "GET", "/api/stores", owner_token),
            call("owner", "sales_analytics", "GET", "/api/sales-analytics", owner_token),
            call("owner", "owner_notifications", "GET", "/api/notifications", owner_token),
            call("owner", "notif_prefs_update", "PUT", "/api/notification-preferences", owner_token, {}),
            call("owner", "payment_config", "GET", "/api/payments/config"),
            call(
                "owner",
                "payment_intent",
                "POST",
                "/api/payments/intent",
                owner_token,
                {"order_id": "e2e-mock-order"},
            ),
        ]
    )

    # Admin flows
    checks.extend(
        [
            call("admin", "debug_health", "GET", "/debug/health"),
            call("admin", "debug_alerts", "GET", "/debug/alerts"),
            call("admin", "debug_scheduler", "GET", "/debug/scheduler/status"),
            call("admin", "debug_logs", "GET", "/api/debug/logs?limit=5"),
            call("admin", "analytics_metrics", "GET", "/api/analytics/metrics", admin_token),
        ]
    )

    passed = [c for c in checks if c.ok]
    failed = [c for c in checks if not c.ok]

    print(f"TOTAL={len(checks)} PASS={len(passed)} FAIL={len(failed)}")
    for c in checks:
        status = "PASS" if c.ok else "FAIL"
        print(f"{status} [{c.role}] {c.feature} {c.method} {c.path} -> {c.status}")
        if c.detail and not c.ok:
            print(f"  detail: {c.detail.replace(chr(10), ' ')[:200]}")

    report = {
        "summary": {"total": len(checks), "pass": len(passed), "fail": len(failed)},
        "results": [c.__dict__ for c in checks],
    }
    with open("e2e_feature_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
