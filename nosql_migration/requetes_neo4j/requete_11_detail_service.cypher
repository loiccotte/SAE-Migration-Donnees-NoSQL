MATCH (s:Service)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WHERE s.code_service = '1'
RETURN s, e, i
LIMIT 20