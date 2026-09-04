#!/usr/bin/env bash
# Seed the demo user + synthetic company (local dev; assumes backend venv active).
set -euo pipefail
cd "$(dirname "$0")/../backend"
alembic upgrade head
python -m app.seed
echo "Seeded. Login: demo@example.com / demo1234"
