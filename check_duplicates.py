import pandas as pd

files = {
    "balancesheet.xlsx": 1,
    "cashflow.xlsx": 1,
    "financial_ratios.xlsx": 0,
    "profitandloss.xlsx": 1
}

for filename, header in files.items():
    df = pd.read_excel("data/raw/" + filename, header=header)

    conflicts = 0

    for key, group in df.groupby(["company_id", "year"]):
        if len(group) > 1:
            values = group.drop(columns=["id"])

            if len(values.drop_duplicates()) > 1:
                conflicts += 1

    print(f"{filename}: conflicting duplicate keys = {conflicts}")