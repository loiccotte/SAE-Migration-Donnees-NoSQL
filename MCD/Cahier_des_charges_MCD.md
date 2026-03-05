# Cahier des Charges  
## Conception du Modèle de Données (MCD)

**Projet :** Migration Base *Crimes & Délits* (2012–2021)  
**Version :** 1.0  
**Date :** 20 janvier 2026  

---

## 1. Contexte et Objectifs

Le projet vise à transformer des fichiers plats hétérogènes (CSV / Excel) en une **structure de données relationnelle rigoureuse**, propre et exploitable.

### Objectifs principaux
- Constituer une **base relationnelle nettoyée et normalisée**
- Fournir une **fondation fiable pour l’analyse spatiale**
- Préparer une **future migration vers une base orientée Graphe**

### Contraintes fondamentales du MCD
- **Normalisation**  
  Éliminer les redondances textuelles (libellés répétés des millions de fois).
- **Unicité**  
  Garantir l’unicité des référentiels (départements, régions, infractions, services).
- **Préparation topologique**  
  Intégrer explicitement la notion de **voisinage géographique**, indispensable pour le futur modèle Graphe.

---

## 2. Analyse de l’Existant (Sources de Données)

### Description des sources
- **20 fichiers CSV**
  - 10 années (2012 → 2021)
  - 2 services (Police Nationale / Gendarmerie Nationale)

### Format actuel
- **Structure :** Tableau croisé (matrice)
  - **Lignes :** Types d’infractions
  - **Colonnes :** Départements (`01`, `02`, …, `974`)
  - **Cellules :** Nombre de faits constatés

### Contrainte technique majeure
Le MCD doit permettre le passage :
- d’une **vue matricielle (Excel)**  
- vers une **vue relationnelle verticale (Base de données)**

---

## 3. Règles de Gestion (Business Rules)

### RG-01 — Granularité temporelle
- L’unité de temps est **l’année civile**
- Historique à gérer : **2012 à 2021**
- Le modèle doit être **extensible aux années futures**

---

### RG-02 — Référentiel géographique & topologie
- Un **Département** est identifié par un **Code INSEE**
  - Format **alphanumérique** requis (`2A`, `2B`)
- Un département appartient à **une seule Région**

#### Règle spécifique Graphe
- Un département peut avoir **plusieurs départements voisins**
- Cette relation d’adjacence est **critique** et doit être modélisée explicitement

---

### RG-03 — Typologie des infractions
- Une infraction est définie par :
  - un **Index numérique unique**
  - un **Libellé descriptif**
- Exemple :
  - `Index = 107`
  - `Libellé = Vols à main armée`

---

### RG-04 — Origine des données (Service)
- Un fait constaté provient :
  - soit de la **Police Nationale (PN)**
  - soit de la **Gendarmerie Nationale (GN)**
- Pour une même année / département / infraction :
  - Les chiffres **PN et GN peuvent coexister**
  - Ils ne doivent **jamais être écrasés**

---

### RG-05 — La mesure statistique (Fait)
Un enregistrement statistique est défini par l’unicité de :

Année + Département + Service + Type d’infraction

- La mesure associée est :
  - un **entier**
  - **positif ou nul**

---

## 4. Dictionnaire des Données

### Entités et attributs minimaux

| Entité | Attribut | Type | Description / Contrainte |
|------|---------|------|---------------------------|
| **Département** | Code_Dept | VARCHAR(3) | Clé primaire (`'01'`, `'974'`, `'2A'`) |
|  | Nom_Dept | VARCHAR | Libellé du département |
| **Région** | ID_Region | INT | Clé primaire |
|  | Nom_Region | VARCHAR | Nom de la région |
| **Infraction** | Code_Index | INT | Clé primaire (ex : `107`) |
|  | Libelle | VARCHAR | Description de l’infraction |
| **Service** | ID_Service | VARCHAR(2) | `'PN'` ou `'GN'` |
| **Temps** | Annee | INT | Année civile (`2012`, `2021`, …) |
| **Statistique** | Nombre_Faits | INT | Mesure quantitative |

---

## 5. Spécifications du Modèle

### 5.1 Type de Modèle

Le modèle retenu est un **Schéma en Étoile (Star Schema)**.

- **Table centrale :**
  - `STATISTIQUES` (table de faits)
- **Tables de dimensions :**
  - `DEPARTEMENT`
  - `REGION`
  - `INFRACTION`
  - `SERVICE`
  - `TEMPS`

---

### 5.2 Cardinalités requises

#### Département / Région
- Un département appartient à **une et une seule région** `(1,1)`
- Une région contient **0 à N départements** `(0,n)`

---

#### Département / Voisinage (relation réflexive)
- Un département peut avoir **0 à N voisins**
- Implémentation via une table d’association :

ADJACENCE
- Dept_A
- Dept_B

---

#### Table de faits / Dimensions
- Chaque ligne de la table `STATISTIQUES` est liée à :
  - **1 Service**
  - **1 Année**
  - **1 Département**
  - **1 Infraction**
- Cardinalité `(1,1)` sur chaque branche de l’étoile

---

## 6. Livrables Attendus

### 6.1 Schéma Graphique du MCD
- Diagramme normalisé :
  - entités
  - attributs
  - clés
  - associations
  - cardinalités

---

### 6.2 Script SQL (DDL – PostgreSQL)
Le script devra inclure :
- `CREATE TABLE`
- **Clés primaires (PK)**
- **Clés étrangères (FK)**
- **Contraintes d’unicité**
- Modélisation explicite de la table `ADJACENCE`

---

### 6.3 Stratégie d’Alimentation des Données
Description synthétique du processus :
1. Lecture des fichiers CSV pivotés
2. Transformation en format **long (vertical)**
3. Alimentation des tables de dimensions
4. Chargement de la table de faits

**Outils recommandés :**
- **Python**
- **Pandas** (`melt`, contrôles d’unicité, gestion des clés)
