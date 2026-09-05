import httpx
import json
import sys

# Ensure UTF-8 output on Windows terminals (handles emoji in AI responses)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

base = "http://127.0.0.1:8000"

scenarios = [
    ("CUST-1001", "My fiber broadband box has a blinking red optical light and I have no internet."),
    ("CUST-1003", "I see an unexpected data overage charge of $35 on my bill. Can I get a refund?"),
    ("CUST-1004", "I was incorrectly billed $140 for international roaming charges. I want a full refund."),
    ("CUST-1005", "I need help activating my eSIM on my new device."),
    ("CUST-1002", "My broadband speeds are very slow and I am getting poor Wi-Fi connection upstairs."),
    ("CUST-1001", "I want to speak to a human agent please."),
    ("CUST-1001", "Can you explain the Gigabit Pro plan upgrade options?"),
]

print("=" * 70)
print("SupportGenie AI - Live Scenario Smoke Tests")
print("=" * 70)

all_pass = True
for cid, msg in scenarios:
    try:
        r = httpx.post(
            f"{base}/api/chat/message",
            json={"customer_id": cid, "message": msg},
            timeout=15
        )
        d = r.json()
        status = d.get("status", "?")
        ncit = len(d.get("citations", []))
        ticket = d.get("escalation_ticket_id", None)
        is_grounded = d.get("is_grounded", False)
        content_preview = d.get("content", "")[:80].replace("\n", " ")
        print(f"\n[CUST={cid}] Status={status} | Citations={ncit} | Grounded={is_grounded}")
        if ticket:
            print(f"  Ticket: {ticket}")
        print(f"  Msg: {msg[:65]}...")
        print(f"  AI : {content_preview}...")
    except Exception as e:
        print(f"ERROR [{cid}]: {e}")
        all_pass = False

print("\n" + "=" * 70)
print("Checking escalation queue...")
tr = httpx.get(f"{base}/api/tickets", timeout=10)
tickets = tr.json()
print(f"Open escalation tickets in queue: {len(tickets)}")
for t in tickets:
    print(f"  [{t['ticket_id']}] Priority={t['priority']} Reason={t['reason']} Customer={t.get('customer_name','?')}")

print("\n" + "=" * 70)
print("Checking KB articles...")
kr = httpx.get(f"{base}/api/kb/articles", timeout=10)
articles = kr.json()
print(f"KB articles indexed: {len(articles)}")

print("\n" + "=" * 70)
print("SMOKE TEST COMPLETE")
