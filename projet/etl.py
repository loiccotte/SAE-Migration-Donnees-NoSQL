import pandas as pd
import os
import re
import glob

def process_excel_final_v3():
    # 1. Recherche du fichier Excel (.xlsx)
    excel_files = glob.glob("*.xlsx")
    
    if not excel_files:
        print("❌ ERREUR : Aucun fichier Excel (.xlsx) trouvé dans le dossier.")
        return

    target_file = excel_files[0]
    print(f"📗 Fichier Excel trouvé : {target_file}")
    print("⏳ Chargement... (Cela inclut maintenant la 3ème ligne de détail)")

    try:
        xls = pd.ExcelFile(target_file)
    except Exception as e:
        print(f"❌ Impossible d'ouvrir le fichier : {e}")
        return

    all_data = []

    for sheet_name in xls.sheet_names:
        # Analyse nom onglet (PN/GN + Année)
        match_service = re.search(r'(PN|GN)', sheet_name, re.IGNORECASE)
        match_annee = re.search(r'(20\d{2})', sheet_name)

        if not (match_service and match_annee):
            continue 

        service = match_service.group(1).upper()
        annee = int(match_annee.group(1))
        
        print(f"   👉 Traitement : {service} - {annee}")

        try:
            # --- ÉTAPE A : Lecture des 3 Lignes d'En-tête ---
            # Ligne 0 = Départements
            # Ligne 1 = Nom de la Zone (Circonscription/Brigade)
            # Ligne 2 = Code / Détail supplémentaire (La ligne manquante)
            header_df = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=3)
            
            raw_depts = header_df.iloc[0].tolist()
            raw_zones = header_df.iloc[1].tolist()
            raw_details = header_df.iloc[2].tolist() # La fameuse 3ème ligne

            col_mapping = {}
            # On commence à l'index 2 (après les colonnes Code index et Libellé)
            for idx in range(2, len(raw_zones)):
                d = str(raw_depts[idx]).strip() if pd.notna(raw_depts[idx]) else None
                z = str(raw_zones[idx]).strip() if pd.notna(raw_zones[idx]) else None
                # On capture aussi la 3ème info
                detail = str(raw_details[idx]).strip() if pd.notna(raw_details[idx]) else ""
                
                if d:
                    col_mapping[idx] = (d, z, detail)

            # --- ÉTAPE B : Lecture des Données (à partir de la ligne 4) ---
            # On saute les 3 lignes d'entêtes
            data_df = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=3)

            # --- ÉTAPE C : Unpivot ---
            df_melted = data_df.melt(id_vars=[0, 1], var_name='col_idx', value_name='faits')

            # --- ÉTAPE D : Nettoyage ---
            df_melted = df_melted.rename(columns={0: 'code_index', 1: 'libelle_index'})

            # Suppression des lignes parasites (ex: répétition des entêtes)
            df_melted = df_melted[df_melted['code_index'].astype(str) != 'Code index']

            # Enrichissement
            df_melted['annee'] = annee
            df_melted['service'] = service
            
            # Application du mapping (Dept, Zone, Detail)
            meta_info = df_melted['col_idx'].map(col_mapping)
            
            df_melted['code_departement'] = meta_info.apply(lambda x: x[0] if isinstance(x, tuple) else None)
            df_melted['nom_zone'] = meta_info.apply(lambda x: x[1] if isinstance(x, tuple) else None)
            # Nouvelle colonne pour la 3ème ligne
            df_melted['code_service_zone'] = meta_info.apply(lambda x: x[2] if isinstance(x, tuple) else None)

            # Conversion numérique
            df_melted['faits'] = pd.to_numeric(df_melted['faits'], errors='coerce').fillna(0).astype(int)
            
            # Nettoyage final
            df_melted = df_melted.dropna(subset=['code_departement'])

            # --- ÉTAPE E : Ordre des colonnes ---
            cols = [
                'annee', 
                'service', 
                'code_departement', 
                'nom_zone', 
                'code_service_zone', # La nouvelle colonne insérée ici
                'code_index', 
                'faits', 
                'libelle_index'
            ]
            df_melted = df_melted[cols]

            all_data.append(df_melted)

        except Exception as e:
            print(f"      ❌ Erreur sur {sheet_name} : {e}")

    # 3. Export
    if all_data:
        print("\n💾 Sauvegarde du fichier complet...")
        final_df = pd.concat(all_data, ignore_index=True)
        
        output_name = "base_crimes_clean_v3.csv"
        final_df.to_csv(output_name, index=False, encoding='utf-8')
        
        print(f"🎉 TERMINÉ ! Fichier créé : {output_name}")
        print(f"✅ Colonne ajoutée : 'code_service_zone' (données de la ligne 3)")
    else:
        print("⚠️ Aucune donnée extraite.")

if __name__ == "__main__":
    process_excel_final_v3()