# Récap travail du 05/03/2026

---

## Partie théorique : Comment passer du relationnel au graphe ?

### Principe général

En relationnel, tout est stocké dans des **tables** (lignes + colonnes). En graphe, on manipule des **nœuds** (entités) reliés par des **relations** (arcs). La migration consiste à décider, pour chaque table, si elle devient un nœud ou une relation.

### Règle 1 — Une table d'entité devient un nœud

Chaque **ligne** d'une table d'entité (qui a sa propre clé primaire et des attributs descriptifs) devient un **nœud** dans le graphe. Les colonnes deviennent des **propriétés** du nœud.

**Exemple concret avec notre projet :**

Table `region` en SQL :
```
| id_region | nom_region          |
|-----------|---------------------|
| 84        | Auvergne-Rhône-Alpes|
| 75        | Nouvelle-Aquitaine  |
```

Devient en Cypher :
```cypher
(:Region {id_region: "84", nom_region: "Auvergne-Rhône-Alpes"})
(:Region {id_region: "75", nom_region: "Nouvelle-Aquitaine"})
```

Chaque ligne = 1 nœud. Chaque colonne = 1 propriété du nœud.

### Règle 2 — Une clé étrangère (FK) devient une relation

Quand une table contient une **clé étrangère** qui référence une autre table, cette FK se traduit par une **relation** (un arc) entre deux nœuds.

**Exemple concret :**

Table `departement` en SQL :
```
| code_dept | nom_dept | id_region |  ← FK vers region
|-----------|----------|-----------|
| 01        | Ain      | 84        |
| 33        | Gironde  | 75        |
```

Transformation :
1. Chaque ligne → un nœud `(:Departement)`
2. La FK `id_region` → une relation `[:APPARTIENT_A]`

Résultat en Cypher :
```cypher
(:Departement {code_dept: "01", nom_dept: "Ain"})
    -[:APPARTIENT_A]->
(:Region {id_region: "84", nom_region: "Auvergne-Rhône-Alpes"})
```

> La colonne `id_region` **disparaît** des propriétés du nœud Departement : elle est remplacée par la relation. C'est un point fondamental — dans un graphe, les liens sont explicites, pas stockés comme des valeurs dans un champ.

### Règle 3 — Une table d'association (N-N) devient une relation directe

Les tables d'association (ou tables de jointure) n'ont pas de raison d'exister en graphe. Elles deviennent simplement une **relation** entre les deux nœuds concernés.

**Exemple concret :**

Table `appartient` (association Service ↔ Perimetre) en SQL :
```
| code_service | id_perimetre |
|--------------|-------------|
| SRV001       | PN          |
| SRV002       | GN          |
```

Pas de nœud intermédiaire. On crée directement :
```cypher
(:Service {code_service: "SRV001"})-[:APPARTIENT]->(:Perimetre {id_perimetre: "PN"})
(:Service {code_service: "SRV002"})-[:APPARTIENT]->(:Perimetre {id_perimetre: "GN"})
```

> La table entière disparaît en tant que structure — chaque ligne devient un arc.

### Règle 4 — Une table d'association avec attributs peut devenir un nœud intermédiaire

Quand une table d'association porte des **attributs propres** (pas juste les deux FK), on peut la transformer en nœud intermédiaire relié aux deux entités.

**Exemple concret :**

Table `enregistrement` en SQL :
```
| id_enregistrement | annee | nb_faits | code_service | code_index |
|-------------------|-------|----------|-------------|-----------|
| 1                 | 2020  | 150      | SRV001      | 42        |
```

Ici, `enregistrement` porte des données propres (`annee`, `nb_faits`), donc elle devient un **nœud** relié aux deux entités par deux relations :

```cypher
(:Service {code_service: "SRV001"})
    -[:ENREGISTRE]->
(:Enregistrement {id_enregistrement: 1, annee: 2020, nb_faits: 150})
    -[:CONCERNE]->
(:Infraction {code_index: 42})
```

### Règle 5 — Une table d'auto-référence devient une relation entre nœuds du même type

Quand une table décrit des liens entre entités du **même type**, chaque ligne devient une relation entre deux nœuds existants.

**Exemple concret :**

Table `adjacence` en SQL :
```
| dept_a | dept_b |
|--------|--------|
| 01     | 38     |
| 01     | 69     |
```

Résultat :
```cypher
(:Departement {code_dept: "01"})-[:EST_ADJACENT]->(:Departement {code_dept: "38"})
(:Departement {code_dept: "01"})-[:EST_ADJACENT]->(:Departement {code_dept: "69"})
```

### Récapitulatif des règles de transformation

| Élément relationnel | Devient en graphe | Exemple du projet |
|---------------------|-------------------|-------------------|
| Table d'entité (avec PK + attributs) | **Nœud** avec propriétés | `region` → `(:Region)` |
| Colonne classique | **Propriété** du nœud | `nom_region` → `{nom_region: "..."}` |
| Clé étrangère (FK) | **Relation** entre nœuds | `departement.id_region` → `[:APPARTIENT_A]` |
| Table d'association pure (N-N) | **Relation** directe | `appartient` → `[:APPARTIENT]` |
| Table d'association avec attributs | **Nœud intermédiaire** + 2 relations | `enregistrement` → `(:Enregistrement)` + `[:ENREGISTRE]` + `[:CONCERNE]` |
| Table d'auto-référence | **Relation** entre nœuds du même label | `adjacence` → `[:EST_ADJACENT]` |

---

## Phase 4 : Validation et Exploitation

### 1. Vérification de la cohérence des données migrées

#### Comptages PostgreSQL vs Neo4j — Nœuds

| Entité | PostgreSQL | Neo4j | Cohérent |
|--------|-----------|-------|----------|
| Régions | 18 | 18 | OUI |
| Départements | 101 | 101 | OUI |
| Services | 1 239 | 1 239 | OUI |
| Périmètres | 2 | 2 | OUI |
| Infractions | 107 | 107 | OUI |
| Enregistrements | 1 120 775 | 1 120 775 | OUI |

#### Comptages Neo4j — Relations

| Relation | Attendu (source PG) | Neo4j | Cohérent |
|----------|-------------------|-------|----------|
| APPARTIENT_A (Dept → Region) | 101 (= nb départements) | 101 | OUI |
| SE_TROUVE (Service → Dept) | 1 239 (= nb services) | 1 239 | OUI |
| APPARTIENT (Service → Perimetre) | 1 239 (table appartient) | 1 239 | OUI |
| ENREGISTRE (Service → Enregistrement) | 1 120 775 (= nb enregistrements) | 1 120 775 | OUI |
| CONCERNE (Enregistrement → Infraction) | 1 120 775 (= nb enregistrements) | 1 120 775 | OUI |
| EST_ADJACENT (Dept ↔ Dept) | 239 (table adjacence) | 239 | OUI |

**Conclusion : La migration est 100% cohérente.** Tous les nœuds et relations (y compris les adjacences entre départements) correspondent exactement aux données source PostgreSQL.

#### Modifications apportées
- Ajout de la relation `EST_ADJACENT` dans Neo4j (239 liens entre départements voisins)
- Script `migrate_pg_to_neo4j_pg8000.py` mis à jour pour inclure la migration des adjacences
- Graphe Neo4j final :
```
(Service)-[:SE_TROUVE]->(Departement)-[:APPARTIENT_A]->(Region)
(Service)-[:APPARTIENT]->(Perimetre)
(Service)-[:ENREGISTRE]->(Enregistrement)-[:CONCERNE]->(Infraction)
(Departement)-[:EST_ADJACENT]->(Departement)
```
