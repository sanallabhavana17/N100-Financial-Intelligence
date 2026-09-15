# Sprint 5 Retrospective — N100 Financial Intelligence

## Sprint Overview

Sprint 5 focused on adding Natural Language Processing, Cash Flow Intelligence,
Capital Allocation analysis, automated company tearsheets, sector reports,
and portfolio-level reporting for the N100 Financial Intelligence project.

## What Went Well

- Generated automated pros/cons analysis covering all 92 companies.
- Implemented confidence-based NLP rules for company strengths and weaknesses.
- Built Cash Flow Intelligence with CFO quality, CapEx intensity, FCF metrics,
  distress indicators, and deleveraging indicators.
- Added Capital Allocation classification and pattern-change analysis.
- Generated individual company tearsheets for all 92 companies.
- Generated a 92-page portfolio summary with one page per company.
- Added sector-level PDF reports based on the sectors present in the project database.
- Maintained automated testing and quality checks throughout the sprint.
- Integrated the outputs into the final project deliverables and documentation.

## Challenges Encountered

### Sector Count Difference

The Sprint 5 specification refers to 11 sectors, while the current N100 project
database contains 10 broad sectors. Therefore, 10 sector reports were generated
from the available database sectors rather than fabricating an additional sector.

### Company Data Coverage

Some companies have limited historical financial data. This affected historical
trend calculations and report generation for a small number of companies.

### Report Generation

Generating 92 individual company tearsheets and the portfolio summary required
careful handling of missing values, historical coverage, formatting, and PDF
layout.

## Lessons Learned

- Financial datasets must be validated before applying analytical rules.
- Missing historical data needs explicit handling instead of being silently treated
  as zero.
- Financial ratios should be interpreted according to company/sector context.
- Automated PDF generation requires both programmatic validation and visual review.
- Output counts and coverage checks are important for large financial datasets.
- Reproducible scripts and automated tests reduce manual verification effort.

## What Could Be Improved

- Improve historical data completeness for companies with shorter available histories.
- Reconcile the sector definition/count between the sprint specification and the
  project database.
- Add stronger validation for source financial ratios and derived metrics.
- Increase automated visual regression testing for generated PDFs.
- Add more detailed validation for NLP confidence and rule coverage.
- Improve documentation of data exceptions and assumptions.

## Sprint 5 Outcome

The major Sprint 5 technical deliverables were implemented and validated,
including NLP analysis, Cash Flow Intelligence, Capital Allocation analysis,
company tearsheets, and portfolio reporting.

The remaining project-level review items are team-lead demonstration/sign-off and
formal acknowledgement of the sector-count/data-coverage deviations.

## Action Items

1. Demonstrate Sprint 5 deliverables to the team lead.
2. Explain the 10-sector database versus 11-sector specification difference.
3. Review the historical-data exceptions.
4. Obtain team-lead feedback and sign-off.
5. Carry approved changes into the next sprint.

## Final Status

Technical implementation: Completed

Documentation: Completed

Team Lead Review: Pending

Team Lead Sign-off: Pending
