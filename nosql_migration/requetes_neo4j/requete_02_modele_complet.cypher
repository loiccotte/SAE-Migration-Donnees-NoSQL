MATCH (s:Service)-[:SE_TROUVE]->(d:Departement)-[:APPARTIENT_A]->(r:Region),
      (s)-[:APPARTIENT]->(p:Perimetre),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
RETURN s, d, r, p, e, i
LIMIT 5