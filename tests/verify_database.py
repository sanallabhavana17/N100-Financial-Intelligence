import sqlite3

DB_PATH = "data/nifty100.db"

expected_tables = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "market_cap",
    "peer_groups",
]

con = sqlite3.connect(DB_PATH)

print("=" * 50)
print("FINAL DATABASE VERIFICATION")
print("=" * 50)

# Check tables
tables = [
    row[0]
    for row in con.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' ORDER BY name"
    )
]

print("\nTABLES:")
for table in tables:
    print(f"  {table}")

missing = set(expected_tables) - set(tables)

print("\nTABLE CHECK:")
if not missing:
    print("PASSED - All 12 required tables exist")
else:
    print("FAILED - Missing tables:", sorted(missing))

# Row counts
print("\nROW COUNTS:")
for table in expected_tables:
    count = con.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]
    print(f"  {table:20} {count}")

# Foreign keys
print("\nFOREIGN KEY CHECK:")
fk_errors = con.execute("PRAGMA foreign_key_check").fetchall()

if not fk_errors:
    print("PASSED - 0 violations")
else:
    print(f"FAILED - {len(fk_errors)} violations")
    for error in fk_errors:
        print(error)

print("\n" + "=" * 50)
print("VERIFICATION COMPLETE")
print("=" * 50)

con.close()