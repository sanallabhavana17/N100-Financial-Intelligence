import sqlite3

DB_PATH = "data/nifty100.db"

indexes = [
    (
        "idx_financial_ratios_company_year",
        "CREATE INDEX IF NOT EXISTS "
        "idx_financial_ratios_company_year "
        "ON financial_ratios(company_id, year)",
    ),
    (
        "idx_profitandloss_company_year",
        "CREATE INDEX IF NOT EXISTS "
        "idx_profitandloss_company_year "
        "ON profitandloss(company_id, year)",
    ),
    (
        "idx_balancesheet_company_year",
        "CREATE INDEX IF NOT EXISTS "
        "idx_balancesheet_company_year "
        "ON balancesheet(company_id, year)",
    ),
    (
        "idx_cashflow_company_year",
        "CREATE INDEX IF NOT EXISTS "
        "idx_cashflow_company_year "
        "ON cashflow(company_id, year)",
    ),
    (
        "idx_sectors_company",
        "CREATE INDEX IF NOT EXISTS "
        "idx_sectors_company "
        "ON sectors(company_id)",
    ),
    (
        "idx_peer_groups_name",
        "CREATE INDEX IF NOT EXISTS "
        "idx_peer_groups_name "
        "ON peer_groups(peer_group_name)",
    ),
]

conn = sqlite3.connect(DB_PATH)

try:
    for name, sql in indexes:
        conn.execute(sql)
        print(f"Created/verified: {name}")

    conn.commit()

finally:
    conn.close()

print("\nDatabase indexes updated successfully.")
