import re
from typing import Dict, Any, List, Optional, Tuple

class SlotManager:
    """
    Tracks and extracts intent-specific information slots.
    Ensures the assistant asks strictly for missing information without
    asking for details already known from customer account context.
    """

    # Slot definitions per intent category
    SLOT_DEFINITIONS = {
        "billing_complaint": {
            "disputed_item": {
                "description": "the specific telecom charge or service (e.g., roaming, data overage, late fee, modem charge)",
                "prompt": "Could you clarify which charge item or service on your bill you are disputing?",
                "patterns": [
                    r"\b(roaming|overage|data\s+overage|late\s+fee|modem\s+charge|modem\s+fee|equipment\s+fee|extra\s+charge|unrecognized\s+fee|service\s+fee|surcharge)\b"
                ]
            },
            "disputed_amount": {
                "description": "the dollar amount being disputed",
                "prompt": "Could you provide the approximate dollar amount of the charge you wish to dispute?",
                "patterns": [
                    r"\$?([0-9]+(?:\.[0-9]{2})?)\s*(?:dollars|bucks|\$)"
                ]
            }
        },
        "connection_problem": {
            "ont_light_status": {
                "description": "the color/status of the Optical or LOS indicator light",
                "prompt": "Can you check your fiber box (ONT) on the wall and let me know if the 'Optical' or 'LOS' light is red, blinking, green, or off?",
                "patterns": [
                    r"\b(red|blinking\s+red|solid\s+red|green|flashing|off|unlit)\b"
                ]
            }
        },
        "mobile_issue": {
            "device_model": {
                "description": "the smartphone or device model (e.g., iPhone 15, Galaxy S24, Pixel 8)",
                "prompt": "Which device model (e.g., iPhone 15, Galaxy S24) are you using for your mobile service?",
                "patterns": [
                    r"\b(iphone\s*\d+|galaxy\s*s\d+|pixel\s*\d+|samsung|apple|google)\b"
                ]
            }
        },
        "plan_question": {
            "target_plan": {
                "description": "the plan tier or upgrade (e.g., Gigabit Fiber, 500 Mbps, Unlimited Data)",
                "prompt": "Which plan tier or upgrade are you interested in (e.g., 500 Mbps, Gigabit Fiber, Unlimited Data)?",
                "patterns": [
                    r"\b(gigabit|fiber\s*1000|500\s*mbps|300\s*mbps|unlimited|tier\s*upgrade|add-?on)\b"
                ]
            }
        }
    }

    # Backward compatibility aliases
    SLOT_DEFINITIONS["billing_refund"] = SLOT_DEFINITIONS["billing_complaint"]
    SLOT_DEFINITIONS["connection_issue"] = SLOT_DEFINITIONS["connection_problem"]
    SLOT_DEFINITIONS["mobile_esim"] = SLOT_DEFINITIONS["mobile_issue"]

    @classmethod
    def detect_category_and_slots(
        cls,
        user_message: str,
        current_slots: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any], List[str]]:
        """
        Detects inquiry category, updates filled slots, and returns list of missing slot names.
        """
        msg_lower = user_message.lower()
        updated_slots = dict(current_slots)

        # 1. Detect Category
        detected_category = None
        if any(w in msg_lower for w in ["refund", "charge", "overcharge", "dispute", "bill", "credit", "fee", "billing"]):
            detected_category = "billing_complaint"
        elif any(w in msg_lower for w in ["red light", "los", "internet down", "no internet", "slow speed", "wifi", "router", "broadband", "connection"]):
            detected_category = "connection_problem"
        elif any(w in msg_lower for w in ["esim", "sim", "mobile", "roaming", "puk", "cellular", "no signal", "network"]):
            detected_category = "mobile_issue"
        elif any(w in msg_lower for w in ["plan", "upgrade", "downgrade", "tier", "subscription", "contract", "data pack"]):
            detected_category = "plan_question"

        if not detected_category:
            return None, updated_slots, []

        slot_defs = cls.SLOT_DEFINITIONS.get(detected_category, {})

        # 2. Extract values from user message
        for slot_name, slot_info in slot_defs.items():
            if slot_name not in updated_slots or not updated_slots[slot_name]:
                for pat in slot_info["patterns"]:
                    match = re.search(pat, msg_lower)
                    if match:
                        val = match.group(1) if match.groups() else match.group(0)
                        # Clean currency
                        val = val.replace("$", "").strip()
                        updated_slots[slot_name] = val
                        break

        # Check for numeric amount anywhere if billing_complaint or billing_refund
        if detected_category in ["billing_complaint", "billing_refund"] and not updated_slots.get("disputed_amount"):
            num_match = re.search(r"\b\$?([0-9]+(?:\.[0-9]{2})?)\b", user_message)
            if num_match:
                try:
                    amt = float(num_match.group(1))
                    if amt > 0 and amt < 10000:
                        updated_slots["disputed_amount"] = amt
                except ValueError:
                    pass

        # 3. Identify missing slots
        missing_slots = []
        for slot_name in slot_defs.keys():
            if not updated_slots.get(slot_name):
                missing_slots.append(slot_name)

        return detected_category, updated_slots, missing_slots

    @classmethod
    def get_prompt_for_missing_slot(cls, category: str, slot_name: str) -> str:
        """Returns the polite clarification prompt for a missing slot."""
        cat_defs = cls.SLOT_DEFINITIONS.get(category, {})
        slot_info = cat_defs.get(slot_name, {})
        return slot_info.get("prompt", f"Could you provide more details about your {slot_name}?")
