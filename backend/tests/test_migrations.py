"""Guards against a broken Alembic revision graph.

A single linear history must have exactly one head. Two heads (e.g. two
migrations sharing the same ``down_revision``) make ``alembic upgrade head``
fail at container startup with "Multiple head revisions are present" — which
is exactly how #80 broke the Docker boot.
"""
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _script_dir() -> ScriptDirectory:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return ScriptDirectory.from_config(cfg)


def test_single_alembic_head() -> None:
    heads = _script_dir().get_heads()
    assert len(heads) == 1, f"expected one Alembic head, found {len(heads)}: {heads}"


def test_revision_graph_has_no_gaps() -> None:
    """Every down_revision must resolve to a real revision (no dangling parents)."""
    script = _script_dir()
    revisions = {rev.revision for rev in script.walk_revisions()}
    for rev in script.walk_revisions():
        downs = rev.down_revision
        if downs is None:
            continue
        for parent in (downs if isinstance(downs, tuple) else (downs,)):
            assert parent in revisions, f"{rev.revision} points at missing parent {parent}"
