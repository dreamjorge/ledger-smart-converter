PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'credit_card',
    bank_id TEXT,
    closing_day INTEGER,
    currency TEXT NOT NULL DEFAULT 'MXN',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS imports (
    import_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

-- NOTE: The UNIQUE(pattern) constraint below applies to new databases only.
-- Existing databases cannot have this constraint added via ALTER TABLE in SQLite
-- (table recreation would be required). New DBs get idempotent INSERT OR IGNORE
-- behaviour automatically via the UNIQUE constraint.
CREATE TABLE IF NOT EXISTS rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    pattern TEXT NOT NULL UNIQUE,
    expense TEXT,
    tags TEXT,
    priority INTEGER NOT NULL DEFAULT 100,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_hash TEXT NOT NULL UNIQUE,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'MXN',
    merchant TEXT,
    description TEXT NOT NULL,
    raw_description TEXT,
    normalized_description TEXT,
    account_id TEXT NOT NULL,
    canonical_account_id TEXT NOT NULL,
    bank_id TEXT NOT NULL,
    statement_period TEXT,
    category TEXT,
    tags TEXT,
    transaction_type TEXT NOT NULL DEFAULT 'withdrawal',
    source_name TEXT,
    destination_name TEXT,
    source_file TEXT NOT NULL,
    import_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (canonical_account_id) REFERENCES accounts (account_id),
    FOREIGN KEY (import_id) REFERENCES imports (import_id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_bank_id ON transactions(bank_id);
CREATE INDEX IF NOT EXISTS idx_transactions_canonical_account ON transactions(canonical_account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_period ON transactions(statement_period);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id);

CREATE VIEW IF NOT EXISTS firefly_export AS
SELECT
    id,
    COALESCE(transaction_type, 'withdrawal') AS type,
    date,
    printf('%.2f', amount) AS amount,
    currency AS currency_code,
    description,
    raw_description,
    normalized_description,
    COALESCE(source_name, account_id) AS source_name,
    COALESCE(destination_name, '') AS destination_name,
    COALESCE(category, '') AS category_name,
    COALESCE(tags, '') AS tags,
    bank_id
FROM transactions;

CREATE VIEW IF NOT EXISTS dashboard_metrics AS
SELECT
    COALESCE(statement_period, 'unknown') AS statement_period,
    COALESCE(category, 'Uncategorized')   AS category,
    bank_id,
    COUNT(*)                              AS tx_count,
    ROUND(SUM(amount), 2)                 AS total_amount
FROM transactions
WHERE transaction_type = 'withdrawal'
GROUP BY statement_period, category, bank_id;
