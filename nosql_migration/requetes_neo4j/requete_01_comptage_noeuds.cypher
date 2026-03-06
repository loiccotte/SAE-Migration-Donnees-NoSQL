MATCH (n)
RETURN labels(n)[0] AS label, COUNT(n) AS nombre
ORDER BY nombre DESC