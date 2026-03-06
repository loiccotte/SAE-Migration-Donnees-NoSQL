MATCH (s:Service)-[:SE_TROUVE]->(d:Departement),
      (s)-[:ENREGISTRE]->(e:Enregistrement)-[:CONCERNE]->(i:Infraction)
WITH d.nom_dept AS departement, i.libelle AS infraction, SUM(e.nb_faits) AS total
ORDER BY departement, total DESC
WITH departement, COLLECT({infraction: infraction, total: total})[0..3] AS top3
UNWIND top3 AS t
RETURN departement, t.infraction AS infraction, t.total AS total_faits