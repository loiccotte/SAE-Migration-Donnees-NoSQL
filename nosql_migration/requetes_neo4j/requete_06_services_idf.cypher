MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region)
WHERE r.nom_region = 'Île-de-France'
RETURN s, d, r
LIMIT 50