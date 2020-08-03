#!/bin/sh

python manage.py makemigrations
python manage.py migrate --run-syncdb
python label/scripts/create_micrograph_data.py
python manage.py loaddata label/fixtures/micrographs.json
python manage.py runserver 0.0.0.0:8000
exec "$@"
