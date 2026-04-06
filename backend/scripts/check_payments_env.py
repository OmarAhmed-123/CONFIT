#!/usr/bin/env python3
"""
Offline payment env audit for CONFIT.
Reads .env / .env.example and validates payment configuration without
printing secrets or making network calls.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


PLACEHOLDER_RE = re.compile(
    r"(your-|change-me|example|placeholder|pk_test_mock|sk_test_mock)",
    re.IGNORECASE,
)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_env(path: Path) -> Tuple[Dict[str, str], Dict[str, List[int]]]:
    data: Dict[str, str] = {}
    first_line: Dict[str, int] = {}
    dups: Dict[str, List[int]] = {}
    if not path.exists():
        return data, dups

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines, 1):
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith("#") or raw.startswith(";") or raw.startswith("//"):
            continue
        if "=" not in raw:
            continue
        key, val = raw.split("=", 1)
        key = key.strip()
        val = _strip_quotes(val.strip())
        if key in data:
            dups.setdefault(key, [first_line[key]]).append(idx)
        else:
            first_line[key] = idx
        data[key] = val
    return data, dups


def is_placeholder(value: str) -> bool:
    if not value:
        return True
    return bool(PLACEHOLDER_RE.search(value))


def has_value(env: Dict[str, str], key: str) -> bool:
    return bool(env.get(key, "").strip())


def looks_test_key(value: str) -> bool:
    v = value.strip()
    return (
        v.startswith("sk_test_")
        or v.startswith("pk_test_")
        or v.startswith("egy_sk_test")
        or v.startswith("egy_pk_test")
    )


def looks_live_key(value: str) -> bool:
    v = value.strip()
    return (
        v.startswith("sk_live_")
        or v.startswith("pk_live_")
        or v.startswith("egy_sk_live")
        or v.startswith("egy_pk_live")
    )


def check_numeric(env: Dict[str, str], key: str) -> bool:
    val = env.get(key, "").strip()
    return bool(val) and val.isdigit()


def audit_env(env: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
    errors: List[str] = []
    warns: List[str] = []
    oks: List[str] = []

    allow_mock = env.get("ALLOW_MOCK_PAYMENTS", "").strip().lower() in ("1", "true", "yes")
    if allow_mock:
        warns.append("ALLOW_MOCK_PAYMENTS=true (mock payments enabled)")
    else:
        oks.append("ALLOW_MOCK_PAYMENTS is disabled")

    # Stripe
    sk = env.get("STRIPE_SECRET_KEY", "").strip()
    pk = env.get("STRIPE_PUBLISHABLE_KEY", "").strip()
    if not sk or not pk:
        errors.append("Stripe: missing STRIPE_SECRET_KEY or STRIPE_PUBLISHABLE_KEY")
    else:
        if looks_test_key(sk) or looks_test_key(pk):
            warns.append("Stripe: test keys detected (not live)")
        if not (sk.startswith("sk_") and pk.startswith("pk_")):
            warns.append("Stripe: key format looks unusual")
        oks.append("Stripe: keys present")

    # Paymob
    if not has_value(env, "PAYMOB_API_KEY"):
        errors.append("Paymob: missing PAYMOB_API_KEY")
    if not check_numeric(env, "PAYMOB_INTEGRATION_ID"):
        errors.append("Paymob: PAYMOB_INTEGRATION_ID missing or not numeric")
    if not check_numeric(env, "PAYMOB_IFRAME_ID"):
        warns.append("Paymob: PAYMOB_IFRAME_ID missing or not numeric (iframe checkout will fail)")
    hmac = env.get("PAYMOB_HMAC_SECRET", "").strip()
    secret_key = env.get("PAYMOB_SECRET_KEY", "").strip()
    if not hmac and not secret_key:
        errors.append("Paymob: missing PAYMOB_HMAC_SECRET / PAYMOB_SECRET_KEY (webhook verification)")
    else:
        oks.append("Paymob: HMAC/secret present")
    if secret_key and looks_test_key(secret_key):
        warns.append("Paymob: test secret key detected (not live)")
    if env.get("PAYMOB_PUBLIC_KEY", "").strip() and looks_test_key(env.get("PAYMOB_PUBLIC_KEY", "")):
        warns.append("Paymob: test public key detected (not live)")

    # PayPal
    if not has_value(env, "PAYPAL_CLIENT_ID") or not has_value(env, "PAYPAL_CLIENT_SECRET"):
        errors.append("PayPal: missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET")
    mode = env.get("PAYPAL_MODE", "sandbox").strip().lower()
    if mode not in ("sandbox", "live"):
        warns.append("PayPal: PAYPAL_MODE must be sandbox or live")
    elif mode == "sandbox":
        warns.append("PayPal: PAYPAL_MODE=sandbox (not live)")
    else:
        oks.append("PayPal: PAYPAL_MODE=live")
    if not has_value(env, "PAYPAL_WEBHOOK_ID"):
        warns.append("PayPal: PAYPAL_WEBHOOK_ID missing (webhook verification will fail)")

    return errors, warns, oks


def detect_secrets_in_example(env_example: Dict[str, str]) -> List[str]:
    payment_keys = [
        "STRIPE_SECRET_KEY",
        "STRIPE_PUBLISHABLE_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "PAYMOB_API_KEY",
        "PAYMOB_INTEGRATION_ID",
        "PAYMOB_HMAC_SECRET",
        "PAYMOB_SECRET_KEY",
        "PAYMOB_PUBLIC_KEY",
        "PAYMOB_IFRAME_ID",
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_WEBHOOK_ID",
    ]
    leaks = []
    for k in payment_keys:
        v = env_example.get(k, "").strip()
        if v and not is_placeholder(v):
            leaks.append(k)
    return leaks


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="CONFIT payment env audit (offline)")
    parser.add_argument("--env", default=str(root / ".env"), help="Path to backend .env")
    parser.add_argument(
        "--example", default=str(root / ".env.example"), help="Path to backend .env.example"
    )
    args = parser.parse_args()

    env_path = Path(args.env)
    ex_path = Path(args.example)

    env, env_dups = parse_env(env_path)
    ex, ex_dups = parse_env(ex_path)

    print("CONFIT payments env audit (offline)")
    print(f"- env: {env_path} {'(missing)' if not env_path.exists() else '(ok)'}")
    print(f"- example: {ex_path} {'(missing)' if not ex_path.exists() else '(ok)'}")
    print("")

    if env_dups:
        print("WARN: duplicate keys in .env (last value wins):")
        for k, lines in env_dups.items():
            print(f"  - {k} (lines {', '.join(str(n) for n in lines)})")
        print("")
    if ex_dups:
        print("WARN: duplicate keys in .env.example (last value wins):")
        for k, lines in ex_dups.items():
            print(f"  - {k} (lines {', '.join(str(n) for n in lines)})")
        print("")

    leaks = detect_secrets_in_example(ex)
    if leaks:
        print("ERROR: payment secrets detected in .env.example (should be placeholders only):")
        for k in leaks:
            print(f"  - {k}")
        print("")

    errors, warns, oks = audit_env(env or ex)

    if oks:
        print("OK:")
        for msg in oks:
            print(f"  - {msg}")
        print("")
    if warns:
        print("WARN:")
        for msg in warns:
            print(f"  - {msg}")
        print("")
    if errors:
        print("ERROR:")
        for msg in errors:
            print(f"  - {msg}")
        print("")

    if errors or leaks:
        print("Status: FAIL")
        return 1
    if warns:
        print("Status: WARN")
        return 2
    print("Status: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
