MATCH ()-[r]->()
RETURN type(r) AS relation, COUNT(r) AS nombre
ORDER BY nombre DESC