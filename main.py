"""
Ramz - A modular cryptocurrency services web application.
This project is built using the Massir framework.
"""
import asyncio
import sys
from pathlib import Path

# Add the main project path to sys.path
MASSIR_ROOT = Path(__file__).parent.parent.joinpath("massir_project").resolve()
CURRENT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from massir import App

async def main():
    """
    Main entry point for the Ramz cryptocurrency web application.
    """
    app = App(
        settings_path="app_settings.json",
        app_dir=CURRENT_ROOT
    )
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass