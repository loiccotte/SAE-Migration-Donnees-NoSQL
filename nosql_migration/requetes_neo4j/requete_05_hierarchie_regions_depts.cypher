MATCH (d:Departement)-[:APPARTIENT_A]->(r:Region)
RETURN d, r