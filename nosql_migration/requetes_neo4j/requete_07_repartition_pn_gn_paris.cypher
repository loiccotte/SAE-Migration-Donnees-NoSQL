MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:APPARTIENT]->(p:Perimetre)
WHERE d.nom_dept = 'Paris'
RETURN s, d, p