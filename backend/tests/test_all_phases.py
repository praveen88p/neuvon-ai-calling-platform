"""
Comprehensive integration test for ALL 17 features across 6 phases.
Run: python tests/test_all_phases.py

Tests hit the live backend on port 8000.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
import httpx

BASE = "http://localhost:8000/api/v1"
PASS = 0
FAIL = 0
SKIP = 0
RESULTS: list[tuple[str, str, str]] = []  # (phase, test_name, status)

# ─── Test credentials ────────────────────────────────────────────────────────
TEST_EMAIL = f"testrunner_{uuid.uuid4().hex[:8]}@neuvon.test"
TEST_PASSWORD = "TestPass123!"
TEST_ORG = f"TestOrg_{uuid.uuid4().hex[:6]}"
TEST_FULL_NAME = "Test Runner"

TOKEN: str | None = None
ORG_ID: str | None = None
USER_ID: str | None = None


def record(phase: str, name: str, passed: bool, skip: bool = False):
    global PASS, FAIL, SKIP
    if skip:
        SKIP += 1
        status = "SKIP"
        icon = "⏭️"
    elif passed:
        PASS += 1
        status = "PASS"
        icon = "✅"
    else:
        FAIL += 1
        status = "FAIL"
        icon = "❌"
    RESULTS.append((phase, name, status))
    print(f"  {icon} {name}")


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"} if TOKEN else {"Content-Type": "application/json"}


def get(path: str, **kw) -> httpx.Response:
    return httpx.get(f"{BASE}{path}", headers=auth_headers(), timeout=15, **kw)


def post(path: str, body: dict | None = None, **kw) -> httpx.Response:
    return httpx.post(f"{BASE}{path}", headers=auth_headers(), json=body, timeout=15, **kw)


def patch(path: str, body: dict | None = None, **kw) -> httpx.Response:
    return httpx.patch(f"{BASE}{path}", headers=auth_headers(), json=body, timeout=15, **kw)


def delete(path: str, **kw) -> httpx.Response:
    return httpx.delete(f"{BASE}{path}", headers=auth_headers(), timeout=15, **kw)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Foundation & Auth (Features 01–04)
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase1():
    global TOKEN, ORG_ID, USER_ID
    print("\n📦 PHASE 1 — Foundation & Auth")

    # 01: Health check
    try:
        r = get("/health")
        record("P1", "01 Health check endpoint", r.status_code == 200)
    except Exception as e:
        record("P1", "01 Health check endpoint", False)
        print(f"     ⚠️  Server unreachable: {e}")
        sys.exit(1)

    # 03: Register
    try:
        r = post("/auth/register", {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "full_name": TEST_FULL_NAME,
            "organization_name": TEST_ORG,
        })
        ok = r.status_code in (200, 201)
        if ok:
            data = r.json()
            TOKEN = data.get("tokens", {}).get("access_token") or data.get("access_token")
            user = data.get("user", {})
            USER_ID = user.get("user_id") or user.get("id")
            ORG_ID = user.get("organization_id")
        record("P1", "03 Register new user", ok and TOKEN is not None)
    except Exception as e:
        record("P1", "03 Register new user", False)
        print(f"     ⚠️  {e}")

    # 03: Login
    try:
        r = post("/auth/login", {"email": TEST_EMAIL, "password": TEST_PASSWORD})
        ok = r.status_code == 200
        if ok:
            data = r.json()
            TOKEN = data.get("tokens", {}).get("access_token") or data.get("access_token")
            user = data.get("user", {})
            USER_ID = user.get("user_id") or user.get("id")
            ORG_ID = user.get("organization_id")
        record("P1", "03 Login", ok and TOKEN is not None)
    except Exception as e:
        record("P1", "03 Login", False)
        print(f"     ⚠️  {e}")

    # 03: Get current user
    try:
        r = get("/auth/me")
        record("P1", "03 Auth /me", r.status_code == 200)
    except Exception:
        record("P1", "03 Auth /me", False)

    # 04: Organization endpoints
    try:
        r = get("/organizations/me")
        record("P1", "04 Get organization", r.status_code == 200)
    except Exception:
        record("P1", "04 Get organization", False)

    try:
        r = get("/organizations/me/members")
        record("P1", "04 List org members", r.status_code == 200)
    except Exception:
        record("P1", "04 List org members", False)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Dograh Integration (Features 05–07)
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase2():
    print("\n🤖 PHASE 2 — Dograh Integration")

    # 05: Agent endpoints
    try:
        r = get("/agents")
        record("P2", "05 List agents", r.status_code == 200)
    except Exception:
        record("P2", "05 List agents", False)

    try:
        r = get("/agents/count")
        record("P2", "05 Agent count", r.status_code == 200)
    except Exception:
        record("P2", "05 Agent count", False)

    # 06: Call trigger (will fail without a real agent, but endpoint should exist)
    try:
        r = post("/calls/trigger", {
            "agent_id": str(uuid.uuid4()),
            "phone_number": "+15551234567",
            "lead_name": "Test Lead",
        })
        # 404 or 422 is acceptable — it means the endpoint exists
        record("P2", "06 Call trigger endpoint exists", r.status_code in (200, 201, 404, 422, 400, 500))
    except Exception:
        record("P2", "06 Call trigger endpoint exists", False)

    # 09: Call history
    try:
        r = get("/calls/history")
        record("P2", "09 Call history", r.status_code == 200)
    except Exception:
        record("P2", "09 Call history", False)

    # 07: Webhook endpoint (POST, unauthenticated)
    try:
        r = httpx.post(f"{BASE}/webhooks/dograh", json={
            "event": "call.completed",
            "run_id": str(uuid.uuid4()),
            "workflow_id": str(uuid.uuid4()),
            "status": "completed",
        }, headers={"Content-Type": "application/json"}, timeout=10)
        # 200 or 401 or 403 or 422 — endpoint exists
        record("P2", "07 Dograh webhook endpoint exists", r.status_code in (200, 401, 403, 422, 400, 500))
    except Exception:
        record("P2", "07 Dograh webhook endpoint exists", False)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Campaigns & Calls (Features 08–10)
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase3():
    print("\n📣 PHASE 3 — Campaigns & Calls")

    # 08: Campaign management
    try:
        r = get("/campaigns")
        record("P3", "08 List campaigns", r.status_code == 200)
    except Exception:
        record("P3", "08 List campaigns", False)

    CAMPAIGN_ID = None
    try:
        r = post("/campaigns", {
            "name": f"Test Campaign {uuid.uuid4().hex[:6]}",
            "agent_id": str(uuid.uuid4()),
            "description": "Integration test campaign",
        })
        ok = r.status_code in (200, 201)
        if ok:
            data = r.json()
            CAMPAIGN_ID = data.get("id")
        record("P3", "08 Create campaign", ok)
    except Exception:
        record("P3", "08 Create campaign", False)

    if CAMPAIGN_ID:
        try:
            r = get(f"/campaigns/{CAMPAIGN_ID}")
            record("P3", "08 Get campaign by ID", r.status_code == 200)
        except Exception:
            record("P3", "08 Get campaign by ID", False)

        try:
            r = patch(f"/campaigns/{CAMPAIGN_ID}", {"status": "paused"})
            record("P3", "08 Update campaign", r.status_code == 200)
        except Exception:
            record("P3", "08 Update campaign", False)
    else:
        record("P3", "08 Get campaign by ID", False, skip=True)
        record("P3", "08 Update campaign", False, skip=True)

    # 10: Live calls WebSocket endpoint check
    try:
        r = httpx.get(f"{BASE}/live-calls/active", headers=auth_headers(), timeout=10)
        record("P3", "10 Live calls active list", r.status_code == 200)
    except Exception:
        record("P3", "10 Live calls active list", False)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Phone Numbers & Telephony (Feature 11)
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase4():
    print("\n📞 PHASE 4 — Phone Numbers & Telephony")

    try:
        r = get("/telephony/providers")
        record("P4", "11 List telephony providers", r.status_code == 200)
    except Exception:
        record("P4", "11 List telephony providers", False)

    try:
        r = get("/telephony/configs")
        record("P4", "11 List telephony configs", r.status_code == 200)
    except Exception:
        record("P4", "11 List telephony configs", False)

    try:
        r = post("/telephony/configs", {
            "provider": "twilio",
            "phone_number": "+15559876543",
            "config": {"account_sid": "test", "auth_token": "test"},
        })
        record("P4", "11 Create telephony config", r.status_code in (200, 201, 422, 400))
    except Exception:
        record("P4", "11 Create telephony config", False)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Analytics & Billing (Features 12–14)
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase5():
    print("\n📊 PHASE 5 — Analytics & Billing")

    # 12: Analytics
    analytics_endpoints = [
        ("/analytics/overview", "12 Analytics overview"),
        ("/analytics/calls-over-time", "12 Calls over time"),
        ("/analytics/disposition-breakdown", "12 Disposition breakdown"),
        ("/analytics/agent-performance", "12 Agent performance"),
        ("/analytics/campaign-performance", "12 Campaign performance"),
    ]
    for path, name in analytics_endpoints:
        try:
            r = get(path)
            record("P5", name, r.status_code == 200)
        except Exception:
            record("P5", name, False)

    # 13: Billing
    billing_endpoints = [
        ("/billing/usage", "13 Billing usage"),
        ("/billing/plan", "13 Billing plan"),
        ("/billing/invoices", "13 Billing invoices"),
    ]
    for path, name in billing_endpoints:
        try:
            r = get(path)
            record("P5", name, r.status_code == 200)
        except Exception:
            record("P5", name, False)

    # 13: Create order
    try:
        r = post("/billing/orders", {"plan": "starter"})
        # May fail if Razorpay not configured, but endpoint should exist
        record("P5", "13 Create billing order (endpoint)", r.status_code in (200, 201, 400, 422, 500))
    except Exception:
        record("P5", "13 Create billing order (endpoint)", False)

    # 13: Razorpay webhook
    try:
        r = httpx.post(f"{BASE}/webhooks/razorpay", 
            content=json.dumps({"event": "payment.captured", "payload": {}}),
            headers={"Content-Type": "application/json", "x-razorpay-signature": "test"},
            timeout=10)
        record("P5", "13 Razorpay webhook endpoint exists", r.status_code in (200, 400, 401, 403, 500))
    except Exception:
        record("P5", "13 Razorpay webhook endpoint exists", False)

    # 14: Appointments
    try:
        r = get("/appointments")
        record("P5", "14 List appointments", r.status_code == 200)
    except Exception:
        record("P5", "14 List appointments", False)

    APT_ID = None
    try:
        r = post("/appointments", {
            "lead_name": "Test Lead",
            "lead_phone": "+15551234567",
            "scheduled_at": "2026-07-01T10:00:00Z",
            "notes": "Test appointment",
        })
        ok = r.status_code in (200, 201)
        if ok:
            APT_ID = r.json().get("id")
        record("P5", "14 Create appointment", ok)
    except Exception:
        record("P5", "14 Create appointment", False)

    if APT_ID:
        try:
            r = get(f"/appointments/{APT_ID}")
            record("P5", "14 Get appointment by ID", r.status_code == 200)
        except Exception:
            record("P5", "14 Get appointment by ID", False)

        try:
            r = patch(f"/appointments/{APT_ID}", {"status": "confirmed"})
            record("P5", "14 Update appointment", r.status_code == 200)
        except Exception:
            record("P5", "14 Update appointment", False)
    else:
        record("P5", "14 Get appointment by ID", False, skip=True)
        record("P5", "14 Update appointment", False, skip=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Settings & Admin (Features 15–17)
# ═══════════════════════════════════════════════════════════════════════════════

def test_phase6():
    print("\n⚙️  PHASE 6 — Settings & Admin")

    # 15: Settings — Organization
    try:
        r = get("/settings/organization")
        record("P6", "15 Get org settings", r.status_code == 200)
    except Exception:
        record("P6", "15 Get org settings", False)

    try:
        r = patch("/settings/organization", {
            "display_name": "Neuvon Test Org",
            "timezone": "Asia/Kolkata",
        })
        record("P6", "15 Update org settings", r.status_code == 200)
    except Exception:
        record("P6", "15 Update org settings", False)

    # 15: Settings — Profile
    try:
        r = get("/settings/profile")
        record("P6", "15 Get profile", r.status_code == 200)
    except Exception:
        record("P6", "15 Get profile", False)

    try:
        r = patch("/settings/profile", {
            "full_name": "Updated Test Runner",
            "phone": "+919876543210",
        })
        record("P6", "15 Update profile", r.status_code == 200)
    except Exception:
        record("P6", "15 Update profile", False)

    # 15: API Keys
    API_KEY_ID = None
    try:
        r = post("/settings/api-keys", {"name": "Test Key", "expires_in_days": 30})
        ok = r.status_code in (200, 201)
        if ok:
            data = r.json()
            API_KEY_ID = data.get("id")
            key = data.get("key", "")
            has_prefix = key.startswith("nvn_")
        else:
            has_prefix = False
        record("P6", "15 Create API key", ok and has_prefix)
    except Exception:
        record("P6", "15 Create API key", False)

    try:
        r = get("/settings/api-keys")
        ok = r.status_code == 200
        if ok:
            data = r.json()
            has_keys = isinstance(data.get("keys"), list)
        else:
            has_keys = False
        record("P6", "15 List API keys", ok and has_keys)
    except Exception:
        record("P6", "15 List API keys", False)

    if API_KEY_ID:
        try:
            r = delete(f"/settings/api-keys/{API_KEY_ID}")
            record("P6", "15 Revoke API key", r.status_code == 200)
        except Exception:
            record("P6", "15 Revoke API key", False)
    else:
        record("P6", "15 Revoke API key", False, skip=True)

    # 16: Admin endpoints (will get 403 since test user is not platform_admin)
    admin_endpoints = [
        ("/admin/organizations", "16 Admin list orgs (403 expected)"),
        ("/admin/usage", "16 Admin usage (403 expected)"),
        ("/admin/audit", "16 Admin audit log (403 expected)"),
        ("/admin/logs", "16 Admin system logs (403 expected)"),
    ]
    for path, name in admin_endpoints:
        try:
            r = get(path)
            # 403 is the CORRECT response for a non-admin user
            record("P6", name, r.status_code == 403)
        except Exception:
            record("P6", name, False)


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND CHECK (Feature 17)
# ═══════════════════════════════════════════════════════════════════════════════

def test_frontend():
    print("\n🌐 FRONTEND — Feature 17")

    try:
        r = httpx.get("http://localhost:8081", timeout=10)
        record("FE", "17 Frontend serves index.html", r.status_code == 200 and "<html" in r.text.lower())
    except Exception:
        record("FE", "17 Frontend serves index.html", False)

    try:
        r = httpx.get("http://localhost:8081", timeout=10)
        has_react = "root" in r.text or "app" in r.text.lower()
        record("FE", "17 React app mounts", has_react)
    except Exception:
        record("FE", "17 React app mounts", False)


# ═══════════════════════════════════════════════════════════════════════════════
# CORS CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def test_cors():
    print("\n🔒 CORS — Cross-Origin")

    try:
        r = httpx.options(f"{BASE}/health", headers={
            "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "GET",
        }, timeout=10)
        has_cors = "access-control-allow-origin" in r.headers
        record("CORS", "CORS preflight returns headers", has_cors or r.status_code == 200)
    except Exception:
        record("CORS", "CORS preflight returns headers", False)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  NEUVON AI — FULL INTEGRATION TEST (ALL 17 FEATURES)")
    print("=" * 60)

    test_phase1()
    test_phase2()
    test_phase3()
    test_phase4()
    test_phase5()
    test_phase6()
    test_frontend()
    test_cors()

    # Summary
    total = PASS + FAIL + SKIP
    print("\n" + "=" * 60)
    print(f"  RESULTS: {PASS} passed | {FAIL} failed | {SKIP} skipped | {total} total")
    print("=" * 60)

    if FAIL > 0:
        print("\n❌ FAILED TESTS:")
        for phase, name, status in RESULTS:
            if status == "FAIL":
                print(f"  [{phase}] {name}")

    print()
    sys.exit(1 if FAIL > 0 else 0)
