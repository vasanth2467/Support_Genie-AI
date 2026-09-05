-- SupportGenie AI Database Schema

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    verification_status TEXT DEFAULT 'VERIFIED', -- 'VERIFIED', 'UNVERIFIED', 'PENDING_KYC'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    plan_name TEXT NOT NULL,
    category TEXT NOT NULL,                 -- 'BROADBAND', 'MOBILE', 'BUNDLE'
    monthly_rate REAL NOT NULL,
    balance_due REAL DEFAULT 0.00,
    billing_cycle_day INTEGER DEFAULT 1,
    status TEXT DEFAULT 'ACTIVE',           -- 'ACTIVE', 'SUSPENDED', 'OVERDUE'
    data_limit_gb REAL DEFAULT -1,          -- -1 = Unlimited
    data_used_gb REAL DEFAULT 0.0,
    roaming_enabled BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS line_telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL UNIQUE REFERENCES accounts(account_id),
    modem_online BOOLEAN DEFAULT 1,
    optical_rx_power_dbm REAL DEFAULT -19.5, -- < -27 dBm indicates fiber loss
    optical_los_alarm BOOLEAN DEFAULT 0,    -- Loss of Signal (Red light)
    router_ip TEXT,
    area_outage_detected BOOLEAN DEFAULT 0,
    area_outage_eta TEXT,
    last_reboot_timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    channel TEXT DEFAULT 'WEB_PORTAL',
    status TEXT DEFAULT 'ACTIVE',           -- 'ACTIVE', 'RESOLVED', 'ESCALATED'
    category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    sender TEXT NOT NULL,                   -- 'CUSTOMER', 'ASSISTANT', 'SYSTEM'
    content TEXT NOT NULL,
    citations_json TEXT,                    -- JSON array of citations
    slots_json TEXT,                        -- JSON object of current slot values
    is_grounded BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS escalation_tickets (
    ticket_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    priority TEXT NOT NULL,                 -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    category TEXT NOT NULL,
    reason TEXT NOT NULL,
    handover_summary TEXT NOT NULL,
    attempted_steps_json TEXT,
    assigned_agent TEXT,
    status TEXT DEFAULT 'OPEN',             -- 'OPEN', 'IN_PROGRESS', 'RESOLVED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS kb_articles (
    article_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,                 -- 'billing', 'connection', 'mobile', 'plans'
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    policy_code TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
