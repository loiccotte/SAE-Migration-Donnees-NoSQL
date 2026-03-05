# Migration PostgreSQL → Neo4j — Crimes en France

Migre des données statistiques de criminalité d'une base relationnelle PostgreSQL vers un graphe Neo4j.

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré — **c'est tout**.

---

## Démarrage en une commande

```bash
docker compose up --build
```

Docker va automatiquement :
1. Démarrer PostgreSQL et Neo4j
2. Attendre que les deux bases soient prêtes
3. Créer le schéma PostgreSQL (`run_ddl_postgres_pg8000.py`)
4. Charger les CSV dans PostgreSQL (`load_csvs_to_postgres_pg8000.py`)
5. Migrer les données vers Neo4j (`migrate_pg_to_neo4j_pg8000.py`)

---

## Identifiants

Tous les identifiants sont centralisés dans [`.env`](.env).

### PostgreSQL

| Paramètre  | Valeur        |
|------------|---------------|
| Hôte       | `localhost`   |
| Port       | `5433`        |
| Base       | `Crimes`      |
| Utilisateur| `crimes_user` |
| Mot de passe | `admin`     |

### Neo4j

| Paramètre  | Valeur              |
|------------|---------------------|
| Browser    | http://localhost:7474 |
| Bolt URI   | `bolt://localhost:7687` |
| Utilisateur| `neo4j`             |
| Mot de passe | `admin1234`       |

---

## Arrêt

```bash
# Arrêter les conteneurs (données conservées dans les volumes Docker)
docker compose down

# Arrêter ET supprimer toutes les données (repart de zéro au prochain up)
docker compose down -v
```

---

## Exécution locale (sans Docker)

Si PostgreSQL et Neo4j sont déjà installés localement :

```powershell
pip install -r requirements.txt

.\run_all.ps1 `
  -CsvDir ".\csv" `
  -PgHost "localhost" -PgPort 5433 -PgDb "Crimes" -PgUser "crimes_user" -PgPassword "admin" `
  -NeoUri "bolt://127.0.0.1:7687" -NeoUser "Crimes" -NeoPassword "admin1234" `
  -TruncateNeo4j
```

Ou en passant par les variables d'environnement (charger `.env` au préalable) :

```bash
export $(grep -v '^#' .env | xargs)
python run_ddl_postgres_pg8000.py
python load_csvs_to_postgres_pg8000.py
python migrate_pg_to_neo4j_pg8000.py --truncate-neo4j
```

---

## Structure des données

| Entité            | Nb enregistrements |
|-------------------|--------------------|
| Régions           | 18                 |
| Départements      | 101                |
| Services          | 1 239              |
| Périmètres        | 2                  |
| Infractions       | 107                |
| Enregistrements   | ~1 120 775         |

Graphe Neo4j obtenu :
```
(Service)-[:SE_TROUVE]->(Departement)-[:APPARTIENT_A]->(Region)
(Service)-[:APPARTIENT]->(Perimetre)
(Service)-[:ENREGISTRE]->(Enregistrement)-[:CONCERNE]->(Infraction)
```
