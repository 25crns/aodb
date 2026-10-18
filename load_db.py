"""Load all SQL scripts into the MySQL server configured in .env - no mysql client or Workbench needed.
Works for local MySQL and for Aiven (reads DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_SSL_CA from .env).
Usage:  python load_db.py
WARNING: script 01 drops and recreates the airport_aodb database."""
import os
import sys

import db

SCRIPTS = ["01_create_database", "02_create_tables", "03_insert_data", "05_views",
           "07_triggers", "06_transactions", "09_auth"]
FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")


def statements(text):
    """Split a .sql file into single statements (understands the DELIMITER command)."""
    delim, buf = ";", []
    for raw in text.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s or s.startswith("--") or (s.startswith("/*") and s.endswith("*/")):
            continue
        if s.upper().startswith("DELIMITER "):
            delim = s.split(None, 1)[1].strip()
            continue
        if " -- " in line:
            line = line.split(" -- ")[0].rstrip()
        buf.append(line)
        if line.endswith(delim):
            stmt = "\n".join(buf).rstrip()[:-len(delim)].rstrip()
            buf = []
            if stmt:
                yield stmt
    rest = "\n".join(buf).strip()
    if rest:
        yield rest


def main():
    conn = db._connect(use_db=False)
    conn.autocommit(True)
    cur = conn.cursor()
    for name in SCRIPTS:
        print(f">> {name}.sql", end=" ", flush=True)
        n = 0
        with open(os.path.join(FOLDER, name + ".sql"), encoding="utf-8") as f:
            for stmt in statements(f.read()):
                try:
                    cur.execute(stmt)
                    if cur.description:
                        cur.fetchall()
                except Exception as e:
                    print(f"\n\nFAILED in {name}.sql\n--- statement ---\n{stmt[:400]}\n--- error ---\n{e}")
                    sys.exit(1)
                n += 1
        print(f"({n} statements OK)")
    cur.execute("SELECT"
                " (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='airport_aodb' AND table_type='BASE TABLE') AS tables_,"
                " (SELECT COUNT(*) FROM information_schema.views WHERE table_schema='airport_aodb') AS views_,"
                " (SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='airport_aodb') AS triggers_,"
                " (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema='airport_aodb') AS procedures_")
    r = cur.fetchone()
    print(f"\nDone: {r['tables_']} tables, {r['views_']} views, {r['triggers_']} triggers, {r['procedures_']} procedure(s).")
    print("Expected: 11 tables, 4 views, 6 triggers, 1 procedure.  Next:  python seed_users.py")
    conn.close()


if __name__ == "__main__":
    main()
