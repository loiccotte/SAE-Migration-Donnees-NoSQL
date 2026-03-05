#!/bin/bash
set -e

sed -e '/^\restrict/d' \
    -e '/^\unrestrict/d' \
    -e "s/OWNER TO postgres/OWNER TO $POSTGRES_USER/g" \
    /dumps/dump.sql \
    | psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "CREATE OR REPLACE VIEW service_perimetre AS SELECT code_service, id_perimetre FROM appartient;"

echo "OK - Dump SQL chargé avec succès"
