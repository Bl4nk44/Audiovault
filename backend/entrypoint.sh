#!/bin/sh
set -e

echo "Bootstrapping database (initial schema / migrations)..."
python -m app.db.bootstrap

echo "Starting application..."
exec "$@"
