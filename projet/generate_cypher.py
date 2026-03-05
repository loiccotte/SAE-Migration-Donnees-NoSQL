import pandas as pd
import os

def generate_cypher_script():
    input_csv = "base_crimes_clean_v3.csv"
    output_cypher = "import_graph.cypher"

    if not os.path.exists(input_csv):
        print("❌ Fichier CSV introuvable. Veuillez lancer etl.py d'abord.")
        return

    print("⏳ Lecture des données...")
    df = pd.read_csv(input_csv)

    print("écriture du script Cypher...")
    with open(output_cypher, "w", encoding="utf-8") as f:
        
        # 1. Optimisation (Index) - Syntaxe compatible anciennes versions
        f.write("// --- INDEX ---\n")
        f.write("CREATE INDEX ON :Departement(code);\n")
        f.write("CREATE INDEX ON :Zone(nom_complet);\n")
        f.write("CREATE INDEX ON :Crime(code);\n\n")

        # 2. Création des Départements (Uniques)
        # On extrait les codes départements uniques
        depts = df['code_departement'].astype(str).unique()
        f.write("// --- NOEUDS DEPARTEMENTS ---\n")
        for dept in depts:
            # CREATE (:Departement {code: "01"})
            line = f'CREATE (:Departement {{code: "{dept}"}});\n'
            f.write(line)
        f.write("\n")

        # 3. Création des Crimes (Uniques)
        # On extrait les codes et libellés uniques
        crimes = df[['code_index', 'libelle_index']].drop_duplicates()
        f.write("// --- NOEUDS CRIMES ---\n")
        for _, row in crimes.iterrows():
            code = row['code_index']
            libelle = str(row['libelle_index']).replace('"', "'") # Échapper les guillemets
            line = f'CREATE (:Crime {{code: {code}, libelle: "{libelle}"}});\n'
            f.write(line)
        f.write("\n")

        # 4. Création des Zones et Relations
        # Attention : Pour ne pas exploser le fichier, on va grouper.
        # Mais pour faire simple et lisible pour le projet :
        
        f.write("// --- ZONES ET RELATIONS ---\n")
        # On itère sur les zones uniques pour les créer
        # Une zone est définie par son nom, son code service et son département
        zones = df[['nom_zone', 'code_service_zone', 'service', 'code_departement']].drop_duplicates()
        
        # Dictionnaire pour retrouver l'ID unique de la zone plus tard si besoin
        # Ici on va utiliser MATCH pour lier
        
        count = 0
        for _, row in zones.iterrows():
            nom = str(row['nom_zone']).replace('"', "'")
            code_service = str(row['code_service_zone']).replace('"', "'")
            service = row['service']
            dept = str(row['code_departement'])
            
            # Identifiant unique technique pour le script Cypher (pour éviter les MATCH lents à l'insertion)
            zone_id = f"z_{count}"
            
            # Création du nœud Zone
            f.write(f'CREATE ({zone_id}:Zone {{nom: "{nom}", code_service: "{code_service}", type: "{service}"}})\n')
            
            # Relation Zone -> Departement
            # On cherche le département créé plus haut
            f.write(f'WITH {zone_id} MATCH (d:Departement {{code: "{dept}"}}) CREATE ({zone_id})-[:APPARTIENT_A]->(d);\n')
            
            count += 1
            if count % 1000 == 0:
                print(f"   {count} zones traitées...")

        # 5. Les Faits (Statistiques) - Le gros morceau
        # Pour limiter la taille du fichier, on ne va prendre que les faits > 0
        df_faits = df[df['faits'] > 0]
        
        f.write("\n// --- RELATIONS DE FAITS (STATISTIQUES) ---\n")
        # Attention : Cette partie peut être très lourde.
        # Stratégie : MATCH la Zone et le Crime, puis CREATE la relation.
        
        # Pour optimiser, on va écrire des blocs.
        # NOTE : Sur Neo4j 1.5.9, le LOAD CSV n'existait pas vraiment de façon performante.
        # On va générer des requêtes CREATE unitaires. C'est verbeux mais ça marche partout.
        
        limit_rows = 5000 # Limite pour l'exemple (sinon le fichier fera 500Mo)
        print(f"⚠️ Génération limitée aux {limit_rows} premiers faits non-nuls pour la démo.")
        
        current = 0
        for _, row in df_faits.iterrows():
            if current >= limit_rows:
                break
                
            nom_zone = str(row['nom_zone']).replace('"', "'")
            code_service = str(row['code_service_zone']).replace('"', "'")
            code_crime = row['code_index']
            annee = row['annee']
            nb = row['faits']
            
            # Requête Cypher
            query = (
                f'MATCH (z:Zone {{nom: "{nom_zone}", code_service: "{code_service}"}}) '
                f'MATCH (c:Crime {{code: {code_crime}}}) '
                f'CREATE (z)-[:A_ENREGISTRE {{annee: {annee}, faits: {nb}}}]->(c);\n'
            )
            f.write(query)
            current += 1

    print(f"✅ Fichier '{output_cypher}' généré avec succès !")
    print("👉 Vous pouvez ouvrir ce fichier texte et copier le contenu dans la console Neo4j.")

if __name__ == "__main__":
    generate_cypher_script()