# N100 Financial Intelligence

A FinTech financial intelligence dashboard for NIFTY 100 companies.

## Project Overview

This project provides financial analysis, screening, peer comparison, trend analysis, sector analysis, capital allocation analysis, annual-report access, valuation insights, and portfolio intelligence for the NIFTY 100 universe.

## Technology Stack

- Python
- SQLite
- FastAPI
- Streamlit
- Pandas
- NumPy
- Scikit-learn
- ReportLab
- Pytest

## Dashboard

The application is built using Streamlit and uses a SQLite database.

### Run the Dashboard

From the project root:

    streamlit run src/dashboard/app.py

## FastAPI

The project provides a FastAPI backend for financial intelligence and analytics.

### Start the API

    python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000

### Health Check

    Invoke-RestMethod http://127.0.0.1:8000/api/v1/health

## API Endpoints

### Companies

    GET /api/v1/companies
    GET /api/v1/companies/{company_id}
    GET /api/v1/companies/{company_id}/pl
    GET /api/v1/companies/{company_id}/bs
    GET /api/v1/companies/{company_id}/cashflow
    GET /api/v1/companies/{company_id}/ratios
    GET /api/v1/companies/{company_id}/tearsheet

### Analytics

    GET /api/v1/screener
    GET /api/v1/sectors
    GET /api/v1/sectors/{sector}/companies
    GET /api/v1/peers/{group_name}
    GET /api/v1/companies/{company_id}/peers/compare
    GET /api/v1/market-cap/{company_id}
    GET /api/v1/portfolio/stats
    GET /api/v1/companies/{company_id}/documents

## Financial Intelligence

- Financial ratio analysis
- CAGR calculations
- Profitability analysis
- Leverage analysis
- Cash-flow intelligence
- Capital allocation analysis
- Financial screening
- Peer comparison
- Sector analysis
- KMeans company clustering
- Portfolio statistics
- Annual-report access
- Automated PDF tearsheets

## Testing

Run the complete test suite:

    python -m pytest -q

Expected Sprint 6 target: 60+ tests with 0 failures.

## Code Quality

Format source and test code:

    black src/ tests/

Run static checks:

    ruff check src/ tests/

## Analyst Guide

The detailed analyst operating guide is available at:

    docs/analyst_guide.pdf

The guide covers dashboard navigation, screening, company analysis, peer analysis, sector analysis, capital allocation, annual reports, PDF tearsheets, FastAPI usage, troubleshooting, and analyst workflow.

## Data Quality

The project includes validation for required fields, duplicate records, financial years, numeric fields, company references, financial statements, cash flows, market data, documents, sectors, and peer groups.

## Project Status

Sprint 1 through Sprint 5 are complete.

Sprint 6 implementation is complete through Day 43. Day 44 documentation, code-quality checks, acceptance verification, and final packaging are in progress.
