#!/usr/bin/env python3
import argparse
import csv
import os
import pg8000


# Mapping table -> (colonnes, fichier)
TABLES = [
    ("region", ["id_region","nom_region"], "region.csv"),
    ("departement", ["code_dept","nom_dept","id_region"], "departement.csv"),
    ("service", ["code_service","nom_service","code_dept"], "service.csv"),
    ("perimetre", ["id_perimetre","nom_perimetre"], "perimetre.csv"),
    # appartient.csv = relation N-N Service <-> Perimetre
    ("service_perimetre", ["code_service","id_perimetre"], "appartient.csv"),
    ("infraction", ["code_index","libelle"], "infraction.csv"),
    ("enregistrement", ["id_enregistrement","annee","nb_faits","code_service","code_index"], "enregistrement.csv"),
]

def batched(it, n=5000):
    buf = []
    for x in it:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir",     default=os.environ.get("CSV_DIR", "./csv"))
    ap.add_argument("--pg-host",     default=os.environ.get("PG_HOST", "localhost"))
    ap.add_argument("--pg-port",     type=int, default=int(os.environ.get("PG_PORT", "5433")))
    ap.add_argument("--pg-db",       default=os.environ.get("PG_DB"))
    ap.add_argument("--pg-user",     default=os.environ.get("PG_USER"))
    ap.add_argument("--pg-password", default=os.environ.get("PG_PASSWORD"))
    args = ap.parse_args()

    conn = pg8000.connect(
        host=args.pg_host,
        port=args.pg_port,
        database=args.pg_db,
        user=args.pg_user,
        password=args.pg_password,
    )
    conn.autocommit = True
    cur = conn.cursor()

    for table, cols, csv_name in TABLES:
        path = os.path.join(args.csv_dir, csv_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV manquant: {path}")

        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)

        # Import résilient (évite crash si doublons)
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            def row_iter():
                for r in reader:
                    row = [r.get(c, None) for c in cols]
                    if table == "enregistrement":
                        # nb_faits = index 2
                        try:
                            row[2] = int(float(row[2])) if row[2] not in (None, "") else 0
                        except Exception:
                            row[2] = 0
                    yield row

            total = 0
            for batch in batched(row_iter(), 5000):
                cur.executemany(sql, batch)
                total += len(batch)

        print(f"OK - {table} <- {csv_name} ({total} lignes)")

    cur.close()
    conn.close()
    print("OK - Chargement terminé (pg8000)")

if __name__ == "__main__":
    main()