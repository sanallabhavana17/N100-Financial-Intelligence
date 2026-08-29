# Sprint 2 Retrospective — Financial Ratio Engine

## Sprint
Sprint 2 — Financial Ratio Engine

## Sprint Goal

Implement and validate the Financial Ratio Engine for the N100 Financial Intelligence Platform, covering profitability, leverage, efficiency, CAGR, cash-flow KPIs, capital allocation, edge cases, and SQLite population.

---

## Completed Work

### Day 08 — Profitability Ratios

- Implemented Net Profit Margin.
- Implemented Operating Profit Margin.
- Added OPM source-field cross-check.
- Implemented Return on Equity.
- Implemented Return on Capital Employed.
- Implemented Return on Assets.
- Added denominator and negative-equity handling.

### Day 09 — Leverage & Efficiency

- Implemented Debt-to-Equity.
- Debt-free companies return D/E = 0.
- Added high-leverage flag for non-Financials.
- Suppressed high-leverage warnings for Financials.
- Implemented Interest Coverage Ratio.
- Added Debt Free ICR label.
- Added ICR warning flag.
- Implemented Net Debt.
- Implemented Asset Turnover.

### Day 10 — CAGR Engine

Implemented 3-year, 5-year and 10-year CAGR calculations for:

- Revenue
- PAT
- EPS

Handled:

- Positive to Positive
- Positive to Negative — DECLINE_TO_LOSS
- Negative to Positive — TURNAROUND
- Negative to Negative — BOTH_NEGATIVE
- Zero Base — ZERO_BASE
- Insufficient history — INSUFFICIENT

CAGR flags are stored separately from CAGR values.

### Day 11 — Cash Flow & Capital Allocation

Implemented:

- Free Cash Flow
- CFO Quality Ratio and classification
- CapEx Intensity and classification
- FCF Conversion
- Capital allocation pattern classifier

Generated:

output/capital_allocation.csv

### Day 12 — SQLite Population

The ratio engine generated:

- 1,073 company-year records
- 92 unique companies
- 46 columns in the SQLite inancial_ratios table
- No duplicate company-year records

All available aligned source company-years were processed.

### Day 13 — Edge Case Investigation

Created:

output/ratio_edge_cases.log

Investigated ROE and ROCE differences against the company-level reference values in companies.xlsx.

Important findings:

- companies.xlsx contains one company-level ROE/ROCE reference value per company.
- The ratio engine calculates annual company-year values.
- Ratio-engine values are retained for analytics.
- Source values are retained as reference/display values.
- Extreme ROCE/ROE values were investigated using the supplied financial statement inputs.
- BEL, HAL, INDIGO and HDFCLIFE contain particularly large computed ROCE values.
- TCS contains an anomalous source ROE value of 0.52% compared with the engine value.
- These differences are documented rather than artificially modifying the formula.

### Financials Sector Carve-Out

The supplied sectors.xlsx classifies 23 companies as Financials, while the sprint specification references 19.

The implementation follows the supplied sectors.xlsx classification.

Validation showed:

- Financials company-year rows: 258
- Financials companies: 23
- Financials rows with D/E > 5: 142
- Incorrect Financials high-leverage flags: 0

Therefore the Financials D/E warning suppression is working correctly.

---

## Testing

Pytest collection:

83 tests collected.

Final result:

83 passed
0 failed

The KPI tests and existing ETL tests are all passing.

---

## Manual Validation

Manual ROE validation was performed for:

- BEL
- TCS
- INFY

The manual calculations matched the ratio-engine values.

Manual 5-year Revenue CAGR validation:

| Company | Manual CAGR | Engine CAGR | Difference |
|---|---:|---:|---:|
| BEL | 10.750806% | 10.750806% | 0.000000% |
| TCS | 10.463615% | 10.463615% | 0.000000% |
| INFY | 13.199101% | 13.199101% | 0.000000% |

All differences are below the required 0.1% tolerance.

---

## Screener Validation

Screener condition:

ROE > 15% AND D/E < 1

2024 result:

38 companies

Required range:

15–50 companies

Result:

PASS

The result set was reviewed and was considered broadly consistent with the intended profitability/leverage screen.

---

## Database Validation

SQLite table:

inancial_ratios

Columns:

46

Rows:

1,073

Unique companies:

92

Duplicate company-year records:

0

All required KPI columns contain non-null values in at least some records.

CAGR columns have legitimate NULL values where the specified edge-case rules apply.

---

## Source Coverage Note

The Sprint exit criterion specifies a target of at least 1,100 rows.

The available aligned P&L source data contains 1,073 unique company-year records, and the ratio engine also contains exactly 1,073 unique company-year records.

Therefore the ratio engine has processed all available aligned P&L company-year records.

No artificial rows were created solely to satisfy the 1,100-row target.

This discrepancy should be reviewed with the team lead as a source-coverage/specification difference.

---

## Formula Decisions

### ROE

ROE uses:

Net Profit / (Equity Capital + Reserves) × 100

Returns None when Equity Capital + Reserves <= 0.

### ROCE

ROCE uses:

EBIT / (Equity Capital + Reserves + Borrowings) × 100

The computed value is retained because it follows the Sprint-defined formula and is reproducible from the supplied financial statements.

### D/E

Debt-to-Equity uses:

Borrowings / (Equity Capital + Reserves)

Debt-free companies return 0.

Financials companies are excluded from the high-leverage warning.

### CAGR

CAGR values are only calculated when the mathematical and historical conditions specified by the sprint are satisfied.

Turnarounds, declines to loss, both-negative periods, zero bases and insufficient history receive explicit flags.

---

## What Went Well

- Ratio formulas were implemented and validated incrementally.
- Edge cases were explicitly investigated instead of hidden.
- Financials-sector leverage behavior was validated against the supplied sector classification.
- Manual calculations matched the engine.
- All 83 automated tests pass.
- Duplicate company-year records were eliminated/verified.
- SQLite population is consistent with the available source coverage.

---

## Issues / Risks

### 1. Row-count target

The database contains 1,073 rows rather than the specified 1,100+.

This is consistent with the available aligned P&L source coverage.

### 2. Source ROE/ROCE differences

The company-level reference ratios in companies.xlsx do not always match the annual ratio-engine calculations.

These differences are documented in:

output/ratio_edge_cases.log

### 3. Extreme ratio values

Several companies have extremely high computed ROE/ROCE values because of the supplied component values and small denominators.

These should remain documented rather than being silently capped or altered.

### 4. Financials count mismatch

The sprint specification references 19 Financials companies, while sectors.xlsx contains 23.

The supplied sector classification is being used.

---

## Sprint 2 Final Status

### Completed

- Profitability ratio engine
- Leverage ratio engine
- Efficiency ratios
- CAGR engine
- Cash-flow KPIs
- Capital allocation classifier
- SQLite financial_ratios population
- Financials leverage carve-out
- ROE/ROCE source comparison
- Edge-case documentation
- Automated tests
- Manual validation
- Screener validation

### Pending Team Lead Review

- Acceptance of 1,073 vs 1,100 row-count difference
- Review/sign-off of ratio edge cases
- Sprint retrospective approval

---

## Definition of Done Assessment

- 1,100+ database rows: ⚠️ Source coverage limitation — 1,073 available
- 14+ KPI columns: PASS
- Required KPI columns not null-only: PASS
- Automated KPI tests: PASS — 83/83
- Manual ROE validation: PASS
- Manual 5-year Revenue CAGR validation: PASS
- Edge-case log: PASS
- Financials D/E carve-out: PASS
- Screener validation: PASS — 38 companies
- Sprint review/sign-off: Pending

---

## Recommended Sprint Review Decision

The Sprint 2 implementation is technically complete against the available source data.

The only unresolved exit criterion is the 1,100-row target, which should be treated as a source-coverage discrepancy because the current source data provides 1,073 aligned company-year records.

Team lead approval is required before marking Sprint 2 fully signed off.

