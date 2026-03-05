#!/usr/bin/env python3
import argparse
import os
import pg8000
from neo4j import GraphDatabase

def chunks(rows, size=1500):
    buf = []
    for r in rows:
        buf.append(r)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pg-host",     default=os.environ.get("PG_HOST", "localhost"))
    ap.add_argument("--pg-port",     type=int, default=int(os.environ.get("PG_PORT", "5433")))
    ap.add_argument("--pg-db",       default=os.environ.get("PG_DB"))
    ap.add_argument("--pg-user",     default=os.environ.get("PG_USER"))
    ap.add_argument("--pg-password", default=os.environ.get("PG_PASSWORD"))

    ap.add_argument("--neo-uri",      default=os.environ.get("NEO_URI", "bolt://localhost:7687"))
    ap.add_argument("--neo-user",     default=os.environ.get("NEO_USER", "neo4j"))
    ap.add_argument("--neo-password", default=os.environ.get("NEO_PASSWORD", "admin1234"))
    ap.add_argument("--neo-db",       default=os.environ.get("NEO_DB", "Crimes"))
    ap.add_argument("--truncate-neo4j", action="store_true")
    args = ap.parse_args()

    pg = pg8000.connect(
        host=args.pg_host, port=args.pg_port, database=args.pg_db,
        user=args.pg_user, password=args.pg_password
    )
    pg.autocommit = True
    cur = pg.cursor()

    driver = GraphDatabase.driver(args.neo_uri, auth=(args.neo_user, args.neo_password))

    with driver.session(database=args.neo_db) as s:
        s.run("CREATE CONSTRAINT region_pk IF NOT EXISTS FOR (r:Region) REQUIRE r.id_region IS UNIQUE")
        s.run("CREATE CONSTRAINT dept_pk IF NOT EXISTS FOR (d:Departement) REQUIRE d.code_dept IS UNIQUE")
        s.run("CREATE CONSTRAINT service_pk IF NOT EXISTS FOR (x:Service) REQUIRE x.code_service IS UNIQUE")
        s.run("CREATE CONSTRAINT perimetre_pk IF NOT EXISTS FOR (p:Perimetre) REQUIRE p.id_perimetre IS UNIQUE")
        s.run("CREATE CONSTRAINT infraction_pk IF NOT EXISTS FOR (i:Infraction) REQUIRE i.code_index IS UNIQUE")
        s.run("CREATE CONSTRAINT enr_pk IF NOT EXISTS FOR (e:Enregistrement) REQUIRE e.id_enregistrement IS UNIQUE")
        if args.truncate_neo4j:
            s.run("MATCH (n) DETACH DELETE n")

    def fetch(sql):
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            yield dict(zip(cols, row))

    def write(cypher, rows, batch_size=2000):
        with driver.session(database=args.neo_db) as s:
            for b in chunks(rows, batch_size):
                s.run(cypher, rows=b)

    write(
        "UNWIND $rows AS row MERGE (r:Region {id_region: row.id_region}) SET r.nom_region = row.nom_region",
        fetch("SELECT id_region, nom_region FROM region")
    )

    write(
        "UNWIND $rows AS row "
        "MERGE (d:Departement {code_dept: row.code_dept}) SET d.nom_dept = row.nom_dept "
        "WITH row, d MATCH (r:Region {id_region: row.id_region}) MERGE (d)-[:APPARTIENT_A]->(r)",
        fetch("SELECT code_dept, nom_dept, id_region FROM departement")
    )

    write(
        "UNWIND $rows AS row "
        "MERGE (s:Service {code_service: row.code_service}) SET s.nom_service = row.nom_service "
        "WITH row, s MATCH (d:Departement {code_dept: row.code_dept}) MERGE (s)-[:SE_TROUVE]->(d)",
        fetch("SELECT code_service, nom_service, code_dept FROM service")
    )

    write(
        "UNWIND $rows AS row MERGE (p:Perimetre {id_perimetre: row.id_perimetre}) SET p.nom_perimetre = row.nom_perimetre",
        fetch("SELECT id_perimetre, nom_perimetre FROM perimetre")
    )

    write(
        "UNWIND $rows AS row "
        "MATCH (s:Service {code_service: row.code_service}) "
        "MATCH (p:Perimetre {id_perimetre: row.id_perimetre}) "
        "MERGE (s)-[:APPARTIENT]->(p)",
        fetch("SELECT code_service, id_perimetre FROM service_perimetre")
    )

    write(
        "UNWIND $rows AS row MERGE (i:Infraction {code_index: row.code_index}) SET i.libelle = row.libelle",
        fetch("SELECT code_index, libelle FROM infraction")
    )

    write(
        "UNWIND $rows AS row "
        "MERGE (e:Enregistrement {id_enregistrement: row.id_enregistrement}) "
        "SET e.annee = row.annee, e.nb_faits = toInteger(row.nb_faits) "
        "WITH row, e MATCH (s:Service {code_service: row.code_service}) MERGE (s)-[:ENREGISTRE]->(e) "
        "WITH row, e MATCH (i:Infraction {code_index: row.code_index}) MERGE (e)-[:CONCERNE]->(i)",
        fetch("SELECT id_enregistrement, annee, nb_faits, code_service, code_index FROM enregistrement"),
        batch_size=1200
    )

    write(
        "UNWIND $rows AS row "
        "MATCH (da:Departement {code_dept: row.dept_a}) "
        "MATCH (db:Departement {code_dept: row.dept_b}) "
        "MERGE (da)-[:EST_ADJACENT]->(db)",
        fetch("SELECT dept_a, dept_b FROM adjacence")
    )

    driver.close()
    cur.close()
    pg.close()
    print("OK - Migration PostgreSQL -> Neo4j terminée (pg8000)")

if __name__ == "__main__":
    main()
