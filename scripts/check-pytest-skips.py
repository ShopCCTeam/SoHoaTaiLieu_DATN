#!/usr/bin/env python3
"""Fail CI when pytest skips exceed an explicit allowlist and ceiling."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIPPED_SUMMARY_PATTERN = re.compile(r"^SKIPPED \[(?P<count>\d+)\].*?: (?P<reason>.+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="pytest output captured with -ra")
    parser.add_argument(
        "--allow-reason",
        action="append",
        default=[],
        help="Exact permitted pytest skip reason; repeat for each reason.",
    )
    parser.add_argument(
        "--max-skips", type=int, required=True, help="Maximum permitted skip count."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_skips < 0:
        print("--max-skips must be non-negative", file=sys.stderr)
        return 2

    allowed_reasons = set(args.allow_reason)
    skip_reasons: list[tuple[int, str]] = []
    for line in args.report.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SKIPPED_SUMMARY_PATTERN.match(line)
        if match:
            skip_reasons.append((int(match.group("count")), match.group("reason")))

    total_skips = sum(count for count, _ in skip_reasons)
    unexpected_reasons = [reason for _, reason in skip_reasons if reason not in allowed_reasons]

    if total_skips > args.max_skips or unexpected_reasons:
        print(
            "pytest skip gate failed: "
            f"total={total_skips}, maximum={args.max_skips}, "
            f"unexpected_reasons={unexpected_reasons}",
            file=sys.stderr,
        )
        return 1

    print(
        "pytest skip gate passed: "
        f"total={total_skips}, maximum={args.max_skips}, reasons={len(skip_reasons)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
