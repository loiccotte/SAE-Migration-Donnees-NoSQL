#!/usr/bin/env python3
import argparse
import os
import re
import pg8000

def split_sql(sql: str):
    sql = re.sub(r"--.*", "", sql)
    parts = [p.strip() for p in sql.split(";")]
    return [p for p in parts if p]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pg-host",     default=os.environ.get("PG_HOST", "localhost"))
    ap.add_argument("--pg-port",     type=int, default=int(os.environ.get("PG_PORT", "5433")))
    ap.add_argument("--pg-db",       default=os.environ.get("PG_DB"))
    ap.add_argument("--pg-user",     default=os.environ.get("PG_USER"))
    ap.add_argument("--pg-password", default=os.environ.get("PG_PASSWORD"))
    ap.add_argument("--ddl-path",    default=os.environ.get("DDL_PATH", "./sql_ddl_postgres.sql"))
    args = ap.parse_args()

    ddl = open(args.ddl_path, "r", encoding="utf-8").read()
    statements = split_sql(ddl)

    conn = pg8000.connect(
        host=args.pg_host,
        port=args.pg_port,
        database=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
    )
    conn.autocommit = True
    cur = conn.cursor()

    for st in statements:
        cur.execute(st)

    cur.close()
    conn.close()
    print("OK - DDL exécuté (pg8000)")

if __name__ == "__main__":
    main()
