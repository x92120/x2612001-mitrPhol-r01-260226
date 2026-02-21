#!/usr/bin/env python3
"""
Seed sample prebatch_recs via the FastAPI endpoints for batch recheck testing.
Uses the running backend at localhost:8001.
"""
import json, sys
import urllib.request
import urllib.error

BASE = "http://localhost:8001"

def api_get(path):
    url = f"{BASE}{path}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())

def api_post(path, data):
    url = f"{BASE}{path}"
    payload = json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  POST {path} failed {e.code}: {body[:200]}")
        return None

# ── Fetch a batch with reqs ──────────────────────────────────────────────────
print("Fetching plans...")
plans = api_get("/production-plans/?skip=0&limit=10")

target_batch = None
target_plan = None
for plan in plans:
    for batch in plan.get("batches", []):
        if batch.get("reqs"):
            target_batch = batch
            target_plan = plan
            break
    if target_batch:
        break

if not target_batch:
    print("No batch with requirements found!")
    sys.exit(1)

batch_id = target_batch["batch_id"]
plan_id = target_plan["plan_id"]
reqs = target_batch["reqs"]

print(f"\nUsing batch: {batch_id}")
print(f"Plan: {plan_id}")
print(f"Requirements ({len(reqs)}):")
for r in reqs:
    print(f"  {r['re_code']}: {r['required_volume']} kg (req_id={r['id']})")

# ── Check existing recs ──────────────────────────────────────────────────────
existing = api_get(f"/prebatch-recs/by-batch/{batch_id}")
print(f"\nExisting prebatch_recs: {len(existing)}")

if existing:
    print("Records already exist. Here they are:")
    for r in existing:
        print(f"  {r['batch_record_id']} | {r['re_code']} | pkg {r['package_no']}/{r['total_packages']} | {r['net_volume']} kg")
    print(f"\n✅ Batch {batch_id} is ready for testing.")
    print_qr_codes(batch_id, plan_id, existing)
    sys.exit(0)

# ── Insert records ───────────────────────────────────────────────────────────
print("\nInserting sample prebatch_recs...")
inserted = []

for req in reqs:
    re_code = req["re_code"]
    req_vol = req["required_volume"] or 100.0
    req_id = req["id"]

    # Most ingredients: 1 package. Larger ones: 2-3 packages
    total_pkgs = 1 if req_vol < 10 else (3 if req_vol > 50 else 2)
    per_pkg = round(req_vol / total_pkgs, 4)

    for pkg_no in range(1, total_pkgs + 1):
        batch_record_id = f"{batch_id}-{re_code}-{pkg_no:02d}"
        data = {
            "req_id": req_id,
            "batch_record_id": batch_record_id,
            "plan_id": plan_id,
            "re_code": re_code,
            "package_no": pkg_no,
            "total_packages": total_pkgs,
            "net_volume": per_pkg,
            "total_volume": req_vol,
            "total_request_volume": req_vol,
            "intake_lot_id": f"LOT-{re_code}-2026"
        }
        result = api_post("/prebatch-recs/", data)
        if result:
            print(f"  ✓ {batch_record_id} ({re_code} pkg {pkg_no}/{total_pkgs}, {per_pkg} kg)")
            inserted.append(result)
        else:
            print(f"  ✗ Failed: {batch_record_id}")

print(f"\n✅ Inserted {len(inserted)} prebatch_recs for batch {batch_id}")

# ── Print QR codes for testing ───────────────────────────────────────────────
total_vol = sum(r.get("net_volume", 0) for r in inserted)
print(f"\n=== QR Codes for BatchRecheck Testing ===")
print(f"BOX  QR: {plan_id},{batch_id},BOX,{len(inserted)},{total_vol:.3f}")
print(f"\nBAG  QRs:")
for r in inserted:
    print(f"  {plan_id},{r['batch_record_id']},{r['re_code']},{r['net_volume']}")

def print_qr_codes(batch_id, plan_id, recs):
    total_vol = sum(r.get("net_volume", 0) for r in recs)
    print(f"\n=== QR Codes for BatchRecheck Testing ===")
    print(f"BOX  QR: {plan_id},{batch_id},BOX,{len(recs)},{total_vol:.3f}")
    print(f"\nBAG  QRs:")
    for r in recs:
        print(f"  {plan_id},{r['batch_record_id']},{r['re_code']},{r['net_volume']}")
