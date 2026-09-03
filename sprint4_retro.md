# Sprint 4 Retrospective

## Sprint 4 — Dashboard & Valuation

### Completed

- D22 — Streamlit scaffold
- D23 — Home and Company Profile
- D24 — Screener and Peer Comparison
- D25 — Trend Analysis, Sector Analysis, Capital Allocation and Annual Reports
- D26 — Valuation
- D27 — Dashboard QA
- D28 — Documentation and retrospective

### Dashboard

Completed 8 required screens:

1. Home
2. Company Profile
3. Financial Screener
4. Peer Comparison
5. Trend Analysis
6. Sector Analysis
7. Capital Allocation
8. Annual Reports

Additional screen:

9. Valuation

### Valuation Results

- 92 companies processed
- 28 valuation columns
- 29 Caution companies
- 30 Discount companies
- 33 Neutral companies
- FCF Yield generated for all 92 companies

### QA

All required dashboard screens were manually tested.

Automated regression test result:

107 passed

### Issues Fixed

- Corrected Trend Analysis revenue source from the invalid `revenue_cr` column to `profitandloss.sales`.
- Added safe handling for text-based numeric financial fields.
- Tested negative FCF and missing-data cases.
- Validated valuation outputs.

### What Went Well

- Streamlit dashboard successfully integrated the existing financial analysis.
- Interactive Plotly charts were added.
- Company, peer, sector and year filters work.
- Automated tests remained green.

### Future Improvements

- Further improve visual styling.
- Add more automated UI tests.
- Add a dashboard walkthrough video if required.

## Final Status

**Sprint 4 COMPLETE**
