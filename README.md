<div align="center">

<p align="center">
  <img src="assets/icon.svg" width="128" height="128" alt="diskopt icon: SRE guardrail shield on emerald squircle tile">
</p>

# 🚀 diskopt

**High-Performance Storage Optimization & Deterministic SRE Boundary Guard for AI VM Host Infrastructure**

[![Python: 3.10+](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Oracle Cloud](https://img.shields.io/badge/Oracle_Cloud-F80000?style=for-the-badge&logo=oracle&logoColor=white)](https://cloud.oracle.com)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://cloudflare.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen?style=for-the-badge)](LICENSE)

<br>

**[⚡ Quick Start](#-quick-start)** · **[🏗️ Architecture](#️-system-architecture)** · **[🛡️ SRE Guardrails](#-fail-safe-guardrails)** · **[📊 Telemetry](#telemetry--json-mode)**

</div>

---
 is a lightweight, zero-dependency storage optimization CLI and SRE guardrail engine designed for production Linux servers, cloud VM shapes (OCI, AWS, GCP), and AI agent workspaces.

It audits disk usage distribution, detects runway caches (npm, uv, pip, playwright, /tmp), and performs safe, crash-proof pruning protected by non-bypassable filesystem boundary guardrails.

---

## Key Capabilities

- **Zero External Dependencies**: Runs on standard Python 3.10+ without requiring external package installations.
- **Fail-Safe Guardrails**: Strict prohibition rules protect OS root directories (`/`, `/bin`, `/boot`, `/etc`, `/usr`, `/var/lib`) from accidental or destructive deletion commands.
- **Cache-Aware Reclamation**: Safely pinpoints regenerable caches:
  - `~/.cache/uv` (Astral UV wheels & build artifacts)
  - `~/.npm/_cacache` (NPM package store)
  - `~/.cache/pip` (Python package cache)
  - `/tmp/core-js-banners*` (Stale build banner files)
  - Playwright browser staging artifacts
- **Docker Integration**: Optional, safe unreferenced image layer & stopped container pruning (`docker system prune -f`).
- **Telemetry & JSON Mode**: Emits structured JSON metrics for integration into SRE alert pipelines, Grafana, or Telegram bot monitors (`@AzGem_Bot`).

---

## Installation & Quick Start

```bash
# Clone repository
git clone https://github.com/Amz34/diskopt.git
cd diskopt

# Run audit mode
python3 -m diskopt --audit

# Preview cleanable space without touching files (Dry-Run)
python3 -m diskopt --clean --dry-run

# Execute safe guardrailed clean
python3 -m diskopt --clean

# Include Docker cleanup
python3 -m diskopt --clean --with-docker

# Machine-readable JSON output for automated watchdogs
python3 -m diskopt --audit --json
```

---

## Guardrail Architecture

```
                    ┌─────────────────────────────────┐
                    │       diskopt Invocation        │
                    └────────────────┬────────────────┘
                                     │
                     Target candidate identification
                                     │
                                     ▼
                      Is path in OS protected tree?
                       (/, /etc, /usr, /bin, ...)
                                     │
                     ┌───────────────┴───────────────┐
                     │ YES                           │ NO
                     ▼                               ▼
            ┌──────────────────┐           Is path in allowed cache list?
            │ GUARDRAIL BLOCK  │           (~/.cache, ~/.npm, /tmp, ...)
            │  (Refuse delete) │                     │
            └──────────────────┘             ┌───────┴───────┐
                                             │ YES           │ NO
                                             ▼               ▼
                                    ┌────────────────┐ ┌────────────────┐
                                    │ ✅ SAFE PURGE   │ │ ❌ REJECT      │
                                    │ (Execute / dry)│ │ (Outside list) │
                                    └────────────────┘ └────────────────┘
```

---

## Testing

```bash
make test
# Or directly via unittest:
PYTHONPATH=. python3 -m unittest discover -s tests
```

---

## License

MIT © [Aamir Zameer (Amz34)](https://github.com/Amz34)

---

Part of [my always-on agent stack](https://github.com/Amz34) · [Awesome Agent Infrastructure](https://github.com/Amz34/awesome-agent-infrastructure) (135 live-checked building blocks).
