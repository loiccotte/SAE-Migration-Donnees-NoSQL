import pandas as pd
import sqlite3
import os

def create_database():
    csv_file = "base_crimes_clean_v3.csv"
    db_file = "crimes_db_relational.db"

    if not os.path.exists(csv_file):
        print(f"❌ Le fichier {csv_file} est introuvable.")
        return

    print("⏳ Lecture du CSV...")
    df = pd.read_csv(csv_file)

    # Connexion à la base de données (création automatique si inexistante)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    print(f"🔌 Connexion à la base de données : {db_file}")

    # --- 1. CRÉATION DES TABLES (DDL) ---
    print("🛠️ Création des tables SQL...")
    
    # Table DIM_INFRACTIONS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS DIM_INFRACTIONS (
        code_index INTEGER PRIMARY KEY,
        libelle_index TEXT
    )
    ''')

    # Table DIM_ZONES
    # On utilise un ID auto-incrémenté car un même nom de zone peut exister
    # dans le temps ou changer légèrement, on veut un identifiant unique propre.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS DIM_ZONES (
        id_zone INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_zone TEXT,
        code_service_zone TEXT,
        code_departement TEXT,
        service TEXT
    )
    ''')

    # Table FACT_CRIMES
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS FACT_CRIMES (
        id_fait INTEGER PRIMARY KEY AUTOINCREMENT,
        annee INTEGER,
        id_zone INTEGER,
        code_index INTEGER,
        nombre_faits INTEGER,
        FOREIGN KEY (id_zone) REFERENCES DIM_ZONES(id_zone),
        FOREIGN KEY (code_index) REFERENCES DIM_INFRACTIONS(code_index)
    )
    ''')

    # --- 2. ALIMENTATION DES DIMENSIONS ---
    print("📥 Importation des données...")

    # A. Import INFRACTIONS (Déduplication)
    infractions = df[['code_index', 'libelle_index']].drop_duplicates()
    infractions.to_sql('DIM_INFRACTIONS', conn, if_exists='replace', index=False)
    print(f"   ✅ {len(infractions)} Types d'infractions insérés.")

    # B. Import ZONES (Déduplication)
    # On prend les colonnes uniques qui définissent une zone
    cols_zone = ['nom_zone', 'code_service_zone', 'code_departement', 'service']
    zones = df[cols_zone].drop_duplicates()
    # On laisse SQLite gérer l'ID auto-incrémenté, on n'insère que les données
    zones.to_sql('DIM_ZONES_TEMP', conn, if_exists='replace', index=False)
    
    # On transfère de la table temporaire vers la vraie table pour avoir les IDs propres
    cursor.execute('DELETE FROM DIM_ZONES') # Nettoyage si relance
    cursor.execute('''
        INSERT INTO DIM_ZONES (nom_zone, code_service_zone, code_departement, service)
        SELECT nom_zone, code_service_zone, code_departement, service FROM DIM_ZONES_TEMP
    ''')
    cursor.execute('DROP TABLE DIM_ZONES_TEMP')
    print(f"   ✅ {len(zones)} Zones géographiques insérées.")

    # --- 3. ALIMENTATION DE LA TABLE DE FAITS ---
    # C'est la partie astucieuse : on doit remplacer les noms par les IDs qu'on vient de créer.
    
    # On recharge les zones avec leurs nouveaux IDs depuis la base
    zones_sql = pd.read_sql("SELECT * FROM DIM_ZONES", conn)
    
    # On fait une jointure (merge) entre le CSV global et la table des zones
    # pour récupérer 'id_zone' correspondant à chaque ligne
    df_merged = pd.merge(
        df, 
        zones_sql, 
        on=['nom_zone', 'code_service_zone', 'code_departement', 'service'], 
        how='left'
    )

    # On prépare la table finale
    faits_final = df_merged[['annee', 'id_zone', 'code_index', 'faits']]
    faits_final = faits_final.rename(columns={'faits': 'nombre_faits'})

    # Insertion massive
    faits_final.to_sql('FACT_CRIMES', conn, if_exists='append', index=False)
    print(f"   ✅ {len(faits_final)} Lignes de faits insérées.")

    # --- 4. EXEMPLE DE REQUÊTE DE CONTRÔLE ---
    print("\n🔎 Vérification (Top 3 Départements avec le plus de crimes en 2021) :")
    query = '''
        SELECT z.code_departement, SUM(f.nombre_faits) as total
        FROM FACT_CRIMES f
        JOIN DIM_ZONES z ON f.id_zone = z.id_zone
        WHERE f.annee = 2021
        GROUP BY z.code_departement
        ORDER BY total DESC
        LIMIT 3
    '''
    for row in cursor.execute(query):
        print(f"   Dépt {row[0]} : {row[1]} crimes")

    conn.commit()
    conn.close()
    print(f"\n🎉 Base de données Relationnelle '{db_file}' créée avec succès !")

if __name__ == "__main__":
    create_database()