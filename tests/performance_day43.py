import sys
import time
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from src.api.main import app


client = TestClient(app)

ENDPOINTS = [
    "/api/v1/health",
    "/api/v1/companies",
    "/api/v1/companies/TCS",
    "/api/v1/companies/TCS/pl",
    "/api/v1/companies/TCS/bs",
    "/api/v1/companies/TCS/cashflow",
    "/api/v1/companies/TCS/ratios",
    "/api/v1/companies/TCS/tearsheet",
    "/api/v1/screener",
    "/api/v1/sectors",
    "/api/v1/sectors/Information Technology/companies",
    "/api/v1/peers/IT Services",
    "/api/v1/companies/TCS/peers/compare",
    "/api/v1/market-cap/TCS",
    "/api/v1/portfolio/stats",
    "/api/v1/companies/TCS/documents",
]


def benchmark_endpoint(endpoint, runs=10):
    times = []
    statuses = []

    for _ in range(runs):
        start = time.perf_counter()
        response = client.get(endpoint)
        elapsed = time.perf_counter() - start

        times.append(elapsed)
        statuses.append(response.status_code)

    sorted_times = sorted(times)

    return {
        "endpoint": endpoint,
        "runs": runs,
        "min_ms": min(times) * 1000,
        "avg_ms": statistics.mean(times) * 1000,
        "p95_ms": sorted_times[max(0, int(len(sorted_times) * 0.95) - 1)] * 1000,
        "max_ms": max(times) * 1000,
        "statuses": sorted(set(statuses)),
    }


def concurrent_screener(total_requests=50, workers=10):
    def request():
        start = time.perf_counter()
        response = client.get("/api/v1/screener")
        elapsed = time.perf_counter() - start
        return response.status_code, elapsed

    start = time.perf_counter()

    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(request)
            for _ in range(total_requests)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    total_elapsed = time.perf_counter() - start

    times = [elapsed for status, elapsed in results]
    statuses = [status for status, elapsed in results]

    sorted_times = sorted(times)

    return {
        "requests": total_requests,
        "workers": workers,
        "total_seconds": total_elapsed,
        "throughput_rps": total_requests / total_elapsed,
        "min_ms": min(times) * 1000,
        "avg_ms": statistics.mean(times) * 1000,
        "p95_ms": sorted_times[max(0, int(len(sorted_times) * 0.95) - 1)] * 1000,
        "max_ms": max(times) * 1000,
        "statuses": sorted(set(statuses)),
    }


if __name__ == "__main__":
    print("=" * 90)
    print("N100 FINANCIAL INTELLIGENCE - DAY 43 PERFORMANCE BENCHMARK")
    print("=" * 90)

    print("\nAPI ENDPOINT BENCHMARKS")
    print("-" * 90)

    for endpoint in ENDPOINTS:
        result = benchmark_endpoint(endpoint)

        print(
            f"{endpoint:<60} "
            f"avg={result['avg_ms']:>8.2f} ms  "
            f"p95={result['p95_ms']:>8.2f} ms  "
            f"max={result['max_ms']:>8.2f} ms  "
            f"status={result['statuses']}"
        )

    print("\nCONCURRENT SCREENER TEST")
    print("-" * 90)

    load_result = concurrent_screener(
        total_requests=50,
        workers=10,
    )

    print(f"Requests       : {load_result['requests']}")
    print(f"Workers        : {load_result['workers']}")
    print(f"Total time     : {load_result['total_seconds']:.3f} sec")
    print(f"Throughput     : {load_result['throughput_rps']:.2f} requests/sec")
    print(f"Average        : {load_result['avg_ms']:.2f} ms")
    print(f"P95            : {load_result['p95_ms']:.2f} ms")
    print(f"Maximum        : {load_result['max_ms']:.2f} ms")
    print(f"Statuses       : {load_result['statuses']}")

    print("\n" + "=" * 90)
    print("BENCHMARK COMPLETE")
    print("=" * 90)
