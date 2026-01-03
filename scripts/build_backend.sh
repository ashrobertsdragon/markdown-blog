#!/usr/bin.bash
uv build --clear monorepo/backend
cp backend/dist/backend-* /var/www/ashlab/package/backend/
generate_index.py backend