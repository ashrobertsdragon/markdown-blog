#!/usr/bin/bash
uv build --clear backend
cp backend/dist/backend-* /var/www/ashlab/package/backend/
scripts/generate_index.py backend