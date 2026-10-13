#!/bin/sh
set -e

# Apply DB migrations before starting the app.
alembic upgrade head

exec "$@"
