import io
from pathlib import Path
import re

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory


def migration_scripts():
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    return ScriptDirectory.from_config(config)


def test_existing_database_revision_is_preserved():
    scripts = migration_scripts()
    existing = scripts.get_revision("e1f2a3b4c5d6")
    assert existing.down_revision is None
    assert "init_database" in Path(existing.path).name
    assert scripts.get_revision("e66fcefb25f6").down_revision == existing.revision


def test_upgrade_from_existing_database_skips_applied_history():
    scripts = migration_scripts()
    pending = list(reversed(list(scripts.iterate_revisions("head", "e1f2a3b4c5d6"))))
    assert [revision.revision for revision in pending] == [
        "e66fcefb25f6", "1de46002d80e", "6c0d715350a3", "a8f21d6e930b",
    ]


def test_migration_filenames_match_ids_and_have_one_head():
    scripts = migration_scripts()
    assert scripts.get_heads() == ["a8f21d6e930b"]
    revisions = list(scripts.walk_revisions())
    assert len(revisions) == 5
    for revision in revisions:
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}_" + revision.revision + r"_[a-z0-9_]+\.py",
            Path(revision.path).name,
        )
        assert re.fullmatch(r"[0-9a-f]{12}", revision.revision)


def test_squashed_baseline_creates_tables_without_replaying_renames():
    baseline = migration_scripts().get_revision("e1f2a3b4c5d6").module
    output = io.StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output},
    )
    with Operations.context(context):
        baseline.upgrade()
    sql = output.getvalue()
    assert sql.count("CREATE TABLE ") == 33
    for table in ("User", "Lesson", "Feedback", "FeedbackAttachment", "PracticeProgress", "Notebook"):
        assert f'CREATE TABLE "{table}"' in sql
    assert " RENAME " not in sql
