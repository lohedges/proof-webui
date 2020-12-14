#!/bin/sh

if ! [ -z ${PROOF_CLEAN_START+x} ]; then
    rm db.sqlite3
    rm celery*
    rm -r label/masks
    find . -path "label/migrations/*.py" -not -name "__init__.py" -delete
    find . -path "label/migrations/*.pyc" -delete
fi

python manage.py makemigrations
python manage.py migrate --run-syncdb
python label/scripts/create_micrograph_data.py
python manage.py loaddata label/fixtures/micrographs.json
python manage.py runserver 0.0.0.0:8000
exec "$@"
