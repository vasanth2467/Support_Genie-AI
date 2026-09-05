---
article_id: KB-CONN-01
category: connection
title: Fibre ONT Red Optical / LOS Light Troubleshooting Guide
keywords: red light, los light, optical light, internet down, blinking red, fibre cut, no internet
last_updated: 2026-03-01
policy_code: POL-TECH-101
---

# Fibre ONT Red Optical / LOS Light Troubleshooting Guide

## 1. Symptom Identification
The Optical Network Terminal (ONT) is the white fiber-to-the-home interface box installed on the wall. 
- A **solid or blinking RED light on the 'OPTICAL' or 'LOS' (Loss of Signal) indicator** signifies that the optical receiver is not receiving a laser signal from the central office splitter.

## 2. Step-by-Step Resolution Workflow
1. **Check Area Outage**: Check system telemetry. If an area outage is declared, advise customer that technicians are already repairing the local trunk fiber and DO NOT perform equipment resets.
2. **Inspect Fibre Patch Cable**:
   - Locate the thin fiber cable (usually yellow or white) connecting the wall outlet to the green SC/APC port on the ONT.
   - Verify that the green connector is firmly clicked into place.
   - Check that the cable has no tight kinks, sharp 90-degree bends, or physical pinch damage.
3. **Power Cycle Procedure**:
   - Disconnect the ONT 12V power adapter from the electrical outlet.
   - Wait 30 seconds to allow all onboard capacitors to discharge completely.
   - Reconnect power and wait 2 to 3 minutes for optical synchronization.
4. **Escalation Protocol**:
   - If the LOS light remains solid red and line telemetry reports optical Rx power below **-27.0 dBm** (e.g. -29 dBm or disconnected), this indicates an external line break or street cabinet disconnect.
   - **Action**: Immediately escalate for a Field Technician Truck Roll to repair physical fiber.
