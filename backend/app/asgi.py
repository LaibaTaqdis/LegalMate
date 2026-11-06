"""ASGI entry point: `uvicorn app.asgi:app`. Importing this module reads backend/.env and fails fast if it is incomplete."""
from .main import create_app

app = create_app()
