# PROOF WebUI

Web UI for the PROOF project.

## Setup

### Dependencies

First create a Python 3.7+ virtual environment:

```bash
python -m venv venv_proof
```

Next, install the required Python dependencies:

```bash
venv_proof/bin/pip install -r requirements.txt
```

We now need to download and install the [RabbitMQ](https://www.rabbitmq.com)
message broker which will be used by [Celery](http://www.celeryproject.org)
for running asynchronous tasks. Follow the installation instructions for
your operating system. For Arch Linux, it can be installed and started as
follows:

```bash
pacman -S rabbitmq
systemctl start rabbitmq
```

### Micrographs

No micrographs are provided with this repository. Place any of interest in
the `label/static/micrographs` directory. For now, it is assumed that these
are [PNG](https://en.wikipedia.org/wiki/Portable_Network_Graphics) format.

### Initialising Django

First you'll want to initialise the Django database using the micrograph model:

```bash
venv_proof/bin/python manage.py makemigrations
venv_proof/bin/python manage.py migrate --run-syncdb
```

Next we need to create some micrograph records that can be loaded into the
Django database. Simply run:

```bash
venv_proof/bin/python label/scripts/create_micrograph_data.py
```

This will create a file called `micrographs.json` within the `label/fixtures`
directory. To load it into the database, run:

```bash
venv_proof/bin/python manage.py loaddata label/fixtures/micrographs.json
```

### Starting the Celery message queue

Assuming you have RabbitMQ up and running, simply run:

```bash
venv_proof/bin/celery -A proof worker -B -l info
```

### Start Django

Finally, start the Django server and point your browser at the URL that is
returned.

```bash
venv_proof/bin/python manage.py runserver
```

The default URL is [http://127.0.0.1:8000](http://127.0.0.1:8000), which,
depending on your operating system, may open automatically in your browser.


## Cleanup

If you want to restart from a clean state, simply run the following set of
commands and re-follow the [Django initialsation](#initialising-django)

```bash
rm db.sqlite
rm celery*
find . -path "label/migrations/*.py" -not -name "__init__.py" -delete
find . -path "label/migrations/*.pyc" -delete
```
