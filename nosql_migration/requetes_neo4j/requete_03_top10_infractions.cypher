MATCH (e:Enregistrement)-[:CONCERNE]->(i:Infraction)
RETURN i.libelle AS infraction, SUM(e.nb_faits) AS total_faits
ORDER BY total_faits DESC
LIMIT 10