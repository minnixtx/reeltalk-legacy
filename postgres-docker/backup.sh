#!/bin/bash
info() { echo >&2 "[$(date --iso-8601=seconds)] $*"; }

if [ -z "$PGDATABASE" ]; then
    info "backup: Database not specified, defaulting to reeltalk"
fi
if [ -z "$PGUSER" ]; then
    info "backup: Database user not specified, defaulting to reeltalk"
fi
BACKUP_DB=${PGDATABASE:-reeltalk}
BACKUP_USER=${PGUSER:-reeltalk}
filename=backup_${BACKUP_DB}_$(date +%F)
pg_dump -U "${BACKUP_USER}" "${BACKUP_DB}" --file "/backups/$filename.sql"
info "backup: completed backup of $BACKUP_DB to /backups/$filename.sql"
