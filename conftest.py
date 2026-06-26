import sys
from pathlib import Path

_root = Path(__file__).parent

# Local: project root contains `backend/` → add it so `app.*` imports resolve
_backend = _root / "backend"
if _backend.is_dir() and str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

# Docker: WORKDIR is /app (the backend), tests mount at /tests.
# /app is already in sys.path via the venv, no action needed.
