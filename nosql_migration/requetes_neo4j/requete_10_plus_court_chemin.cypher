MATCH (a:Departement {code_dept: '75'}),
      (b:Departement {code_dept: '13'}),
      path = shortestPath((a)-[:EST_ADJACENT*]-(b))
RETURN path