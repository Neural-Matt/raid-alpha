"""Vercel Python entrypoint — re-exports the FastAPI app defined in app.py."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402
