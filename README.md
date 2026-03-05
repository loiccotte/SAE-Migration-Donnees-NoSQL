# SAE Migration de Donnees - Crimes et Delits (2012-2022)

Migration d'une base relationnelle (PostgreSQL) vers une base orientee graphe (Neo4j) pour l'analyse des crimes et delits enregistres par la Police et la Gendarmerie nationale.

**Les deux bases sont pre-chargees** : un simple `docker compose up` suffit, pas besoin de lancer la migration manuellement.

---

## Demarrage rapide

### Prerequis

- **Docker Desktop** installe et demarre (c'est tout)

### Lancer le projet

```bash
cd nosql_migration/nosql_migration
cp .env.example .env        # ou utiliser le .env fourni
docker compose up -d
```

Au premier lancement (~1 min) :
- PostgreSQL charge automatiquement le dump SQL
- Neo4j charge automatiquement le dump de graphe (88 Mo, ~15s)

Une fois demarre :

| Service    | URL / Acces                     | Utilisateur   | Mot de passe |
|------------|---------------------------------|---------------|--------------|
| Neo4j Browser | http://localhost:7474        | `neo4j`       | `admin1234`  |
| PostgreSQL | `localhost:5433`, base `Crimes` | `crimes_user` | `admin`      |

### Arreter

```bash
# Arreter (donnees conservees)
docker compose down

# Arreter et tout supprimer (repart de zero au prochain up)
docker compose down -v
```

---

## Structure du projet

```
.
├── nosql_migration/nosql_migration/   # Coeur du projet (Docker)
│   ├── docker-compose.yml             # Orchestration PostgreSQL + Neo4j
│   ├── .env.example                   # Variables de connexion (a copier en .env)
│   ├── dump.sql                       # Dump PostgreSQL (charge auto au demarrage)
│   ├── neo4j.dump                     # Dump Neo4j (charge auto au demarrage)
│   ├── init-db.sh                     # Script init PostgreSQL
│   ├── init-neo4j.sh                  # Script init Neo4j
│   ├── sql_ddl_postgres.sql           # Schema DDL PostgreSQL
│   ├── migrate_pg_to_neo4j_pg8000.py  # Script de migration PG -> Neo4j
│   ├── load_csvs_to_postgres_pg8000.py# Chargement CSV -> PostgreSQL
│   ├── run_ddl_postgres_pg8000.py     # Creation des tables PostgreSQL
│   ├── Dockerfile                     # Image du conteneur de migration
│   ├── requirements.txt               # Dependances Python
│   ├── requetes_metier.ipynb          # 11 requetes Cypher a tester
│   └── csv/                           # Donnees CSV par table
│
├── projet/                            # Phase 1 - ETL et prototypage
│   ├── etl.py                         # Excel -> CSV (unpivot avec Pandas)
│   ├── create_sql_db.py               # Prototype SQLite
│   └── generate_cypher.py             # Prototype Cypher
│
├── eclatement/                        # CSV eclates par table
├── MCD/                               # Modele Conceptuel de Donnees
│   └── MCD_VF.png                     # Schema MCD final
│
├── rapport_final.md                   # Rapport complet du projet
├── rapport_final.pdf                  # Rapport en PDF
└── Consignes.txt                      # Cahier des charges
```

---

## Modele du graphe Neo4j

```
(Service)-[:SE_TROUVE]->(Departement)-[:APPARTIENT_A]->(Region)
(Service)-[:APPARTIENT]->(Perimetre)
(Service)-[:ENREGISTRE]->(Enregistrement)-[:CONCERNE]->(Infraction)
(Departement)-[:EST_ADJACENT]->(Departement)
```

| Noeud | Nombre | Description |
|-------|--------|-------------|
| Region | 18 | Regions de France |
| Departement | 101 | Avec adjacences geographiques (239 relations) |
| Service | 1 239 | Commissariats / brigades |
| Perimetre | 2 | Police nationale (PN) / Gendarmerie nationale (GN) |
| Infraction | 107 | Types de crimes et delits |
| Enregistrement | 1 120 775 | Faits constates par annee |

---

## Requetes metier

Le fichier `requetes_metier.ipynb` contient 11 requetes Cypher a executer dans Neo4j Browser :

1. Comptage des noeuds et relations
2. Visualisation du modele complet
3. Top 10 des infractions les plus frequentes
4. Top 3 des crimes par departement
5. Hierarchie regions / departements
6. Services d'une region (Ile-de-France)
7. Repartition Police / Gendarmerie
8. Adjacences d'un departement
9. Carte complete des adjacences
10. Plus court chemin entre deux departements (`shortestPath`)
11. Detail des enregistrements d'un service

---

## Scripts

| Script | Role |
|--------|------|
| `etl.py` | Lit le fichier Excel brut, depivote (melt), nettoie, produit un CSV |
| `load_csvs_to_postgres_pg8000.py` | Charge les 7 CSV dans PostgreSQL (batch 5000, ON CONFLICT) |
| `migrate_pg_to_neo4j_pg8000.py` | Lit PostgreSQL, cree noeuds/relations Neo4j (UNWIND + MERGE) |
| `run_ddl_postgres_pg8000.py` | Execute le DDL SQL dans PostgreSQL |

---

## Relancer la migration manuellement

Si besoin de re-migrer depuis PostgreSQL vers Neo4j (par ex. apres modification des donnees) :

```bash
cd nosql_migration/nosql_migration
docker compose --profile migrate up --build migration
```

---

## Execution locale (sans Docker)

Si PostgreSQL et Neo4j sont deja installes localement :

```bash
cd nosql_migration/nosql_migration
pip install -r requirements.txt
python run_ddl_postgres_pg8000.py --pg-host localhost --pg-port 5433 --pg-db Crimes --pg-user crimes_user --pg-password admin
python load_csvs_to_postgres_pg8000.py --pg-host localhost --pg-port 5433 --pg-db Crimes --pg-user crimes_user --pg-password admin
python migrate_pg_to_neo4j_pg8000.py --pg-host localhost --pg-port 5433 --pg-db Crimes --pg-user crimes_user --pg-password admin --truncate-neo4j
```
