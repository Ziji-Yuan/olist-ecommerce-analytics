"""Streamlit Community Cloud entrypoint for the packaged dashboard."""

from pathlib import Path
import runpy


runpy.run_path(
    str(Path(__file__).resolve().parent / "src" / "dashboard" / "app.py"),
    run_name="__main__",
)
