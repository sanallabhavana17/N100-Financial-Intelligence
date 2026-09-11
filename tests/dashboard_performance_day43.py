import sys
import time
import statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_pl,
    get_pros_cons,
)

TICKERS = ["TCS", "RELIANCE", "HDFCBANK", "INFY", "ITC"]


def benchmark_ticker(ticker, runs=5):
    times = []

    # Clear Streamlit cache so each measured run represents
    # the dashboard data-loading path rather than cached data.
    get_companies.clear()
    get_ratios.clear()
    get_pl.clear()
    get_pros_cons.clear()

    for _ in range(runs):
        start = time.perf_counter()

        companies = get_companies()
        ratios = get_ratios(ticker)
        pl = get_pl(ticker)
        pros_cons = get_pros_cons(ticker)

        elapsed = time.perf_counter() - start
        times.append(elapsed)

        # Basic correctness check
        assert not companies.empty
        assert not ratios.empty
        assert not pl.empty

    return {
        "ticker": ticker,
        "runs": runs,
        "avg_ms": statistics.mean(times) * 1000,
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
        "rows_ratios": len(ratios),
        "rows_pl": len(pl),
        "rows_pros_cons": len(pros_cons),
    }


if __name__ == "__main__":
    print("=" * 90)
    print("N100 FINANCIAL INTELLIGENCE - DAY 43 DASHBOARD BENCHMARK")
    print("=" * 90)
    print("\nCompany Profile data-loading benchmark")
    print("5 representative Nifty 100 tickers, 5 runs each")
    print("-" * 90)

    results = []

    for ticker in TICKERS:
        result = benchmark_ticker(ticker)
        results.append(result)

        print(
            f"{ticker:<12} "
            f"avg={result['avg_ms']:>8.2f} ms  "
            f"min={result['min_ms']:>8.2f} ms  "
            f"max={result['max_ms']:>8.2f} ms  "
            f"ratios={result['rows_ratios']:>4}  "
            f"PL={result['rows_pl']:>4}  "
            f"pros/cons={result['rows_pros_cons']:>3}"
        )

    overall_avg = statistics.mean(
        result["avg_ms"] for result in results
    )

    worst = max(
        results,
        key=lambda result: result["avg_ms"]
    )

    print("\n" + "-" * 90)
    print(f"Overall average: {overall_avg:.2f} ms")
    print(
        f"Worst ticker: {worst['ticker']} "
        f"({worst['avg_ms']:.2f} ms)"
    )

    print("\nAcceptance target: Company Profile < 3 seconds")
    print(
        "Result: PASS"
        if worst["avg_ms"] < 3000
        else "Result: REVIEW REQUIRED"
    )

    print("\n" + "=" * 90)
    print("DASHBOARD BENCHMARK COMPLETE")
    print("=" * 90)
