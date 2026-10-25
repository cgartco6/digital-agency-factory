# Digital Agency Factory

An autonomous, CPU-only-host-safe Digital Agency repository driven by a
Meta-Orchestrator swarm. All AI runs against external cloud APIs — no local
GPU models are ever loaded.

## Components

| Component | Path | Purpose |
|---|---|---|
| Meta-Orchestrator | `meta_orchestrator/` | The Mind — plans, spawns, tracks, certifies |
| Branding Studio | `studios/branding/` | Brand identity generation |
| Design Studio | `studios/design/` | Design system generation |
| Marketing Studio | `studios/marketing/` | Campaign planning |
| Core Mesh | `studios/core_mesh/` | Fans out across all studios and reconciles |
| Master Gateway | `gateway.py` | FastAPI — mounts everything |
| Lockdown Guard | `lockdown_check.py` | Halts deployment if any module < 95% coverage |
| Command Center | `command_center/` | Live Streamlit UI for the swarm matrix |

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # add cloud API keys (optional — runs offline-det.)
