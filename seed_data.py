import os
import json
import re
from pathlib import Path
from app.config import settings
from app.database.connection import get_db, init_db

BASE_DIR = Path(__file__).resolve().parent

def parse_frontmatter(content: str):
    """Simple parser for YAML frontmatter in markdown files."""
    frontmatter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_fm = parts[1].strip()
            body = parts[2].strip()
            for line in raw_fm.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    frontmatter[key.strip()] = val.strip()
    return frontmatter, body

def seed_database():
    print("--- Initializing SupportGenie SQLite Database ---")
    init_db()

    with get_db() as conn:
        # Check if already seeded
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customers;")
        cust_count = cursor.fetchone()[0]

        if cust_count == 0:
            print("Seeding customer accounts and telemetry...")
            customers_file = BASE_DIR / "app" / "data" / "seed_customers.json"
            if customers_file.exists():
                with open(customers_file, "r", encoding="utf-8") as f:
                    customers = json.load(f)

                for c in customers:
                    conn.execute(
                        """
                        INSERT INTO customers (customer_id, full_name, email, phone, address, verification_status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (c["customer_id"], c["full_name"], c["email"], c["phone"], c["address"], c.get("verification_status", "VERIFIED"))
                    )

                    acc = c.get("account")
                    if acc:
                        conn.execute(
                            """
                            INSERT INTO accounts (account_id, customer_id, plan_name, category, monthly_rate, balance_due, billing_cycle_day, status, data_limit_gb, data_used_gb, roaming_enabled)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (acc["account_id"], c["customer_id"], acc["plan_name"], acc["category"], acc["monthly_rate"], acc["balance_due"], acc["billing_cycle_day"], acc["status"], acc["data_limit_gb"], acc["data_used_gb"], 1 if acc.get("roaming_enabled") else 0)
                        )

                    tel = c.get("telemetry")
                    if tel and acc:
                        conn.execute(
                            """
                            INSERT INTO line_telemetry (account_id, modem_online, optical_rx_power_dbm, optical_los_alarm, router_ip, area_outage_detected, area_outage_eta, last_reboot_timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (acc["account_id"], 1 if tel["modem_online"] else 0, tel["optical_rx_power_dbm"], 1 if tel["optical_los_alarm"] else 0, tel.get("router_ip"), 1 if tel.get("area_outage_detected") else 0, tel.get("area_outage_eta"), tel.get("last_reboot_timestamp"))
                        )
                print(f"Successfully seeded {len(customers)} customer profiles.")
        else:
            print(f"Database already contains {cust_count} customers. Skipping customer seeding.")

        # Seed KB Articles
        cursor.execute("SELECT COUNT(*) FROM kb_articles;")
        kb_count = cursor.fetchone()[0]

        if kb_count == 0:
            print("Seeding Knowledge Base articles from markdown files...")
            kb_dir = BASE_DIR / "app" / "data" / "kb_articles"
            md_files = list(kb_dir.rglob("*.md"))
            seeded_kb = 0

            for md_path in md_files:
                with open(md_path, "r", encoding="utf-8") as f:
                    text = f.read()

                fm, body = parse_frontmatter(text)
                article_id = fm.get("article_id") or md_path.stem
                category = fm.get("category") or md_path.parent.name
                title = fm.get("title") or md_path.stem.replace("_", " ").title()
                keywords = fm.get("keywords", "")
                policy_code = fm.get("policy_code", "")

                # Derive brief summary from first section
                summary_lines = [l for l in body.splitlines() if l.strip() and not l.startswith("#")]
                summary = summary_lines[0] if summary_lines else title

                conn.execute(
                    """
                    INSERT INTO kb_articles (article_id, category, title, summary, content, keywords, policy_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (article_id, category, title, summary, body, keywords, policy_code)
                )
                seeded_kb += 1

            print(f"Successfully seeded {seeded_kb} knowledge base articles.")
        else:
            print(f"Database already contains {kb_count} knowledge base articles.")

    print("--- Database Setup Complete ---")

if __name__ == "__main__":
    seed_database()
