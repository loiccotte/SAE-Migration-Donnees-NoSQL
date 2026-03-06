MATCH (d:Departement {code_dept: '75'})-[:EST_ADJACENT]-(voisin:Departement)
RETURN d, voisin