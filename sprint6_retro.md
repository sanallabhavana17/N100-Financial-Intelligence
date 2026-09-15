\# Sprint 6 Retrospective — N100 Financial Intelligence



\## Sprint Overview



Sprint 6 focused on finalizing the N100 Financial Intelligence platform through

clustering, advanced analytics, FastAPI APIs, performance optimization, testing,

documentation, final QA, and acceptance-gate validation.



\---



\## Completed Work



\### Day 36 — Company Clustering



\- Implemented company clustering using financial and operational KPIs.

\- Used:

&#x20; - Return on Equity

&#x20; - Debt-to-Equity

&#x20; - Revenue CAGR

&#x20; - FCF CAGR

&#x20; - Operating Profit Margin

\- Implemented sector-median imputation for missing values.

\- Applied feature scaling and K-Means clustering.

\- Evaluated cluster counts using an elbow plot.

\- Assigned all 92 companies to five clusters.



Generated:



\- output/cluster\_labels.csv

\- reports/elbow\_plot.png



\### Day 37 — Analytics \& Portfolio Intelligence



Generated:



\- output/cluster\_profiles.csv

\- output/kpi\_correlation.csv

\- output/sector\_outliers.csv

\- output/portfolio\_statistics.csv

\- reports/correlation\_heatmap.png

\- output/outlier\_report.csv

\- output/portfolio\_stats.csv



Implemented portfolio-level KPI statistics and sector/market-cap

distribution analysis.



\### Day 38 — FastAPI Foundation



Implemented the FastAPI application with:



\- Health monitoring

\- Company APIs

\- Analytics APIs

\- CORS configuration

\- Request logging

\- OpenAPI documentation



Verified:



\- `/api/v1/health` returns HTTP 200.

\- FastAPI documentation is available through `/docs`.



\### Day 39 — Company APIs



Implemented company-level API endpoints for:



\- Company listing

\- Company profile

\- Profit \& Loss

\- Balance Sheet

\- Cash Flow

\- Financial Ratios

\- Company Tearsheet



Added filtering support for:



\- Sector

\- Market-cap category

\- Company search

\- Year/date ranges



Validated the APIs using representative company data.



\### Day 40 — Analytics APIs



Implemented APIs for:



\- Financial Screener

\- Sector analysis

\- Sector companies

\- Peer groups

\- Peer comparison

\- Market-cap history

\- Portfolio statistics

\- Company documents



Validated that the API screener matches the Excel screener output.



\### Day 41 — Automated Testing



Implemented and executed automated API, ETL, KPI and DQ tests.



Final regression result:



\- 155 tests passed

\- 0 failures



Generated:



reports/pytest\_report.html



\### Day 42 — Quality \& Integration Validation



\- Validated API integration with existing financial intelligence modules.

\- Verified company, sector, peer and portfolio analytics.

\- Validated generated outputs and API responses.

\- Confirmed required project components were integrated into the final

&#x20; deliverables.



\### Day 43 — Performance Optimization



Implemented database indexing and performance benchmarking.



Added indexes for frequently queried:



\- Company/year financial data

\- Sector/company relationships

\- Peer-group data

\- Peer percentile lookups



Performance testing covered the major API endpoints.



Concurrent screener testing achieved:



\- 54.29 requests/second

\- 0.921 seconds total execution time

\- 95th percentile response time of approximately 204 ms

\- All requests returned HTTP 200



Dashboard performance testing remained well below the required 3-second

company-profile target.



Generated:



\- tests/performance\_day43.py

\- tests/dashboard\_performance\_day43.py

\- tests/query\_plan\_day43.py

\- tests/add\_indexes\_day43.py

\- reports/day43\_performance.md



\### Day 44 — Documentation \& Code Quality



Completed project documentation and code-quality improvements.



Implemented:



\- README documentation

\- Analyst guide

\- OpenAPI specification

\- Postman collection

\- Pytest HTML report

\- Black formatting

\- Ruff linting



Final Ruff result:



\- All checks passed



Generated:



\- docs/analyst\_guide.pdf

\- docs/openapi.json

\- docs/postman\_collection.json

\- reports/pytest\_report.html



\### Day 45 — Final QA \& Acceptance



Performed final project-wide validation against 20 acceptance gates.



Final result:



\- 18 acceptance gates passed

\- 2 acceptance gates failed



\---



\## Acceptance Gate Exceptions



\### AC-04 — Financial Ratio Record Count



Status: \*\*FAIL\*\*



The acceptance requirement specifies at least 1,100 financial-ratio

company-year records.



The final database contains:



\- 1,073 financial-ratio records



The source data was not fabricated or artificially expanded to satisfy the

threshold.



\### AC-06 — ROE Source Cross-Check



Status: \*\*FAIL\*\*



The acceptance requirement specifies that the ROE cross-check should have at

least 4 of 5 sampled companies within a 5% difference.



Final result:



\- 1 of 5 samples passed the 5% tolerance.



The discrepancy was documented as a source-data mismatch. The source data was

not modified or fabricated to force the acceptance gate to pass.



\---



\## Data Exceptions



\### Sector Count Difference



The Sprint specification refers to 11 broad sectors, while the project

database contains 10 broad sectors.



The available database sectors were used as-is rather than fabricating an

additional sector.



\### Historical Data Coverage



Some companies have limited historical financial data.



The final validation showed:



\- 84 of 92 companies meet the required >=10-year history criterion.

\- 91.3% of companies satisfy the historical coverage requirement.



These exceptions were documented during final QA.



\---



\## Final Validation Results



The following major acceptance gates passed:



\- 92 companies available

\- Historical coverage requirement met

\- Foreign-key validation passed

\- TCS 5-year revenue CAGR validated

\- Quality Compounder screener validated

\- Company Profile performance requirement passed

\- Required CSV outputs validated

\- Tearsheet generation validated

\- Health API returned HTTP 200

\- TCS ratios cover 2013–2024

\- API screener matches Excel screener

\- 11 peer groups populated

\- 92 companies clustered

\- 92 companies have pros/cons coverage

\- 92 tearsheets generated

\- 155 automated tests passed

\- Validation-failure report generated

\- Analyst guide generated successfully



\---



\## What Went Well



\- Successfully integrated analytics with FastAPI.

\- All 92 companies were processed by the clustering pipeline.

\- API endpoints were implemented and performance-tested.

\- Database indexes improved query performance.

\- Automated testing remained stable with 155 tests passing.

\- Ruff and Black checks were completed successfully.

\- Final documentation and analyst materials were generated.

\- No source data was fabricated to artificially satisfy acceptance thresholds.



\---



\## Challenges Encountered



\- Financial-ratio source coverage was below the specified threshold.

\- ROE source values showed discrepancies for several sampled companies.

\- The database contains 10 broad sectors while the specification refers to 11.

\- Some companies have limited historical financial coverage.

\- Final PDF and API validation required multiple integration and performance

&#x20; checks.



\---



\## Lessons Learned



\- Acceptance criteria should be validated against the actual source dataset

&#x20; early in the development cycle.

\- Data-quality limitations should be documented instead of being hidden or

&#x20; artificially corrected.

\- Database indexing is important for API performance when multiple analytical

&#x20; endpoints query historical financial data.

\- Automated tests provide reliable regression protection during large

&#x20; multi-sprint projects.

\- Generated financial reports require both programmatic and visual validation.

\- Source-data discrepancies must be distinguished from calculation errors.



\---



\## What Could Be Improved



\- Improve source financial-ratio data coverage to meet the 1,100-record target.

\- Investigate and reconcile ROE source-data discrepancies.

\- Align sector definitions between the specification and database.

\- Improve historical financial coverage for companies with shorter histories.

\- Add more automated dashboard visual regression tests.

\- Continue improving API and dashboard performance monitoring.

\- Complete formal team-lead acceptance and sign-off.



\---



\## Sprint 6 Outcome



The major Sprint 6 technical deliverables were implemented, integrated,

tested, documented and performance-validated.



Final acceptance result:



\*\*18 of 20 acceptance gates passed.\*\*



AC-04 and AC-06 remain failed because of documented source-data limitations.

No source data was fabricated or altered solely to satisfy the acceptance

criteria.



The final project deliverables and documentation were prepared for team-lead

review.



\---



\## Action Items



1\. Demonstrate the final project to the team lead.

2\. Obtain acknowledgement of the AC-04 financial-ratio coverage deviation.

3\. Obtain acknowledgement of the AC-06 ROE source-data discrepancy.

4\. Explain the 10-sector database versus 11-sector specification difference.

5\. Review historical-data coverage exceptions.

6\. Obtain team-lead feedback and formal sign-off.

7\. Carry approved improvements into future project iterations.



\---



\## Final Status



Technical implementation: \*\*Completed\*\*



Testing: \*\*Completed — 155 passed, 0 failures\*\*



Documentation: \*\*Completed\*\*



Final QA: \*\*Completed\*\*



Acceptance Gates: \*\*18/20 Passed\*\*



Source-data exceptions: \*\*Documented\*\*



Team Lead Review: \*\*Pending\*\*



Team Lead Sign-off: \*\*Pending\*\*

