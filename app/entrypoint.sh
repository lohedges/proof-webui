#!/bin/sh

# Perform a "clean" start, i.e. trash all existing output.
if ! [ -z ${PROOF_CLEAN_START+x} ]; then
    rm db.sqlite3
    rm celery*
    rm -r label/masks
    rm label/static/micrographs/*.png
    find . -path "label/migrations/*.py" -not -name "__init__.py" -delete
    find . -path "label/migrations/*.pyc" -delete
fi

# Pre-process any raw micrographs.
python label/scripts/pre_process_micrographs.py

python manage.py makemigrations
python manage.py migrate --run-syncdb
python label/scripts/create_micrograph_data.py
python manage.py loaddata label/fixtures/micrographs.json

# Run labelling app in "local" mode.
if ! [ -z ${PROOF_LOCAL+x} ]; then
    PROOF_LOCAL=${PROOF_LOCAL} python manage.py runserver 0.0.0.0:8000
else
    python manage.py runserver 0.0.0.0:8000
fi

exec "$@"
