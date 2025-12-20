from alembic import command
from alembic.config import Config
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

def run_migrations(revision: str = "head"):
    alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location",
        str(BASE_DIR / "alembic"),
    )

    command.upgrade(alembic_cfg, revision)
