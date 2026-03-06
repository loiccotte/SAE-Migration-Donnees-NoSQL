# Migration d'une base relationnelle vers un modele graphe — Crimes et delits (2012-2022)

---

**Commanditaire** : Ministere de l'Interieur — Direction Generale des Donnees et de la Securite Numerique

**Formation** : BUT Science des Donnees — SAE NoSQL

**Date** : Mars 2026

---

## Sommaire

1. Introduction
2. Phase 1 — Analyse des donnees et modelisation relationnelle
3. Phase 2 — Limites du relationnel et passage au graphe
4. Phase 3 — Migration des donnees
5. Phase 4 — Validation et exploitation
6. Ajout de nouvelles donnees
7. Difficultes rencontrees
8. Conclusion
9. Annexes

---

## 1. Introduction

### 1.1 Contexte

Chaque annee, le Ministere de l'Interieur collecte les statistiques de criminalite sur tout le territoire francais. Les donnees couvrent la periode 2012-2022 et proviennent de deux sources : la Police Nationale (PN) en zone urbaine, et la Gendarmerie Nationale (GN) en zone rurale et periurbaine. Au total, on parle de plus d'un million d'enregistrements repartis sur 101 departements et 107 types d'infractions.

A l'origine, tout est stocke dans un gros fichier Excel avec un format matriciel. Ca se lit bien a l'oeil, mais c'est penible a exploiter par programme.

### 1.2 Problematique

Le Ministere veut pouvoir repondre a des questions du type : quels departements voisins ont des pics de criminalite similaires ? Quels services couvrent quel territoire ? Ce genre de questions tourne autour des relations entre les entites. En SQL classique, ca implique beaucoup de jointures imbriquees et des requetes recursives des qu'on veut suivre un chemin dans les donnees. D'ou l'idee de tester un modele graphe.

### 1.3 Objectifs

1. Structurer les donnees Excel en base relationnelle PostgreSQL.
2. Montrer ou le relationnel coince face a certaines requetes.
3. Concevoir un modele graphe Neo4j adapte.
4. Migrer toutes les donnees vers Neo4j.
5. Verifier que rien n'a ete perdu et montrer ce que le graphe apporte.

---

## 2. Phase 1 — Analyse des donnees et modelisation relationnelle

### 2.1 Le fichier Excel source

Le fichier contient 20 onglets : un par croisement service (PN/GN) x annee (2012 a 2022).

Chaque onglet est au format matriciel :

| | Dept 01 - Zone A | Dept 01 - Zone B | Dept 02 - Zone A | ... |
|---|---|---|---|---|
| Infraction 1 | 42 | 18 | 7 | ... |
| Infraction 2 | 105 | 33 | 22 | ... |

Les lignes correspondent aux 107 types d'infractions, les colonnes aux zones geographiques (commissariats, brigades), et les cellules au nombre de faits constates.

On a rencontre plusieurs problemes avec ce fichier :

1. Il y a 3 lignes d'en-tete par onglet (departement, nom de zone, code service) au lieu d'une seule. Pandas ne gere pas ca tout seul.
2. Les codes departement sont alphanumeriques : la Corse utilise `2A` et `2B`, donc on ne peut pas stocker ca en entier.
3. Il faut gerer les doublons potentiels entre onglets.

### 2.2 Processus ETL

Le script `etl.py` transforme le fichier Excel en CSV exploitable :

```
Fichier Excel (20 onglets, format pivot)
        |
        v
Script ETL Python (Pandas)
   1. Lecture des 3 lignes d'en-tete
   2. Unpivot (melt) du format matriciel
   3. Nettoyage et enrichissement
        |
        v
CSV vertical (1 ligne = 1 observation)
```

L'operation qui fait tout le travail, c'est le `melt` (unpivot). On passe d'un format large a un format long :

Avant (format matriciel) :

| code_index | libelle | Zone_A | Zone_B |
|---|---|---|---|
| 01 | Vol simple | 42 | 18 |

Apres (format vertical) :

| code_index | libelle | zone | faits |
|---|---|---|---|
| 01 | Vol simple | Zone_A | 42 |
| 01 | Vol simple | Zone_B | 18 |

Chaque cellule du tableau original devient une ligne. On passe de "1 ligne = 1 infraction pour N zones" a "1 ligne = 1 observation". Pandas est pratique ici : il lit les fichiers Excel multi-onglets nativement et la methode `melt()` fait exactement cette operation d'unpivot.

### 2.3 Modele Conceptuel (MCD)

On a opte pour un schema en etoile centre sur la table de faits `enregistrement`.

| Entite | Role |
|---|---|
| Region | Decoupage administratif de niveau 1 (18 regions) |
| Departement | Decoupage de niveau 2 (101 departements) |
| Service | Unite operationnelle, commissariat ou brigade (1 239) |
| Perimetre | Type de service : PN ou GN (2) |
| Infraction | Type de crime/delit selon la nomenclature officielle (107) |
| Enregistrement | Fait statistique : nombre de faits constates (1 120 775) |

Cardinalites principales :

- 1 Region contient 1 a N Departements
- 1 Departement contient 1 a N Services
- 1 Service appartient a 1 seul Departement
- Service et Perimetre sont lies en N-N (via table d'association)
- 1 Enregistrement correspond a 1 Service + 1 Infraction

Le schema MCD complet est dans `MCD/MCD_VF.png`.

### 2.4 Modele logique et physique

Voici le schema SQL avec les choix qu'on a faits :

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
  nb_faits         INTEGER NOT NULL CHECK (nb_faits >= 0),
  code_service     VARCHAR(50) NOT NULL REFERENCES service(code_service),
  code_index       VARCHAR(50) NOT NULL REFERENCES infraction(code_index),
  CONSTRAINT uq_enr UNIQUE (annee, code_service, code_index)
);
```

Quelques points a noter :

- `VARCHAR` partout pour les codes, a cause des codes corses `2A`/`2B` qu'on ne peut pas stocker en entier.
- `CHECK (nb_faits >= 0)` pour empecher les valeurs negatives.
- `UNIQUE (annee, code_service, code_index)` pour garantir un seul enregistrement par triplet.
- Les `REFERENCES` (cles etrangeres) empechent de creer un departement sans sa region, par exemple.

### 2.5 Alimentation de la base

Le script `load_csvs_to_postgres_pg8000.py` charge 7 fichiers CSV dans PostgreSQL, dans l'ordre impose par les cles etrangeres :

1. `region` puis 2. `departement` puis 3. `service` puis 4. `perimetre` puis 5. `service_perimetre` puis 6. `infraction` puis 7. `enregistrement`

Deux techniques qu'on a utilisees :

- Batching par lots de 5 000 : au lieu d'inserer 1,1 million de lignes une par une (tres lent a cause des allers-retours reseau), on les regroupe par paquets de 5 000.

- `ON CONFLICT DO NOTHING` : si on relance le script, les lignes deja presentes sont ignorees au lieu de provoquer des erreurs. Ca rend le chargement idempotent, on peut le relancer autant de fois qu'on veut sans risque.

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

## 3. Phase 2 — Limites du relationnel et passage au graphe

### 3.1 Ou le SQL coince

#### Les jointures s'empilent vite

Pour repondre a "Quels sont les crimes les plus frequents en Ile-de-France ?", il faut traverser Region, Departement, Service, Enregistrement et Infraction. Ca fait 4 jointures :

```sql
SELECT i.libelle, SUM(e.nb_faits) AS total
FROM region r
JOIN departement d ON d.id_region = r.id_region
JOIN service s ON s.code_dept = d.code_dept
JOIN enregistrement e ON e.code_service = s.code_service
JOIN infraction i ON i.code_index = e.code_index
WHERE r.nom_region = 'Île-de-France'
GROUP BY i.libelle
ORDER BY total DESC LIMIT 10;
```

En Cypher (Neo4j), la meme question se lit beaucoup plus naturellement :

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WHERE r.nom_region = 'Île-de-France'
RETURN i.libelle AS infraction, SUM(e.nb_faits) AS total
ORDER BY total DESC LIMIT 10
```

On "dessine" le chemin qu'on veut parcourir au lieu de specifier les conditions de jointure une par une.

#### Les requetes recursives pour les chemins

La question "Quel est le plus court chemin entre Paris et Marseille via les adjacences ?" necessite en SQL une CTE recursive d'une vingtaine de lignes. En Cypher, ca tient en 3 lignes :

```cypher
MATCH path = shortestPath(
  (a:Departement {code_dept: '75'})-[:EST_ADJACENT*]-(b:Departement {code_dept: '13'})
)
RETURN path
```

#### Resume

| Operation | SQL | Cypher |
|---|---|---|
| Traversee hierarchique | N jointures | Pattern chaine |
| Plus court chemin | CTE recursive (~20 lignes) | `shortestPath` (3 lignes) |
| Voisins des voisins | Self-JOIN multiples | `*2` dans le pattern |

### 3.2 Pourquoi le graphe colle mieux a ces donnees

Les donnees de criminalite forment un reseau : des services dans des departements, des departements dans des regions, des departements voisins les uns des autres. Les questions metier sont des questions de relations, quels voisins ? quels chemins ? quelle couverture ?

Dans Neo4j, les relations sont des objets a part entiere (avec un type, des proprietes, une direction), pas juste un mecanisme technique comme une cle etrangere. Le modele de donnees et les questions metier parlent le meme langage.

Neo4j utilise aussi ce qu'on appelle l'index-free adjacency : chaque noeud stocke un pointeur direct vers ses voisins. Traverser une relation est en temps constant, quelle que soit la taille du graphe. En SQL, chaque jointure passe par un index dont le cout depend du volume de donnees.

### 3.3 Conception du modele graphe

#### Regles de transformation

On a applique 5 regles pour passer du relationnel au graphe :

| Regle | Relationnel | Graphe |
|---|---|---|
| 1 | Table d'entite | Noeud avec proprietes |
| 2 | Cle etrangere | Relation (la colonne FK disparait du noeud) |
| 3 | Table d'association pure (N-N) | Relation directe (la table disparait) |
| 4 | Table d'association avec attributs | Noeud intermediaire + 2 relations |
| 5 | Auto-reference | Relation entre noeuds du meme label |

#### Exemples concrets

Regle 2 -- La FK devient une relation :

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

La colonne `id_region` disparait du noeud Departement. Elle est remplacee par la relation `APPARTIENT_A`.

Regle 3 -- La table d'association disparait :

PostgreSQL `service_perimetre` :

| code_service | id_perimetre |
|---|---|
| SVC-00001 | PN |

Neo4j :
```
(:Service {code_service: "SVC-00001"}) -[:APPARTIENT]-> (:Perimetre {id_perimetre: "PN"})
```

La table `service_perimetre` n'existe plus. Chaque ligne devient une relation directe.

#### Transformation table par table

| Table PostgreSQL | Ce qu'elle devient dans Neo4j |
|---|---|
| `region` | Noeud `:Region` |
| `departement` | Noeud `:Departement` + relation `APPARTIENT_A` vers Region. Colonne `id_region` supprimee. |
| `service` | Noeud `:Service` + relation `SE_TROUVE` vers Departement. Colonne `code_dept` supprimee. |
| `perimetre` | Noeud `:Perimetre` |
| `service_perimetre` | Table supprimee. Devient relation `APPARTIENT` (Service vers Perimetre). |
| `infraction` | Noeud `:Infraction` |
| `enregistrement` | Noeud `:Enregistrement` + relations `ENREGISTRE` et `CONCERNE`. Colonnes FK supprimees. |
| `adjacence` | Relation `EST_ADJACENT` entre deux `:Departement` |

#### Schema du graphe final

```
(Service)-[:SE_TROUVE]->(Departement)-[:APPARTIENT_A]->(Region)
(Service)-[:APPARTIENT]->(Perimetre)
(Service)-[:ENREGISTRE]->(Enregistrement)-[:CONCERNE]->(Infraction)
(Departement)-[:EST_ADJACENT]->(Departement)
```

6 labels de noeuds, 6 types de relations.

---

## 4. Phase 3 — Migration des donnees

### 4.1 Les differentes methodes de migration

Avant de se lancer, on a regarde ce qui existait comme methodes.

#### 1. ETL applicatif (Python + driver Bolt) -- ce qu'on a choisi

Un script Python lit PostgreSQL et ecrit dans Neo4j via le driver officiel Bolt.

Avantages : controle total sur les transformations, gestion d'erreurs fine, code versionnable. Inconvenient principal : il faut le developper.

#### 2. LOAD CSV natif Neo4j

Commande Cypher qui lit directement des fichiers CSV.

```cypher
LOAD CSV WITH HEADERS FROM 'file:///region.csv' AS row
MERGE (r:Region {id_region: row.id_region})
```

Simple et natif, mais pas de transformation possible. Il faut pre-formater les CSV et les placer dans le bon repertoire.

#### 3. neo4j-admin import

Outil en ligne de commande pour l'import massif. Tres rapide car il ecrit directement dans les fichiers de stockage, mais la base doit etre vide et le format CSV est strict.

#### 4. APOC (Awesome Procedures On Cypher)

Bibliotheque de procedures etendues, incluant `apoc.load.jdbc` pour lire depuis un SGBDR. Connexion directe PostgreSQL vers Neo4j sans fichier intermediaire, mais c'est un plugin a installer avec de la configuration JDBC.

#### 5. Neo4j ETL Tool

Outil graphique de mapping visuel tables vers noeuds. Interface visuelle mais limite, peu flexible, pas fiable sur de gros volumes.

#### Comparatif

| Methode | Controle | Performance | Complexite | Reproductibilite |
|---|---|---|---|---|
| ETL applicatif (Python) | Total | Bonne | Moyenne | Excellente |
| LOAD CSV | Faible | Bonne | Faible | Moyenne |
| neo4j-admin import | Aucun | Excellente | Moyenne | Bonne |
| APOC (JDBC) | Moyen | Bonne | Moyenne | Bonne |
| Neo4j ETL Tool | Faible | Moyenne | Faible | Faible |

#### Pourquoi on a choisi Python

On avait besoin de transformer les donnees pendant la migration : les FK deviennent des relations, la table d'association disparait, les types sont convertis. Avec 1,1 million de lignes, il fallait aussi pouvoir gerer les erreurs lot par lot. Et le script s'integre bien dans Docker, ce qui le rend reproductible.

### 4.2 Architecture technique

L'infrastructure repose sur Docker Compose avec 3 conteneurs :

```
+---------------------------------------------+
|              Docker Compose                  |
|                                              |
|  +------------+  +----------+  +----------+ |
|  | PostgreSQL |  |  Neo4j   |  | Migration| |
|  |    17      |  |    5     |  | Python   | |
|  | Port 5433  |  |Port 7474 |  |  3.11    | |
|  |            |  |Port 7687 |  |          | |
|  +------------+  +----------+  +----------+ |
|       ^               ^           |    |     |
|       +---------------+-----------+    |     |
|          depends_on (healthy)          |     |
+---------------------------------------------+
```

On a choisi Docker pour trois raisons :

- `docker compose up` recree l'environnement identique sur n'importe quelle machine.
- Chaque service a ses dependances propres, pas de conflits de versions.
- `depends_on` avec healthcheck garantit que la migration ne demarre que quand les deux bases sont pretes.

Le conteneur de migration utilise un profil (`migrate`) : il ne demarre pas automatiquement, on le lance quand on est pret.

### 4.3 Le script de migration en detail

Le script `migrate_pg_to_neo4j_pg8000.py` fonctionne en etapes sequentielles.

#### Contraintes d'unicite

```python
s.run("CREATE CONSTRAINT region_pk IF NOT EXISTS FOR (r:Region) REQUIRE r.id_region IS UNIQUE")
s.run("CREATE CONSTRAINT dept_pk IF NOT EXISTS FOR (d:Departement) REQUIRE d.code_dept IS UNIQUE")
# ... idem pour chaque label
```

Ces contraintes sont l'equivalent des cles primaires cote graphe. Elles garantissent l'unicite et creent un index pour accelerer les `MERGE`.

#### Migration entite par entite

Pour chaque entite, le script fait : lecture SQL puis ecriture Cypher.

Exemple avec les departements :

```python
# Lecture depuis PostgreSQL
fetch("SELECT code_dept, nom_dept, id_region FROM departement")

# Ecriture dans Neo4j
"UNWIND $rows AS row "
"MERGE (d:Departement {code_dept: row.code_dept}) SET d.nom_dept = row.nom_dept "
"WITH row, d MATCH (r:Region {id_region: row.id_region}) MERGE (d)-[:APPARTIENT_A]->(r)"
```

On lit `id_region` depuis PostgreSQL, mais on ne la stocke pas comme propriete du noeud. Elle sert uniquement a creer la relation `APPARTIENT_A`. C'est la regle 2 en action.

Exemple avec la table d'association :

```python
fetch("SELECT code_service, id_perimetre FROM service_perimetre")

"UNWIND $rows AS row "
"MATCH (s:Service {code_service: row.code_service}) "
"MATCH (p:Perimetre {id_perimetre: row.id_perimetre}) "
"MERGE (s)-[:APPARTIENT]->(p)"
```

Pas de noeud cree ici : chaque ligne devient directement une relation.

#### UNWIND + MERGE

UNWIND prend une liste de lignes et les traite une par une dans une seule requete Cypher. Au lieu de 2 000 requetes individuelles (2 000 allers-retours reseau), on envoie 1 seule requete contenant 2 000 lignes.

MERGE veut dire "cree si ca n'existe pas, sinon ne fais rien". Ca rend la migration idempotente, on peut la relancer sans creer de doublons.

Les enregistrements (1,1 million de lignes) sont traites par lots de 1 200 (plus petit que les autres entites car chaque ligne cree 1 noeud + 2 relations).

### 4.4 Enrichissement des donnees

En plus de la migration, on a ajoute 239 relations d'adjacence entre departements (quels departements partagent une frontiere). Ces donnees viennent de sources publiques.

```python
"UNWIND $rows AS row "
"MATCH (da:Departement {code_dept: row.dept_a}) "
"MATCH (db:Departement {code_dept: row.dept_b}) "
"MERGE (da)-[:EST_ADJACENT]->(db)"
```

Ca montre un avantage concret du graphe : ajouter un nouveau type de relation ne modifie pas le schema existant. On cree de nouvelles connexions entre des noeuds deja presents, c'est tout.

---

## 5. Phase 4 — Validation et exploitation

### 5.1 Verification de coherence

On a fait des comptages exhaustifs pour verifier que chaque noeud et chaque relation dans Neo4j correspond a une ligne dans PostgreSQL.

| Entite / Relation | PostgreSQL | Neo4j | Ecart |
|---|---|---|---|
| Regions | 18 | 18 | 0 |
| Departements | 101 | 101 | 0 |
| Services | 1 239 | 1 239 | 0 |
| Perimetres | 2 | 2 | 0 |
| Infractions | 107 | 107 | 0 |
| Enregistrements | 1 120 775 | 1 120 775 | 0 |
| APPARTIENT_A | 101 | 101 | 0 |
| SE_TROUVE | 1 239 | 1 239 | 0 |
| APPARTIENT | 1 239 | 1 239 | 0 |
| ENREGISTRE | 1 120 775 | 1 120 775 | 0 |
| CONCERNE | 1 120 775 | 1 120 775 | 0 |
| EST_ADJACENT | 239 | 239 | 0 |

Aucune donnee perdue ni dupliquee, 100% de coherence.

### 5.2 Requetes metier

#### Requete 1 -- Comptage des noeuds et relations

Verifier l'integrite apres migration.

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

#### Requete 2 -- Visualisation du modele complet

Voir tous les types de noeuds et relations sur un sous-graphe.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region),
      (s)-[:APPARTIENT]->(p:Perimetre),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
RETURN s, d, r, p, e, i
LIMIT 5
```

#### Requete 3 -- Top 10 des infractions les plus frequentes

Identifier les infractions les plus courantes pour orienter la prevention.

```cypher
MATCH (e:Enregistrement)-[:CONCERNE]->(i:Infraction)
RETURN i.libelle AS infraction, SUM(e.nb_faits) AS total_faits
ORDER BY total_faits DESC
LIMIT 10
```

#### Requete 4 -- Top 3 des crimes par departement

Adapter les moyens locaux en fonction des infractions dominantes.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WITH d.nom_dept AS departement, i.libelle AS infraction, SUM(e.nb_faits) AS total
ORDER BY departement, total DESC
WITH departement, COLLECT({infraction: infraction, total: total})[0..3] AS top3
UNWIND top3 AS t
RETURN departement, t.infraction AS infraction, t.total AS total_faits
```

#### Requete 5 -- Hierarchie regions / departements

Visualiser le decoupage administratif.

```cypher
MATCH (d:Departement)-[:APPARTIENT_A]->(r:Region)
RETURN d, r
```

#### Requete 6 -- Services d'une region (Ile-de-France)

Analyser le maillage territorial d'une region.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region)
WHERE r.nom_region = 'Île-de-France'
RETURN s, d, r
LIMIT 50
```

#### Requete 7 -- Repartition Police / Gendarmerie

Voir les services d'un departement et leur perimetre.

```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:APPARTIENT]->(p:Perimetre)
WHERE d.nom_dept = 'Paris'
RETURN s, d, p
```

#### Requete 8 -- Adjacences d'un departement

Identifier les departements voisins. C'est la que le graphe prend tout son sens.

```cypher
MATCH (d:Departement {code_dept: '75'})-[:EST_ADJACENT]-(voisin:Departement)
RETURN d, voisin
```

#### Requete 9 -- Carte complete des adjacences

Visualiser tout le reseau de voisinage.

```cypher
MATCH (a:Departement)-[:EST_ADJACENT]->(b:Departement)
RETURN a, b
```

#### Requete 10 -- Plus court chemin entre deux departements

Trouver le chemin geographique le plus court via les adjacences.

```cypher
MATCH (a:Departement {code_dept: '75'}),
      (b:Departement {code_dept: '13'}),
      path = shortestPath((a)-[:EST_ADJACENT*]-(b))
RETURN path
```

#### Requete 11 -- Detail des enregistrements d'un service

Quelles infractions un service a-t-il enregistrees ?

```cypher
MATCH (s:Service)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WHERE s.code_service = '1'
RETURN s, e, i
LIMIT 20
```

### 5.3 Comparaison SQL vs Cypher

#### Exemple 1 -- Crimes par region

SQL (4 jointures) :
```sql
SELECT i.libelle, SUM(e.nb_faits) AS total
FROM region r
JOIN departement d ON d.id_region = r.id_region
JOIN service s ON s.code_dept = d.code_dept
JOIN enregistrement e ON e.code_service = s.code_service
JOIN infraction i ON i.code_index = e.code_index
WHERE r.nom_region = 'Île-de-France'
GROUP BY i.libelle ORDER BY total DESC LIMIT 10;
```

Cypher (pattern direct) :
```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WHERE r.nom_region = 'Île-de-France'
RETURN i.libelle, SUM(e.nb_faits) AS total
ORDER BY total DESC LIMIT 10
```

#### Exemple 2 -- Plus court chemin

SQL (~20 lignes de CTE recursive) :
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

Cypher (3 lignes) :
```cypher
MATCH path = shortestPath(
  (a:Departement {code_dept: '75'})-[:EST_ADJACENT*]-(b:Departement {code_dept: '13'})
)
RETURN path
```

#### Exemple 3 -- Repartition PN/GN par departement

SQL (3 jointures, table d'association explicite) :
```sql
SELECT p.nom_perimetre, COUNT(s.code_service) AS nb_services
FROM departement d
JOIN service s ON s.code_dept = d.code_dept
JOIN service_perimetre sp ON sp.code_service = s.code_service
JOIN perimetre p ON p.id_perimetre = sp.id_perimetre
WHERE d.nom_dept = 'Paris'
GROUP BY p.nom_perimetre;
```

Cypher (relation directe, pas de table intermediaire) :
```cypher
MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:APPARTIENT]->(p:Perimetre)
WHERE d.nom_dept = 'Paris'
RETURN p.nom_perimetre, COUNT(s) AS nb_services
```

#### Synthese

| Critere | SQL | Cypher |
|---|---|---|
| Lisibilite | Technique (jointures) | Naturelle (patterns) |
| Traversees profondes | N jointures | Suivi de pointeurs |
| Plus courts chemins | CTE recursive | `shortestPath` natif |
| Tables d'association | Jointure obligatoire | Relation directe |

---

## 6. Ajout de nouvelles donnees

### 6.1 Cote relationnel (PostgreSQL)

#### Ajouter une nouvelle annee

```sql
INSERT INTO enregistrement (id_enregistrement, annee, nb_faits, code_service, code_index)
VALUES ('2023-SVC-00001-01', '2023', 42, 'SVC-00001', '01');
```

Les contraintes verifient automatiquement que le service et l'infraction existent (FK) et qu'il n'y a pas de doublon (UNIQUE).

Pour un chargement massif, on relance le script avec `ON CONFLICT DO NOTHING`.

#### Ajouter un nouveau type d'infraction

```sql
-- 1. D'abord l'infraction
INSERT INTO infraction (code_index, libelle) VALUES ('108', 'Cyberharcelement');

-- 2. Puis les enregistrements
INSERT INTO enregistrement (id_enregistrement, annee, nb_faits, code_service, code_index)
VALUES ('2023-SVC-00001-108', '2023', 15, 'SVC-00001', '108');
```

L'ordre compte : il faut creer l'infraction avant de l'utiliser dans un enregistrement, sinon la contrainte FK bloque.

### 6.2 Cote graphe (Neo4j)

#### Ajouter une nouvelle annee

```cypher
MATCH (s:Service {code_service: 'SVC-00001'})
MATCH (i:Infraction {code_index: '01'})
MERGE (e:Enregistrement {id_enregistrement: '2023-SVC-00001-01'})
SET e.annee = '2023', e.nb_faits = 42
MERGE (s)-[:ENREGISTRE]->(e)
MERGE (e)-[:CONCERNE]->(i)
```

`MERGE` garantit que si l'enregistrement existe deja, il est mis a jour au lieu d'etre duplique.

#### Ajouter un nouveau type d'infraction

```cypher
MERGE (i:Infraction {code_index: '108'})
SET i.libelle = 'Cyberharcelement'
WITH i
MATCH (s:Service {code_service: 'SVC-00001'})
MERGE (e:Enregistrement {id_enregistrement: '2023-SVC-00001-108'})
SET e.annee = '2023', e.nb_faits = 15
MERGE (s)-[:ENREGISTRE]->(e)
MERGE (e)-[:CONCERNE]->(i)
```

### 6.3 Comparaison

| Critere | PostgreSQL | Neo4j |
|---|---|---|
| Ordre d'insertion | Contraint par les FK | Flexible (MERGE dans n'importe quel ordre) |
| Idempotence | `ON CONFLICT DO NOTHING` | `MERGE` natif |
| Modification du schema | Necessaire si nouveau type d'entite | Pas necessaire (graphe flexible) |
| Ajout de relations | Table d'association a creer | Simple relation entre noeuds existants |
| Validation | CHECK, FK, UNIQUE automatiques | Contraintes d'unicite + logique applicative |

En gros, le graphe est plus souple (pas de schema rigide a modifier), mais offre moins de garde-fous automatiques que le relationnel.

---

## 7. Difficultes rencontrees

| Probleme | Ce qui coincait | Comment on a fait |
|---|---|---|
| Format Excel matriciel | Format pivot inadapte au traitement | Methode `pd.melt()` de Pandas |
| 3 lignes d'en-tete | Pandas ne gere pas ca nativement | Lecture separee avec `nrows=3` + mapping manuel |
| Codes 2A/2B (Corse) | Impossible de stocker en entier | `VARCHAR` systematique pour tous les codes |
| 1,1 million de lignes | Insertion unitaire beaucoup trop lente | Batching (5 000 en PG, 1 200 en Neo4j) |
| Coordination Docker | La migration demarrait avant que les bases soient pretes | Healthcheck + `depends_on: condition: service_healthy` |

---

## 8. Conclusion

On a migre l'integralite des donnees de criminalite depuis PostgreSQL vers Neo4j :

- 1 120 775 enregistrements migres sans perte
- 6 types de noeuds et 6 types de relations
- 239 relations d'adjacence ajoutees en enrichissement
- 11 requetes metier qui montrent ce que le graphe apporte
- Une infrastructure Docker qui permet de tout relancer en une commande

Quelques recommandations si le projet devait etre pousse plus loin :

1. Garder les deux bases : PostgreSQL pour le stockage de reference, Neo4j pour l'analyse relationnelle.
2. Enrichir le graphe avec des donnees supplementaires (demographie, flux de criminalite, relations entre types d'infractions).
3. Former les analystes a Cypher : le langage se prend en main assez vite pour des questions relationnelles.
4. Industrialiser le pipeline avec du logging, des metriques, et une orchestration type Airflow pour les mises a jour planifiees.

On pourrait aussi aller plus loin avec les outils de Graph Data Science de Neo4j (detection de communautes, centralite) ou brancher des dashboards avec Neo4j Bloom ou Grafana.

---

## 9. Annexes

### Annexe A -- Script SQL DDL complet

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

### Annexe B -- Script de migration (extrait principal)

```python
# Regions
write(
    "UNWIND $rows AS row MERGE (r:Region {id_region: row.id_region}) "
    "SET r.nom_region = row.nom_region",
    fetch("SELECT id_region, nom_region FROM region")
)

# Departements + relation APPARTIENT_A
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

# Service-Perimetre (table d'association -> relation directe)
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

### Annexe C -- Docker Compose

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
