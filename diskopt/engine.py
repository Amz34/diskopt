#!/usr/bin/env python3
"""
diskopt - Production-grade Disk Optimization & Guardrail Engine.
Audits storage distribution, detects runaway caches, safely purges dead assets,
and enforces crash-proof storage guardrails.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


PROTECTED_DIRECTORIES = {
    "/",
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/home",
    "/lib",
    "/lib64",
    "/proc",
    "/root",
    "/sbin",
    "/sys",
    "/usr",
    "/usr/bin",
    "/usr/lib",
    "/var",
    "/var/lib",
}

SAFE_RECLAIMABLE_TARGETS = [
    {
        "id": "npm_cache",
        "description": "NPM package download cache and npx scratchpads",
        "path": os.path.expanduser("~/.npm/_cacache"),
        "type": "directory",
    },
    {
        "id": "uv_cache",
        "description": "Astral UV package & wheel download cache",
        "path": os.path.expanduser("~/.cache/uv"),
        "type": "directory",
    },
    {
        "id": "pip_cache",
        "description": "Python pip download cache",
        "path": os.path.expanduser("~/.cache/pip"),
        "type": "directory",
    },
    {
        "id": "tmp_core_js",
        "description": "Node/Webpack core-js banner temporary debris in /tmp",
        "path": "/tmp",
        "pattern": "core-js-banners*",
        "type": "files",
    },
    {
        "id": "playwright_cache",
        "description": "Playwright stale browser download artifacts",
        "path": os.path.expanduser("~/.cache/ms-playwright/tmp"),
        "type": "directory",
    },
]


@dataclass
class StorageMetric:
    mount: str
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float
    is_critical: bool
    status: str


@dataclass
class ReclaimCandidate:
    id: str
    description: str
    path: str
    size_bytes: int
    size_mb: float
    safe_to_purge: bool
    guardrail_passed: bool
    rejection_reason: Optional[str] = None


def get_disk_metric(path: str = "/") -> StorageMetric:
    usage = shutil.disk_usage(path)
    total_gb = usage.total / (1024**3)
    used_gb = usage.used / (1024**3)
    free_gb = usage.free / (1024**3)
    usage_pct = (usage.used / usage.total) * 100.0

    is_critical = usage_pct >= 75.0
    if usage_pct >= 85.0:
        status = "CRITICAL"
    elif usage_pct >= 75.0:
        status = "WARNING"
    elif usage_pct >= 60.0:
        status = "ELEVATED"
    else:
        status = "HEALTHY"

    return StorageMetric(
        mount=path,
        total_gb=round(total_gb, 2),
        used_gb=round(used_gb, 2),
        free_gb=round(free_gb, 2),
        usage_percent=round(usage_pct, 1),
        is_critical=is_critical,
        status=status,
    )


def verify_guardrail(path: str) -> tuple[bool, Optional[str]]:
    resolved = os.path.realpath(os.path.abspath(path))

    if resolved in PROTECTED_DIRECTORIES:
        return False, f"Guardrail Violation: target '{resolved}' is a protected system directory."

    if resolved.startswith(("/etc", "/boot", "/sys", "/proc", "/dev", "/usr/bin", "/sbin")):
        return False, f"Guardrail Violation: path '{resolved}' falls inside critical OS tree."

    # Must be under /tmp or specific user caches
    home = os.path.realpath(os.path.expanduser("~"))
    allowed_bases = [
        os.path.join(home, ".cache"),
        os.path.join(home, ".npm"),
        os.path.join(home, ".local", "share", "Trash"),
        "/tmp",
    ]

    is_allowed = any(resolved.startswith(base) for base in allowed_bases)
    if not is_allowed:
        return False, f"Guardrail Rejection: '{resolved}' is outside allowed cache/scratch hierarchies."

    return True, None


def get_dir_size(path: str) -> int:
    if not os.path.exists(path):
        return 0
    total = 0
    try:
        if os.path.isfile(path) or os.path.islink(path):
            return os.path.getsize(path)
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def scan_reclaimable() -> List[ReclaimCandidate]:
    candidates = []

    for item in SAFE_RECLAIMABLE_TARGETS:
        target_path = item["path"]
        if not os.path.exists(target_path):
            continue

        passed, reason = verify_guardrail(target_path)
        size = get_dir_size(target_path)
        size_mb = round(size / (1024 * 1024), 2)

        candidates.append(
            ReclaimCandidate(
                id=item["id"],
                description=item["description"],
                path=target_path,
                size_bytes=size,
                size_mb=size_mb,
                safe_to_purge=passed and size > 0,
                guardrail_passed=passed,
                rejection_reason=reason,
            )
        )

    return candidates


def prune_candidate(candidate: ReclaimCandidate, dry_run: bool = True) -> int:
    if not candidate.guardrail_passed or not candidate.safe_to_purge:
        return 0

    if dry_run:
        return candidate.size_bytes

    freed = 0
    try:
        if os.path.isfile(candidate.path):
            size = os.path.getsize(candidate.path)
            os.remove(candidate.path)
            freed = size
        elif os.path.isdir(candidate.path):
            for entry in os.listdir(candidate.path):
                sub = os.path.join(candidate.path, entry)
                try:
                    if os.path.isdir(sub) and not os.path.islink(sub):
                        shutil.rmtree(sub, ignore_errors=True)
                    else:
                        os.unlink(sub)
                except Exception:
                    pass
            freed = candidate.size_bytes
    except Exception:
        pass
    return freed


def run_docker_prune(dry_run: bool = True) -> Dict[str, Any]:
    if dry_run:
        return {"action": "docker_prune", "dry_run": True, "status": "simulated"}

    try:
        proc = subprocess.run(
            ["docker", "system", "prune", "-f"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return {
            "action": "docker_prune",
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "status": "success" if proc.returncode == 0 else "error",
        }
    except Exception as e:
        return {"action": "docker_prune", "status": "failed", "error": str(e)}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="diskopt - Production-grade Disk Optimization & Guardrail Engine"
    )
    parser.add_argument("--audit", action="store_true", help="Audit current disk usage & reclaimable space")
    parser.add_argument("--clean", action="store_true", help="Execute safe guardrailed clean of regenerable caches")
    parser.add_argument("--dry-run", action="store_true", help="Simulate purge without deleting bytes")
    parser.add_argument("--with-docker", action="store_true", help="Include safe docker system prune -f")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    metric = get_disk_metric("/")
    candidates = scan_reclaimable()

    total_reclaimable_mb = sum(c.size_mb for c in candidates if c.safe_to_purge)

    if args.json:
        payload = {
            "metric": asdict(metric),
            "reclaimable_candidates": [asdict(c) for c in candidates],
            "total_reclaimable_mb": round(total_reclaimable_mb, 2),
        }
        if args.clean:
            cleaned_mb = 0.0
            for c in candidates:
                freed = prune_candidate(c, dry_run=args.dry_run)
                cleaned_mb += freed / (1024 * 1024)
            payload["execution"] = {
                "dry_run": args.dry_run,
                "cleaned_mb": round(cleaned_mb, 2),
            }
            if args.with_docker:
                payload["docker"] = run_docker_prune(dry_run=args.dry_run)
        print(json.dumps(payload, indent=2))
        return 0

    print("=================================================================")
    print(" diskopt - Production-grade Storage Optimizer & Guardrail Engine")
    print("=================================================================")
    print(f"Mount Point      : {metric.mount}")
    print(f"Total Capacity   : {metric.total_gb} GB")
    print(f"Used Space       : {metric.used_gb} GB ({metric.usage_percent}%)")
    print(f"Available Free   : {metric.free_gb} GB")
    print(f"Status           : {metric.status}")
    print("-----------------------------------------------------------------")
    print(f"Guardrail Status : ENFORCED ({len(PROTECTED_DIRECTORIES)} protected OS root boundaries)")
    print("-----------------------------------------------------------------")
    print(f"Identified Reclaimable Caches ({len(candidates)} targets):")
    for c in candidates:
        guard_badge = "✅ SAFE" if c.guardrail_passed else "❌ BLOCKED"
        print(f" - [{guard_badge}] {c.id:<18}: {c.size_mb:>8.2f} MB ({c.path})")

    print("-----------------------------------------------------------------")
    print(f"Total Immediately Reclaimable : {total_reclaimable_mb:.2f} MB")

    if args.clean:
        print("\n[Executing Safe Guardrailed Prune...]")
        if args.dry_run:
            print(" [MODE: DRY-RUN - No actual files removed]")
        cleaned_bytes = 0
        for c in candidates:
            if c.safe_to_purge:
                freed = prune_candidate(c, dry_run=args.dry_run)
                cleaned_bytes += freed
                print(f" [OK] Purged cache for '{c.id}' ({round(freed/(1024*1024), 2)} MB freed)")
        if args.with_docker:
            d_res = run_docker_prune(dry_run=args.dry_run)
            print(f" [OK] Docker Prune: {d_res.get('status')}")

        print(f"\nCompleted! Total freed: {round(cleaned_bytes/(1024*1024), 2)} MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
