---
article_id: KB-MOB-02
category: mobile
title: SIM Card PIN Unlock Key (PUK) Retrieval Security Guidelines
keywords: puk code, puk, sim locked, enter puk, pin blocked, sim card locked
last_updated: 2026-03-01
policy_code: POL-MOB-302
---

# SIM Card PIN Unlock Key (PUK) Retrieval

## 1. Important Warning
Entering an incorrect PUK code **10 consecutive times** permanently destroys the SIM card chip, requiring a physical SIM replacement.

## 2. Security & Verification Requirements
- PUK codes cannot be disclosed to unverified or guest callers.
- **Mandatory Verification**: Before revealing the 8-digit PUK code, the assistant must verify:
  1. Primary account holder's registered mobile number.
  2. 4-digit Account Security PIN or billing address zip code.

## 3. Retrieval Protocol
- Once identity is verified against `customers.verification_status == 'VERIFIED'`, display the 8-digit PUK 1 code securely.
- Advise customer: "Enter the 8-digit code carefully, then set a new 4-digit SIM PIN of your choice."
- If the customer has already exhausted 10 attempts and the SIM is permanently invalidated, route to Mobile Dispatch for urgent express SIM replacement.
