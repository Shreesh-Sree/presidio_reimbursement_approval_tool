import os, subprocess, tempfile, time, signal, sys
from pathlib import Path
import postgresql_binaries

BIN = postgresql_binaries.bin()
BACKEND = Path("/home/shreesh/Documents/presidio_reimbursement_approval_tool/.claude/worktrees/feat-phase-0-foundation/backend")

tmp = Path(tempfile.mkdtemp(prefix="pgtest_"))
data = tmp / "data"; sock = tmp / "sock"; sock.mkdir()

def run(*a): subprocess.run(a, check=True)

run(str(BIN/"initdb"), "-D", str(data), "-U", "postgres", "-A", "trust")
proc = subprocess.Popen([str(BIN/"postgres"), "-D", str(data), "-k", str(sock), "-h", "", "-p", "5433"])
try:
    for _ in range(60):
        if subprocess.run([str(BIN/"pg_isready"), "-h", str(sock), "-p", "5433"]).returncode == 0: break
        time.sleep(0.5)
    run(str(BIN/"createdb"), "-h", str(sock), "-p", "5433", "-U", "postgres", "app")
    db_url = f"postgresql+psycopg://postgres@/app?host={sock}&port=5433"
    sys.path.insert(0, str(BACKEND))
    os.environ.update(DATABASE_URL=db_url, JWT_SECRET="x", S3_BUCKET="b")
    from alembic.config import Config
    from alembic import command
    import sqlalchemy as sa
    from app.core.database import Base
    cfg = Config(str(BACKEND/"alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND/"alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")
    eng = sa.create_engine(db_url); insp = sa.inspect(eng)
    actual = set(insp.get_table_names()); expected = set(Base.metadata.tables.keys())
    assert not (expected - actual), f"MISSING: {sorted(expected-actual)}"
    with eng.connect() as c:
        assert c.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname='pgcrypto'")).scalar(), "no pgcrypto"
    print(f"UPGRADE OK: {len(actual & expected)} tables, pgcrypto present")
    command.downgrade(cfg, "base"); insp = sa.inspect(eng)
    assert not (set(insp.get_table_names()) & expected), "downgrade dirty"
    print("DOWNGRADE OK: clean"); eng.dispose()
    print("REAL POSTGRES MIGRATION TEST PASSED")
finally:
    proc.send_signal(signal.SIGINT); proc.wait(timeout=30)
