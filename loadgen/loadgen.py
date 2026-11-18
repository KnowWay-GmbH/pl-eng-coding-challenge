#!/usr/bin/env python3
"""Send a mix of POST/GET traffic to the API and print a status summary."""
import argparse
import json
import random
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

AGENTS = ["planner", "coder", "reviewer", "deployer"]


def one_request(base_url, i):
    if i % 2 == 0:
        body = json.dumps({
            "agent": random.choice(AGENTS),
            "status": random.choice(["completed", "failed"]),
            "duration_ms": random.randint(50, 5000),
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/runs", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
    else:
        req = urllib.request.Request(f"{base_url}/runs")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = "error"
    return code, time.perf_counter() - start


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:8080")
    p.add_argument("--requests", type=int, default=200)
    p.add_argument("--concurrency", type=int, default=4)
    args = p.parse_args()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda i: one_request(args.url, i), range(args.requests)))
    elapsed = time.perf_counter() - started

    codes = Counter(code for code, _ in results)
    latencies = sorted(t for _, t in results)
    print(f"requests:    {len(results)} in {elapsed:.1f}s ({len(results) / elapsed:.0f} req/s)")
    for code, n in sorted(codes.items(), key=lambda kv: str(kv[0])):
        print(f"status {code}: {n:5d} ({100 * n / len(results):.1f}%)")
    print(f"latency p50: {latencies[len(latencies) // 2] * 1000:.0f} ms")
    print(f"latency p95: {latencies[int(len(latencies) * 0.95)] * 1000:.0f} ms")


if __name__ == "__main__":
    main()
