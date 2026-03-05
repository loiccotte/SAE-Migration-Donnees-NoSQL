#!/bin/bash
# Charge le dump Neo4j si la base est vide (premier lancement uniquement)

DUMP_FILE="/dumps/neo4j.dump"
MARKER="/data/databases/.imported"

if [ -f "$DUMP_FILE" ] && [ ! -f "$MARKER" ]; then
    echo "==> Chargement du dump Neo4j..."
    neo4j-admin database load --from-path=/dumps neo4j --overwrite-destination=true
    touch "$MARKER"
    echo "==> Dump Neo4j charge avec succes"
else
    echo "==> Dump deja charge ou absent, skip"
fi

# Lancer Neo4j normalement
exec /startup/docker-entrypoint.sh neo4j
