import sqlite3

c = sqlite3.connect("data/nifty100.db")

queries = [
    (
        "ratios",
        "EXPLAIN QUERY PLAN "
        "SELECT * FROM financial_ratios "
        "WHERE company_id = ? ORDER BY year",
        ("TCS",),
    ),
    (
        "pl",
        "EXPLAIN QUERY PLAN "
        "SELECT * FROM profitandloss "
        "WHERE company_id = ? ORDER BY year",
        ("TCS",),
    ),
    (
        "bs",
        "EXPLAIN QUERY PLAN "
        "SELECT * FROM balancesheet "
        "WHERE company_id = ? ORDER BY year",
        ("TCS",),
    ),
    (
        "cf",
        "EXPLAIN QUERY PLAN "
        "SELECT * FROM cashflow "
        "WHERE company_id = ? ORDER BY year",
        ("TCS",),
    ),
    (
        "sectors",
        "EXPLAIN QUERY PLAN "
        "SELECT * FROM sectors "
        "WHERE company_id = ?",
        ("TCS",),
    ),
    (
        "peers",
        "EXPLAIN QUERY PLAN "
        "SELECT * FROM peer_groups "
        "WHERE peer_group_name = ?",
        ("IT Services",),
    ),
]

for name, sql, params in queries:
    print(f"\n{name}:")
    for row in c.execute(sql, params).fetchall():
        print(row)

c.close()
