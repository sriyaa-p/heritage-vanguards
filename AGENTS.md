# Heritage Vanguards — AI Agent Instructions

## What is this file?
This file (`AGENTS.md`) is automatically read by AI coding tools such as
Claude Code, OpenAI Codex, Cursor, Hermes, and Gemini CLI whenever they
open this project folder. It gives every AI assistant the same understanding
of how this project works — so all contributors get consistent behaviour
from their AI tools without any manual setup.

**You do not need to configure anything.** Just open the project in your
AI tool of choice and it will follow the rules below automatically.

---

## Project Overview
**Heritage Sentinel AI** — a multi-agent AI system that helps archaeologists
and heritage experts review potential UNESCO World Heritage Site submissions faster.

Community members submit photos and descriptions of candidate sites. Three AI
agents process each submission and present a structured Confidence Card to a
human expert who makes the final decision. The system never autonomously
designates heritage status — all final decisions remain with human reviewers.

**Hackathon MVP deadline: July 2026**
GitHub: https://github.com/sriyaa-p/heritage-vanguards

---

## Technology Stack
| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| AI | Gemini 2.5 Flash (google-generativeai, google-adk) |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Search | BM25 / FAISS (sentence-transformers, faiss-cpu) |
| Frontend | Next.js, Tailwind CSS |
| Infrastructure | Docker Compose |
| Dataset | UNESCO World Heritage Sites |

---

## Architecture — Three Agent Workflow
```
Community Submission
        │
        ▼
  Intake Processor → Canonical Dossier
        │
        ▼
  RegistryAgent         # Checks UNESCO dataset for duplicates
        │
   Duplicate? ──Yes──▶ Existing Record (workflow ends)
        │ No
        ▼
  EvaluationAgent       # Extracts evidence, generates Heritage Score (0-100)
        │
        ▼
  VerificationAgent     # Creates Confidence Card, waits for human review
        │
   ┌────┴────┐
   ▼         ▼
Approve   Reject
```

---

## Repository Structure
```
heritage-vanguards/
├── backend/            # FastAPI app, agents, models, API routes
├── frontend/           # Next.js + Tailwind CSS
├── data/
│   ├── raw/            # Original UNESCO dataset
│   └── processed/      # Cleaned dataset (unesco_sites_clean.json)
├── scripts/            # seed_database.py and utility scripts
├── tests/              # All test files
├── docs/               # Documentation
├── docker-compose.yml  # Runs the full stack
├── .env.example        # Template for environment variables
└── requirements.txt    # Python dependencies
```

---

## Collaborators
- **sriyaa-p** — repo owner, reviews and merges all PRs
- **Aishwarya Bhangarshettra** (GitHub: Aishwarya29121994) — contributor

> New contributor? Add your name and GitHub handle to this list in your first PR.

---

## Branch Rules
- Never commit directly to main
- Always create a branch for your changes
- Branch naming: `<your-name>-<short-description>`
  - Example: `aishwarya-project-skeleton` or `sriyaa-database-schema`

---

## Commit & PR Rules
- PR title format: `<Short description> - <Your Name>`
- PR description: always explain what changed and why
- Always assign **sriyaa-p** as reviewer
- Never merge your own PR — wait for sriyaa-p to review and merge

---

## Environment Setup
Copy `.env.example` to `.env` and fill in your values before running.
Never commit `.env` — it is in `.gitignore`.

To run the full stack locally:
```bash
cp .env.example .env
docker compose up
```

---

## For New Contributors — Quick Start
1. Clone the repo
2. Copy `.env.example` to `.env` and fill in values
3. Run `docker compose up` — PostgreSQL, FastAPI, and frontend all start
4. Create a branch: `git checkout -b yourname-what-you-are-doing`
5. Make your changes
6. Push and open a PR — title it `What you did - Your Name`
7. Assign sriyaa-p as reviewer and wait for approval before merging

---

## Project Setup — What Has Been Configured
- `AGENTS.md` — this file; shared rules for all AI tools on the team
- Docker Compose — full stack runs with `docker compose up`
- GitHub token configured for authenticated API access (Aishwarya's side)
- Automated weekly check on this file to suggest updates when project evolves

---

## Keeping This File Updated
If project conventions or the tech stack changes, update this file in the
same PR. An automated check runs every Monday at 9am to suggest updates
when the project evolves.
