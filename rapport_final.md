# Migration d'une Base de Données Relationnelle vers un Modèle Graphe pour l'Analyse des Crimes et Délits (2012-2022)

---

**Commanditaire** : Ministère de l'Intérieur — Direction Générale des Données et de la Sécurité Numérique

**Formation** : SAE NoSQL — Migration de Données

**Date** : Mars 2026

---

## Sommaire

1. Introduction
2. Phase 1 — Analyse des données sources et modélisation relationnelle
3. Phase 2 — Analyse des limites du modèle relationnel
4. Phase 3 — Migration des données
5. Phase 4 — Validation et exploitation
6. Ajout de nouvelles données
7. Défis rencontrés et solutions
8. Conclusion et recommandations
9. Annexes

---

## 1. Introduction

### 1.1 Contexte

Le Ministère de l'Intérieur collecte chaque année les statistiques de criminalité sur l'ensemble du territoire français. Ces données, couvrant la période 2012-2022, proviennent de deux sources : la **Police Nationale (PN)**, qui opère en zone urbaine, et la **Gendarmerie Nationale (GN)**, en zone rurale et périurbaine. Elles représentent plus d'un million d'enregistrements répartis sur 101 départements et 107 types d'infractions.

Ces données sont historiquement stockées dans des fichiers Excel au format matriciel — pratique pour la consultation humaine, mais inadapté à l'analyse programmatique. Le Ministère souhaite les migrer vers des systèmes de bases de données modernes.

### 1.2 Problématique

**En quoi le modèle relationnel atteint-il ses limites pour l'analyse relationnelle des données de criminalité, et comment un modèle graphe peut-il y répondre de manière plus naturelle ?**

Les questions du Ministère portent sur les **relations** entre entités : quels départements voisins connaissent des pics de criminalité similaires ? Quels services couvrent quel territoire ? Ces questions impliquent des traversées de graphe que le modèle relationnel gère difficilement (jointures multiples, requêtes récursives).

### 1.3 Objectifs

1. Structurer les données Excel en une base relationnelle PostgreSQL normalisée.
2. Identifier les limites du relationnel face aux requêtes relationnelles.
3. Concevoir un modèle graphe Neo4j adapté.
4. Migrer l'intégralité des données vers Neo4j.
5. Valider la migration et démontrer la valeur ajoutée du graphe.

---

## 2. Phase 1 — Analyse des données sources et modélisation relationnelle

### 2.1 Étude des données sources

#### Structure du fichier Excel

Le fichier Excel source contient **20 onglets** : un par croisement service (PN/GN) × année (2012 à 2022).

Chaque onglet est au **format matriciel** :

| | Dept 01 - Zone A | Dept 01 - Zone B | Dept 02 - Zone A | ... |
|---|---|---|---|---|
| Infraction 1 | 42 | 18 | 7 | ... |
| Infraction 2 | 105 | 33 | 22 | ... |

- **Lignes** : les 107 types d'infractions
- **Colonnes** : les zones géographiques (commissariats, brigades)
- **Cellules** : le nombre de faits constatés

#### Difficultés rencontrées

1. **3 lignes d'en-tête** par onglet (département, nom de zone, code service) au lieu d'une seule.
2. **Codes département alphanumériques** : la Corse utilise `2A` et `2B`, ce qui interdit le stockage en entier.
3. **Doublons potentiels** entre onglets à gérer lors du chargement.

### 2.2 Processus ETL

Le script `etl.py` transforme le fichier Excel matriciel en CSV exploitable :

```
Fichier Excel (20 onglets, format pivot)
        │
        ▼
Script ETL Python (Pandas)
   1. Lecture des 3 lignes d'en-tête
   2. Unpivot (melt) du format matriciel
   3. Nettoyage et enrichissement
        │
        ▼
CSV vertical (1 ligne = 1 observation)
```

**L'opération centrale est le `melt`** (unpivot). Elle transforme le format large en format long :

*Avant (format matriciel) :*

| code_index | libelle | Zone_A | Zone_B |
|---|---|---|---|
| 01 | Vol simple | 42 | 18 |

*Après (format vertical) :*

| code_index | libelle | zone | faits |
|---|---|---|---|
| 01 | Vol simple | Zone_A | 42 |
| 01 | Vol simple | Zone_B | 18 |

Chaque cellule du tableau original devient une ligne distincte. On passe d'un format « 1 ligne = 1 infraction pour N zones » à « 1 ligne = 1 observation ».

**Pourquoi Pandas ?** La bibliothèque offre la lecture native des fichiers Excel multi-onglets et la méthode `melt()` est conçue précisément pour cette opération d'unpivot.

### 2.3 Modèle Conceptuel (MCD)

Le MCD adopte un **schéma en étoile** centré sur la table de faits `enregistrement`.

| Entité | Rôle |
|---|---|
| **Region** | Découpage administratif de niveau 1 (18 régions) |
| **Departement** | Découpage de niveau 2 (101 départements) |
| **Service** | Unité opérationnelle — commissariat ou brigade (1 239) |
| **Perimetre** | Type de service : PN ou GN (2) |
| **Infraction** | Type de crime/délit selon la nomenclature officielle (107) |
| **Enregistrement** | Fait statistique : nombre de faits constatés (1 120 775) |

**Cardinalités principales** :
- 1 Région → 1,N Départements
- 1 Département → 1,N Services
- 1 Service → 1,1 Département
- Service ↔ Périmètre : relation N-N (via table d'association)
- 1 Enregistrement → 1 Service + 1 Infraction

Le schéma MCD complet est dans le fichier `MCD/MCD_VF.png`.

### 2.4 Modèle logique et physique

Voici le schéma SQL avec les justifications des choix importants :

```sql
CREATE TABLE region (
  id_region    VARCHAR(50) PRIMARY KEY,
  nom_region   VARCHAR(100) NOT NULL
);

CREATE TABLE departement (
  code_dept    VARCHAR(50) PRIMARY KEY,    -- VARCHAR car codes 2A/2B (Corse)
  nom_dept     VARCHAR(100) NOT NULL,
  id_region    VARCHAR(50) NOT NULL REFERENCES region(id_region)
);

CREATE TABLE service (
  code_service VARCHAR(50) PRIMARY KEY,
  nom_service  VARCHAR(100) NOT NULL,
  code_dept    VARCHAR(50) NOT NULL REFERENCES departement(code_dept)
);

CREATE TABLE perimetre (
  id_perimetre  VARCHAR(50) PRIMARY KEY,
  nom_perimetre VARCHAR(100) NOT NULL
);

-- Table d'association N-N (pas d'attribut propre)
CREATE TABLE service_perimetre (
  code_service  VARCHAR(50) NOT NULL REFERENCES service(code_service),
  id_perimetre  VARCHAR(50) NOT NULL REFERENCES perimetre(id_perimetre),
  PRIMARY KEY (code_service, id_perimetre)
);

CREATE TABLE infraction (
  code_index VARCHAR(50) PRIMARY KEY,
  libelle    VARCHAR(200) NOT NULL
);

CREATE TABLE enregistrement (
  id_enregistrement VARCHAR(120) PRIMARY KEY,
  annee            VARCHAR(10) NOT NULL,
  nb_faits         INTEGER NOT NULL CHECK (nb_faits >= 0),  -- pas de valeur négative
  code_service     VARCHAR(50) NOT NULL REFERENCES service(code_service),
  code_index       VARCHAR(50) NOT NULL REFERENCES infraction(code_index),
  CONSTRAINT uq_enr UNIQUE (annee, code_service, code_index)  -- empêche les doublons
);
```

**Choix notables** :
- `VARCHAR` partout pour les codes : imposé par les codes corses `2A`/`2B`.
- `CHECK (nb_faits >= 0)` : un nombre de faits ne peut pas être négatif.
- `UNIQUE (annee, code_service, code_index)` : garantit un seul enregistrement par triplet.
- `REFERENCES` (clés étrangères) : garantissent l'intégrité — impossible de créer un département sans sa région.

### 2.5 Alimentation de la base

Le script `load_csvs_to_postgres_pg8000.py` charge 7 fichiers CSV dans PostgreSQL, dans l'ordre imposé par les clés étrangères :

1. `region` → 2. `departement` → 3. `service` → 4. `perimetre` → 5. `service_perimetre` → 6. `infraction` → 7. `enregistrement`

**Deux techniques importantes** :

- **Batching par lots de 5 000** : au lieu d'insérer 1,1 million de lignes une par une (très lent), on les regroupe par paquets de 5 000. Cela réduit les allers-retours réseau et accélère considérablement le chargement.

- **`ON CONFLICT DO NOTHING`** : si on relance le script, les lignes déjà présentes sont ignorées au lieu de provoquer des erreurs. Cela rend le chargement **idempotent** (on peut le relancer sans risque).

| Table | Fichier CSV | Lignes |
|---|---|---|
| region | region.csv | 18 |
| departement | departement.csv | 101 |
| service | service.csv | 1 239 |
| perimetre | perimetre.csv | 2 |
| service_perimetre | appartient.csv | 1 239 |
| infraction | infraction.csv | 107 |
| enregistrement | enregistrement.csv | 1 120 775 |

---

## 3. Phase 2 — Analyse des limites du modèle relationnel

### 3.1 Limites identifiées

#### Jointures multiples pour les traversées

Pour répondre à « Quels sont les crimes les plus fréquents en Île-de-France ? », il faut traverser Region → Département → Service → Enregistrement → Infraction, soit **4 jointures** :

```sql
SELECT i.libelle, SUM(e.nb_faits) AS total
FROM region r
JOIN departement d ON d.id_region = r.id_region
JOIN service s ON s.code_dept = d.code_dept
JOIN enregistrement e ON e.code_service = s.code_service
JOIN infraction i ON i.code_index = e.code_index
WHERE r.nom_region = 'Ile-de-France'
GROUP BY i.libelle
ORDER BY total DESC LIMIT 10;
```

En Cypher (Neo4j), la même question se lit naturellement :

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WHERE r.nom_region = 'Ile-de-France'
RETURN i.libelle AS infraction, SUM(e.nb_faits) AS total
ORDER BY total DESC LIMIT 10
```

On « dessine » le chemin qu'on veut parcourir — plus besoin de spécifier les conditions de jointure.

#### Requêtes récursives pour les chemins

La question « Quel est le plus court chemin entre Paris et Marseille via les adjacences ? » nécessite en SQL une **CTE récursive** d'une vingtaine de lignes, complexe et lente. En Cypher, c'est natif :

```cypher
MATCH path = shortestPath(
  (a:Departement {code_dept: '75'})-[:EST_ADJACENT*]-(b:Departement {code_dept: '13'})
)
RETURN path
```

#### Résumé des limites

| Opération | SQL | Cypher |
|---|---|---|
| Traversée hiérarchique | N jointures | Pattern chaîné |
| Plus court chemin | CTE récursive (~20 lignes) | `shortestPath` (3 lignes) |
| Voisins des voisins | Self-JOIN multiples | `*2` dans le pattern |

### 3.2 Pourquoi le modèle graphe est plus adapté

Les données de criminalité sont **naturellement un réseau** : des services dans des départements, des départements dans des régions, des départements voisins les uns des autres. Les questions métier sont des questions de **relations** (quels voisins ? quels chemins ? quelle couverture ?).

Dans Neo4j, les relations sont des **entités à part entière** (avec un type, des propriétés, une direction), pas un simple mécanisme technique comme une clé étrangère. Le modèle de données et les questions métier utilisent le même vocabulaire.

De plus, Neo4j utilise l'**index-free adjacency** : chaque nœud stocke un pointeur direct vers ses voisins. La traversée d'une relation est en temps constant, quelle que soit la taille du graphe. En SQL, chaque jointure implique un accès par index dont le coût dépend du volume de données.

### 3.3 Proposition du modèle graphe

#### Les 5 règles de transformation

| Règle | Relationnel | Graphe |
|---|---|---|
| 1 | Table d'entité | Nœud avec propriétés |
| 2 | Clé étrangère | Relation (la colonne FK disparaît du nœud) |
| 3 | Table d'association pure (N-N) | Relation directe (la table disparaît) |
| 4 | Table d'association avec attributs | Nœud intermédiaire + 2 relations |
| 5 | Auto-référence | Relation entre nœuds du même label |

#### Exemples concrets de transformation

**Règle 2 — La FK devient une relation :**

PostgreSQL `departement` :

| code_dept | nom_dept | id_region |
|---|---|---|
| 75 | Paris | REG-11 |

Neo4j :
```
(:Departement {code_dept: "75", nom_dept: "Paris"})
  -[:APPARTIENT_A]->
(:Region {id_region: "REG-11"})
```

La colonne `id_region` **disparaît** du nœud Departement. Elle est remplacée par la relation `APPARTIENT_A`.

**Règle 3 — La table d'association disparaît :**

PostgreSQL `service_perimetre` :

| code_service | id_perimetre |
|---|---|
| SVC-00001 | PN |

Neo4j :
```
(:Service {code_service: "SVC-00001"}) -[:APPARTIENT]-> (:Perimetre {id_perimetre: "PN"})
```

La table `service_perimetre` **n'existe plus**. Chaque ligne devient une relation directe.

#### Ce qui se passe pour chaque table

| Table PostgreSQL | Ce qu'elle devient dans Neo4j |
|---|---|
| `region` | Nœud `:Region` |
| `departement` | Nœud `:Departement` + relation `APPARTIENT_A` → Region. Colonne `id_region` supprimée. |
| `service` | Nœud `:Service` + relation `SE_TROUVE` → Departement. Colonne `code_dept` supprimée. |
| `perimetre` | Nœud `:Perimetre` |
| `service_perimetre` | **Table supprimée.** Devient relation `APPARTIENT` (Service → Perimetre). |
| `infraction` | Nœud `:Infraction` |
| `enregistrement` | Nœud `:Enregistrement` + relations `ENREGISTRE` et `CONCERNE`. Colonnes FK supprimées. |
| `adjacence` | Relation `EST_ADJACENT` entre deux `:Departement` |

#### Schéma du graphe final

```
(Service)-[:SE_TROUVE]->(Departement)-[:APPARTIENT_A]->(Region)
(Service)-[:APPARTIENT]->(Perimetre)
(Service)-[:ENREGISTRE]->(Enregistrement)-[:CONCERNE]->(Infraction)
(Departement)-[:EST_ADJACENT]->(Departement)
```

**6 labels de nœuds**, **6 types de relations**.

---

## 4. Phase 3 — Migration des données

### 4.1 Les différentes méthodes de migration

Avant de choisir notre approche, nous avons étudié les méthodes existantes.

#### 1. ETL applicatif (Python + driver Bolt) — Notre choix

Un script Python lit PostgreSQL et écrit dans Neo4j via le driver officiel Bolt.

- **Avantages** : contrôle total, transformations complexes, gestion d'erreurs fine, code versionnable.
- **Inconvénients** : développement nécessaire.

#### 2. LOAD CSV natif Neo4j

Commande Cypher qui lit directement des fichiers CSV.

```cypher
LOAD CSV WITH HEADERS FROM 'file:///region.csv' AS row
MERGE (r:Region {id_region: row.id_region})
```

- **Avantages** : simple, natif, aucun code externe.
- **Inconvénients** : pas de transformation possible, CSV à pré-formater et placer dans le bon répertoire.

#### 3. neo4j-admin import

Outil en ligne de commande pour l'import massif (bulk).

- **Avantages** : très rapide (écrit directement dans les fichiers de stockage).
- **Inconvénients** : la base doit être **vide**, format CSV strict avec en-têtes spécifiques.

#### 4. APOC (Awesome Procedures On Cypher)

Bibliothèque de procédures étendues, incluant `apoc.load.jdbc` pour lire directement depuis un SGBDR.

- **Avantages** : connexion directe PostgreSQL → Neo4j, pas de fichier intermédiaire.
- **Inconvénients** : plugin à installer, configuration JDBC, moins de contrôle.

#### 5. Neo4j ETL Tool

Outil graphique de mapping visuel tables → nœuds.

- **Avantages** : interface visuelle intuitive.
- **Inconvénients** : limité, peu flexible, moins fiable sur de gros volumes.

#### Tableau comparatif

| Méthode | Contrôle | Performance | Complexité | Reproductibilité |
|---|---|---|---|---|
| **ETL applicatif (Python)** | Total | Bonne | Moyenne | Excellente |
| LOAD CSV | Faible | Bonne | Faible | Moyenne |
| neo4j-admin import | Aucun | Excellente | Moyenne | Bonne |
| APOC (JDBC) | Moyen | Bonne | Moyenne | Bonne |
| Neo4j ETL Tool | Faible | Moyenne | Faible | Faible |

#### Pourquoi l'ETL applicatif Python ?

1. Nous avons besoin de **transformations** : les FK deviennent des relations, la table d'association disparaît, les types sont convertis.
2. Avec 1,1 million de lignes, il faut une **gestion d'erreurs robuste** par lot.
3. Le script est **reproductible** et s'intègre dans Docker.

### 4.2 Architecture technique

L'infrastructure repose sur **Docker Compose** avec 3 conteneurs :

```
┌─────────────────────────────────────────────┐
│              Docker Compose                  │
│                                              │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐ │
│  │ PostgreSQL │  │  Neo4j   │  │ Migration│ │
│  │    17      │  │    5     │  │ Python   │ │
│  │ Port 5433  │  │Port 7474 │  │  3.11    │ │
│  │            │  │Port 7687 │  │          │ │
│  └────────────┘  └──────────┘  └──────────┘ │
│       ▲               ▲           │    │     │
│       └───────────────┴───────────┘    │     │
│          depends_on (healthy)          │     │
└─────────────────────────────────────────────┘
```

**Pourquoi Docker ?**
- **Reproductibilité** : `docker compose up` recrée l'environnement identique sur n'importe quelle machine.
- **Isolation** : chaque service a ses dépendances propres, pas de conflits de versions.
- **Orchestration** : `depends_on` avec healthcheck garantit que la migration ne démarre que quand les deux bases sont prêtes.

Le conteneur de migration utilise un **profil** (`migrate`) : il ne démarre pas automatiquement, on le lance quand on est prêt.

### 4.3 Le script de migration en détail

Le script `migrate_pg_to_neo4j_pg8000.py` procède en étapes séquentielles.

#### Création des contraintes d'unicité

```python
s.run("CREATE CONSTRAINT region_pk IF NOT EXISTS FOR (r:Region) REQUIRE r.id_region IS UNIQUE")
s.run("CREATE CONSTRAINT dept_pk IF NOT EXISTS FOR (d:Departement) REQUIRE d.code_dept IS UNIQUE")
# ... idem pour chaque label
```

Ces contraintes sont l'**équivalent des clés primaires** côté graphe. Elles garantissent l'unicité et créent automatiquement un index pour accélérer les `MERGE`.

#### Migration entité par entité

Pour chaque entité, le script fait : **lecture SQL** → **écriture Cypher**.

**Exemple — Migration des départements :**

```python
# Lecture depuis PostgreSQL
fetch("SELECT code_dept, nom_dept, id_region FROM departement")

# Écriture dans Neo4j
"UNWIND $rows AS row "
"MERGE (d:Departement {code_dept: row.code_dept}) SET d.nom_dept = row.nom_dept "
"WITH row, d MATCH (r:Region {id_region: row.id_region}) MERGE (d)-[:APPARTIENT_A]->(r)"
```

On lit `id_region` depuis PostgreSQL, mais on ne la stocke **pas** comme propriété du nœud. Elle sert uniquement à créer la relation `APPARTIENT_A`. C'est la règle 2 en action.

**Exemple — Migration de la table d'association :**

```python
fetch("SELECT code_service, id_perimetre FROM service_perimetre")

"UNWIND $rows AS row "
"MATCH (s:Service {code_service: row.code_service}) "
"MATCH (p:Perimetre {id_perimetre: row.id_perimetre}) "
"MERGE (s)-[:APPARTIENT]->(p)"
```

Pas de nœud créé : chaque ligne devient directement une relation.

#### UNWIND + MERGE : comment ça marche

- **UNWIND** : prend une liste de lignes et les traite une par une dans une seule requête Cypher. Au lieu de 2 000 requêtes individuelles (2 000 allers-retours réseau), on envoie 1 seule requête contenant 2 000 lignes.
- **MERGE** : « crée si ça n'existe pas, sinon ne fait rien ». Cela rend la migration **idempotente** — on peut la relancer sans créer de doublons.

Les enregistrements (1,1 million de lignes) sont traités par lots de **1 200** (plus petit que les autres entités car chaque ligne crée 1 nœud + 2 relations).

### 4.4 Enrichissement des données

Au-delà de la migration, nous avons enrichi le graphe avec **239 relations d'adjacence** entre départements (quels départements partagent une frontière), issues de données publiques.

```python
"UNWIND $rows AS row "
"MATCH (da:Departement {code_dept: row.dept_a}) "
"MATCH (db:Departement {code_dept: row.dept_b}) "
"MERGE (da)-[:EST_ADJACENT]->(db)"
```

Cet enrichissement montre un avantage du modèle graphe : **ajouter un nouveau type de relation ne modifie pas le schéma existant**. On crée simplement de nouvelles connexions entre des nœuds déjà présents.

---

## 5. Phase 4 — Validation et exploitation

### 5.1 Vérification de cohérence

La validation repose sur des **comptages exhaustifs** : chaque nœud et relation dans Neo4j doit correspondre exactement à une ligne dans PostgreSQL.

| Entité / Relation | PostgreSQL | Neo4j | Écart |
|---|---|---|---|
| Régions | 18 | 18 | 0 |
| Départements | 101 | 101 | 0 |
| Services | 1 239 | 1 239 | 0 |
| Périmètres | 2 | 2 | 0 |
| Infractions | 107 | 107 | 0 |
| Enregistrements | 1 120 775 | 1 120 775 | 0 |
| APPARTIENT_A | 101 | 101 | 0 |
| SE_TROUVE | 1 239 | 1 239 | 0 |
| APPARTIENT | 1 239 | 1 239 | 0 |
| ENREGISTRE | 1 120 775 | 1 120 775 | 0 |
| CONCERNE | 1 120 775 | 1 120 775 | 0 |
| EST_ADJACENT | 239 | 239 | 0 |

**100% de cohérence.** Aucune donnée perdue ni dupliquée.

### 5.2 Requêtes métier

#### Requête 1 — Comptage des nœuds et relations

**Contexte** : Vérifier l'intégrité après migration.

```cypher
MATCH (n)
RETURN labels(n)[0] AS label, COUNT(n) AS nombre
ORDER BY nombre DESC
```

```cypher
MATCH ()-[r]->()
RETURN type(r) AS relation, COUNT(r) AS nombre
ORDER BY nombre DESC
```

#### Requête 2 — Visualisation du modèle complet

**Contexte** : Voir tous les types de nœuds et relations sur un sous-graphe.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region),
      (s)-[:APPARTIENT]->(p:Perimetre),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
RETURN s, d, r, p, e, i
LIMIT 5
```

#### Requête 3 — Top 10 des infractions les plus fréquentes

**Contexte** : Orienter les politiques de prévention nationales.

```cypher
MATCH (e:Enregistrement)-[:CONCERNE]->(i:Infraction)
RETURN i.libelle AS infraction, SUM(e.nb_faits) AS total_faits
ORDER BY total_faits DESC
LIMIT 10
```

#### Requête 4 — Top 3 des crimes par département

**Contexte** : Adapter les moyens locaux aux infractions dominantes.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WITH d.nom_dept AS departement, i.libelle AS infraction, SUM(e.nb_faits) AS total
ORDER BY departement, total DESC
WITH departement, COLLECT({infraction: infraction, total: total})[0..3] AS top3
UNWIND top3 AS t
RETURN departement, t.infraction AS infraction, t.total AS total_faits
```

#### Requête 5 — Hiérarchie Régions / Départements

**Contexte** : Visualiser le découpage administratif.

```cypher
MATCH (d:Departement)-[:APPARTIENT_A]->(r:Region)
RETURN d, r
```

#### Requête 6 — Services d'une région (Île-de-France)

**Contexte** : Analyser le maillage territorial d'une région.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region)
WHERE r.nom_region = 'Ile-de-France'
RETURN s, d, r
LIMIT 50
```

#### Requête 7 — Répartition Police / Gendarmerie

**Contexte** : Voir les services d'un département et leur périmètre.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:APPARTIENT]->(p:Perimetre)
WHERE d.nom_dept = 'Paris'
RETURN s, d, p
```

#### Requête 8 — Adjacences d'un département

**Contexte** : Identifier les départements voisins (avantage clé du graphe).

```cypher
MATCH (d:Departement {code_dept: '75'})-[:EST_ADJACENT]-(voisin:Departement)
RETURN d, voisin
```

#### Requête 9 — Carte complète des adjacences

**Contexte** : Visualiser tout le réseau de voisinage — uniquement possible en graphe.

```cypher
MATCH (a:Departement)-[:EST_ADJACENT]->(b:Departement)
RETURN a, b
```

#### Requête 10 — Plus court chemin entre deux départements

**Contexte** : Trouver le chemin géographique le plus court via les adjacences.

```cypher
MATCH (a:Departement {code_dept: '75'}),
      (b:Departement {code_dept: '13'}),
      path = shortestPath((a)-[:EST_ADJACENT*]-(b))
RETURN path
```

#### Requête 11 — Détail des enregistrements d'un service

**Contexte** : Quelles infractions un service a-t-il enregistrées ?

```cypher
MATCH (s:Service)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WHERE s.code_service = 'SVC-00001'
RETURN s, e, i
LIMIT 20
```

### 5.3 Comparaison SQL vs Cypher

#### Exemple 1 — Crimes par région

**SQL** (4 jointures) :
```sql
SELECT i.libelle, SUM(e.nb_faits) AS total
FROM region r
JOIN departement d ON d.id_region = r.id_region
JOIN service s ON s.code_dept = d.code_dept
JOIN enregistrement e ON e.code_service = s.code_service
JOIN infraction i ON i.code_index = e.code_index
WHERE r.nom_region = 'Ile-de-France'
GROUP BY i.libelle ORDER BY total DESC LIMIT 10;
```

**Cypher** (pattern direct) :
```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WHERE r.nom_region = 'Ile-de-France'
RETURN i.libelle, SUM(e.nb_faits) AS total
ORDER BY total DESC LIMIT 10
```

#### Exemple 2 — Plus court chemin

**SQL** (~20 lignes de CTE récursive) :
```sql
WITH RECURSIVE chemin AS (
  SELECT dept_a, dept_b, 1 AS profondeur, ARRAY[dept_a, dept_b] AS parcours
  FROM adjacence WHERE dept_a = '75'
  UNION ALL
  SELECT c.dept_a, a.dept_b, c.profondeur + 1, c.parcours || a.dept_b
  FROM chemin c JOIN adjacence a ON a.dept_a = c.dept_b
  WHERE a.dept_b != ALL(c.parcours) AND c.profondeur < 20
)
SELECT parcours FROM chemin WHERE dept_b = '13'
ORDER BY profondeur LIMIT 1;
```

**Cypher** (3 lignes) :
```cypher
MATCH path = shortestPath(
  (a:Departement {code_dept: '75'})-[:EST_ADJACENT*]-(b:Departement {code_dept: '13'})
)
RETURN path
```

#### Exemple 3 — Répartition PN/GN par département

**SQL** (3 jointures, table d'association explicite) :
```sql
SELECT p.nom_perimetre, COUNT(s.code_service) AS nb_services
FROM departement d
JOIN service s ON s.code_dept = d.code_dept
JOIN service_perimetre sp ON sp.code_service = s.code_service
JOIN perimetre p ON p.id_perimetre = sp.id_perimetre
WHERE d.nom_dept = 'Paris'
GROUP BY p.nom_perimetre;
```

**Cypher** (relation directe, pas de table intermédiaire) :
```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:APPARTIENT]->(p:Perimetre)
WHERE d.nom_dept = 'Paris'
RETURN p.nom_perimetre, COUNT(s) AS nb_services
```

#### Synthèse

| Critère | SQL | Cypher |
|---|---|---|
| Lisibilité | Technique (jointures) | Naturelle (patterns) |
| Traversées profondes | Coûteux (N jointures) | Efficace (suivi de pointeurs) |
| Plus courts chemins | CTE récursive complexe | `shortestPath` natif |
| Tables d'association | Jointure obligatoire | Relation directe |

---

## 6. Ajout de nouvelles données

### 6.1 Côté relationnel (PostgreSQL)

#### Ajouter une nouvelle année

```sql
INSERT INTO enregistrement (id_enregistrement, annee, nb_faits, code_service, code_index)
VALUES ('2023-SVC-00001-01', '2023', 42, 'SVC-00001', '01');
```

Les contraintes vérifient automatiquement que le service et l'infraction existent (FK) et qu'il n'y a pas de doublon (UNIQUE).

Pour un chargement massif, on relance le script avec `ON CONFLICT DO NOTHING`.

#### Ajouter un nouveau type d'infraction

```sql
-- 1. D'abord l'infraction
INSERT INTO infraction (code_index, libelle) VALUES ('108', 'Cyberharcèlement');

-- 2. Puis les enregistrements
INSERT INTO enregistrement (id_enregistrement, annee, nb_faits, code_service, code_index)
VALUES ('2023-SVC-00001-108', '2023', 15, 'SVC-00001', '108');
```

L'ordre est important : il faut créer l'infraction **avant** de l'utiliser dans un enregistrement (contrainte FK).

### 6.2 Côté graphe (Neo4j)

#### Ajouter une nouvelle année

```cypher
MATCH (s:Service {code_service: 'SVC-00001'})
MATCH (i:Infraction {code_index: '01'})
MERGE (e:Enregistrement {id_enregistrement: '2023-SVC-00001-01'})
SET e.annee = '2023', e.nb_faits = 42
MERGE (s)-[:ENREGISTRE]->(e)
MERGE (e)-[:CONCERNE]->(i)
```

`MERGE` garantit que si l'enregistrement existe déjà, il est mis à jour au lieu d'être dupliqué.

#### Ajouter un nouveau type d'infraction

```cypher
MERGE (i:Infraction {code_index: '108'})
SET i.libelle = 'Cyberharcèlement'
WITH i
MATCH (s:Service {code_service: 'SVC-00001'})
MERGE (e:Enregistrement {id_enregistrement: '2023-SVC-00001-108'})
SET e.annee = '2023', e.nb_faits = 15
MERGE (s)-[:ENREGISTRE]->(e)
MERGE (e)-[:CONCERNE]->(i)
```

### 6.3 Comparaison

| Critère | PostgreSQL | Neo4j |
|---|---|---|
| Ordre d'insertion | Contraint par les FK | Flexible (MERGE dans n'importe quel ordre) |
| Idempotence | `ON CONFLICT DO NOTHING` | `MERGE` natif |
| Modification du schéma | Nécessaire si nouveau type d'entité | Pas nécessaire (graphe flexible) |
| Ajout de relations | Table d'association à créer | Simple relation entre nœuds existants |
| Validation | CHECK, FK, UNIQUE automatiques | Contraintes d'unicité + logique applicative |

**En résumé** : le graphe est plus flexible (pas de schéma rigide à modifier), mais offre moins de garde-fous automatiques que le relationnel.

---

## 7. Défis rencontrés et solutions

| Défi | Problème | Solution |
|---|---|---|
| **Format Excel matriciel** | Format pivot inadapté au traitement | Méthode `pd.melt()` de Pandas |
| **3 lignes d'en-tête** | Pandas ne gère pas nativement | Lecture séparée avec `nrows=3` + mapping |
| **Codes 2A/2B (Corse)** | Casting en entier impossible | `VARCHAR` systématique pour les codes |
| **1,1 million de lignes** | Insertion unitaire trop lente | Batching (5 000 en PG, 1 200 en Neo4j) |
| **Coordination Docker** | Migration avant que les bases soient prêtes | Healthcheck + `depends_on: condition: service_healthy` |

---

## 8. Conclusion et recommandations

### Bilan

Ce projet a réalisé avec succès la migration complète des données de criminalité :

- **1 120 775 enregistrements** migrés avec 100% de cohérence.
- **6 types de nœuds** et **6 types de relations** dans le modèle graphe.
- **239 relations d'adjacence** enrichissant le graphe.
- **11 requêtes métier** démontrant la valeur ajoutée.
- Une **infrastructure Docker** reproductible.

### Recommandations pour le Ministère

1. **Architecture hybride** : garder PostgreSQL pour le stockage de référence et Neo4j pour l'analytique relationnelle.
2. **Enrichir le graphe** : ajouter des relations entre types d'infractions, des flux de criminalité, des données démographiques.
3. **Former les analystes** à Cypher : le langage est accessible et intuitif pour les questions relationnelles.
4. **Industrialiser le pipeline** : ajouter du logging, des métriques et une orchestration (Airflow) pour les mises à jour planifiées.

### Perspectives

- Analyses temporelles (tendances par année et par type d'infraction).
- Graph Data Science (détection de communautés, centralité).
- Intégration avec d'autres sources de données (démographie, économie).
- Dashboards interactifs avec Neo4j Bloom ou Grafana.

---

## 9. Annexes

### Annexe A — Script SQL DDL complet

```sql
DROP TABLE IF EXISTS service_perimetre;
DROP TABLE IF EXISTS enregistrement;
DROP TABLE IF EXISTS perimetre;
DROP TABLE IF EXISTS service;
DROP TABLE IF EXISTS departement;
DROP TABLE IF EXISTS region;
DROP TABLE IF EXISTS infraction;

CREATE TABLE region (
  id_region    VARCHAR(50) PRIMARY KEY,
  nom_region   VARCHAR(100) NOT NULL
);

CREATE TABLE departement (
  code_dept    VARCHAR(50) PRIMARY KEY,
  nom_dept     VARCHAR(100) NOT NULL,
  id_region    VARCHAR(50) NOT NULL REFERENCES region(id_region)
);

CREATE TABLE service (
  code_service VARCHAR(50) PRIMARY KEY,
  nom_service  VARCHAR(100) NOT NULL,
  code_dept    VARCHAR(50) NOT NULL REFERENCES departement(code_dept)
);

CREATE TABLE perimetre (
  id_perimetre  VARCHAR(50) PRIMARY KEY,
  nom_perimetre VARCHAR(100) NOT NULL
);

CREATE TABLE service_perimetre (
  code_service  VARCHAR(50) NOT NULL REFERENCES service(code_service),
  id_perimetre  VARCHAR(50) NOT NULL REFERENCES perimetre(id_perimetre),
  PRIMARY KEY (code_service, id_perimetre)
);

CREATE TABLE infraction (
  code_index VARCHAR(50) PRIMARY KEY,
  libelle    VARCHAR(200) NOT NULL
);

CREATE TABLE enregistrement (
  id_enregistrement VARCHAR(120) PRIMARY KEY,
  annee            VARCHAR(10) NOT NULL,
  nb_faits         INTEGER NOT NULL CHECK (nb_faits >= 0),
  code_service     VARCHAR(50) NOT NULL REFERENCES service(code_service),
  code_index       VARCHAR(50) NOT NULL REFERENCES infraction(code_index),
  CONSTRAINT uq_enr UNIQUE (annee, code_service, code_index)
);
```

### Annexe B — Script de migration (extrait principal)

```python
# Régions
write(
    "UNWIND $rows AS row MERGE (r:Region {id_region: row.id_region}) "
    "SET r.nom_region = row.nom_region",
    fetch("SELECT id_region, nom_region FROM region")
)

# Départements + relation APPARTIENT_A
write(
    "UNWIND $rows AS row "
    "MERGE (d:Departement {code_dept: row.code_dept}) SET d.nom_dept = row.nom_dept "
    "WITH row, d MATCH (r:Region {id_region: row.id_region}) "
    "MERGE (d)-[:APPARTIENT_A]->(r)",
    fetch("SELECT code_dept, nom_dept, id_region FROM departement")
)

# Services + relation SE_TROUVE
write(
    "UNWIND $rows AS row "
    "MERGE (s:Service {code_service: row.code_service}) SET s.nom_service = row.nom_service "
    "WITH row, s MATCH (d:Departement {code_dept: row.code_dept}) "
    "MERGE (s)-[:SE_TROUVE]->(d)",
    fetch("SELECT code_service, nom_service, code_dept FROM service")
)

# Service-Périmètre (table d'association → relation directe)
write(
    "UNWIND $rows AS row "
    "MATCH (s:Service {code_service: row.code_service}) "
    "MATCH (p:Perimetre {id_perimetre: row.id_perimetre}) "
    "MERGE (s)-[:APPARTIENT]->(p)",
    fetch("SELECT code_service, id_perimetre FROM service_perimetre")
)

# Enregistrements + relations ENREGISTRE et CONCERNE
write(
    "UNWIND $rows AS row "
    "MERGE (e:Enregistrement {id_enregistrement: row.id_enregistrement}) "
    "SET e.annee = row.annee, e.nb_faits = toInteger(row.nb_faits) "
    "WITH row, e MATCH (s:Service {code_service: row.code_service}) "
    "MERGE (s)-[:ENREGISTRE]->(e) "
    "WITH row, e MATCH (i:Infraction {code_index: row.code_index}) "
    "MERGE (e)-[:CONCERNE]->(i)",
    fetch("SELECT id_enregistrement, annee, nb_faits, code_service, code_index "
          "FROM enregistrement"),
    batch_size=1200
)

# Adjacences
write(
    "UNWIND $rows AS row "
    "MATCH (da:Departement {code_dept: row.dept_a}) "
    "MATCH (db:Departement {code_dept: row.dept_b}) "
    "MERGE (da)-[:EST_ADJACENT]->(db)",
    fetch("SELECT dept_a, dept_b FROM adjacence")
)
```

### Annexe C — Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:17
    container_name: postgres-crimes
    env_file: .env
    environment:
      POSTGRES_USER: ${PG_USER}
      POSTGRES_PASSWORD: ${PG_PASSWORD}
      POSTGRES_DB: ${PG_DB}
    ports:
      - "5433:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./dump.sql:/dumps/dump.sql:ro
      - ./init-db.sh:/docker-entrypoint-initdb.d/01-init-db.sh:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${PG_USER} -d ${PG_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10

  neo4j:
    image: neo4j:5
    container_name: neo4j-crimes
    env_file: .env
    environment:
      NEO4J_AUTH: ${NEO_USER}/${NEO_PASSWORD}
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s

  migration:
    profiles: [migrate]
    build:
      context: .
      dockerfile: Dockerfile
    container_name: migration-crimes
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_healthy

volumes:
  pg_data:
  neo4j_data:
```
