# SAE NoSQL — Migration PostgreSQL vers Neo4j

Migration d'une base relationnelle vers un modèle graphe pour l'analyse des crimes et délits enregistrés en France (2012-2022).

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré

## Lancer le projet

```bash
cd nosql_migration/nosql_migration
docker compose up -d
```

Les deux bases sont **pré-chargées** via des dumps. Au premier lancement (~1 min), PostgreSQL et Neo4j importent automatiquement les données.

## Accès aux bases

| Service         | URL / Accès                    | Utilisateur   | Mot de passe |
|-----------------|--------------------------------|---------------|--------------|
| Neo4j Browser   | http://localhost:7474          | `neo4j`       | `admin1234`  |
| PostgreSQL      | `localhost:5433`, base `Crimes`| `crimes_user` | `admin`      |

## Arrêter

```bash
cd nosql_migration/nosql_migration

# Arrêter (données conservées)
docker compose down

# Arrêter et tout supprimer (repart de zéro)
docker compose down -v
```

## Relancer la migration manuellement

Si besoin de re-migrer depuis PostgreSQL vers Neo4j :

```bash
cd nosql_migration/nosql_migration
docker compose --profile migrate up --build migration
```

## Structure du projet

```
.
├── nosql_migration/nosql_migration/    # Docker : PostgreSQL + Neo4j
│   ├── docker-compose.yml              # Orchestration des conteneurs
│   ├── .env.example                    # Variables de connexion
│   ├── dump.sql                        # Dump PostgreSQL (chargé au démarrage)
│   ├── neo4j.dump                      # Dump Neo4j (chargé au démarrage)
│   ├── sql_ddl_postgres.sql            # Schéma DDL PostgreSQL
│   ├── migrate_pg_to_neo4j_pg8000.py   # Script de migration PG → Neo4j
│   ├── load_csvs_to_postgres_pg8000.py # Chargement CSV → PostgreSQL
│   ├── requetes_metier.ipynb           # 11 requêtes Cypher commentées
│   └── csv/                            # Données CSV par table
│
├── projet/                             # Phase 1 — ETL et prototypage
│   ├── etl.py                          # Excel → CSV (unpivot Pandas)
│   └── *.xlsx                          # Fichier Excel source
│
├── eclatement/                         # CSV éclatés par table
├── MCD/                                # Modèle Conceptuel de Données
├── rapport_final.md                    # Rapport du projet
└── rapport_final.pdf                   # Rapport en PDF
```

## Modèle du graphe Neo4j

```
(Service)-[:SE_TROUVE]->(Departement)-[:APPARTIENT_A]->(Region)
(Service)-[:APPARTIENT]->(Perimetre)
(Service)-[:ENREGISTRE]->(Enregistrement)-[:CONCERNE]->(Infraction)
(Departement)-[:EST_ADJACENT]->(Departement)
```

6 types de nœuds, 6 types de relations, 1 120 775 enregistrements.

## Requêtes métier

11 requêtes Cypher disponibles dans `requetes_metier.ipynb`, à exécuter dans Neo4j Browser (http://localhost:7474) :

1. Comptage des nœuds et relations
2. Visualisation du modèle complet
3. Top 10 des infractions les plus fréquentes
4. Top 3 des crimes par département
5. Hiérarchie régions / départements
6. Services d'une région (Île-de-France)
7. Répartition Police / Gendarmerie
8. Adjacences d'un département
9. Carte complète des adjacences
10. Plus court chemin entre deux départements
11. Détail des enregistrements d'un service
