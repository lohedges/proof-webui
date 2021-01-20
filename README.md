# PROOF WebUI

Web UI for the PROOF project.

## Setup

The following assumes that you're working within the `app` directory.

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

(Note that this uses a combined queue for both regular and periodic (beat)
tasks.)

### Start Django

Finally, start the Django server and point your browser at the URL that is
returned.

```bash
venv_proof/bin/python manage.py runserver
```

The default URL is [http://127.0.0.1:8000](http://127.0.0.1:8000), which,
depending on your operating system, may open automatically in your browser.

Currently there is no landing page at the default URL and you'll need to
navigate to [http://127.0.0.1:8000/label](http://127.0.0.1:8000/label) to
launch the PROOF filament labelling web app.


## Cleanup

If you want to restart from a clean state, simply run the following set of
commands and re-follow the [Django initialsation](#initialising-django)

```bash
rm db.sqlite3
rm celery*
find . -path "label/migrations/*.py" -not -name "__init__.py" -delete
find . -path "label/migrations/*.pyc" -delete
```

## Using the filament labeller

![Filament labeller](/app/label/static/screenshot.png?raw=true)

Filaments can be labelled using mouse or touch input. In mouse mode, two
different drawing modes are provided:

* Freehand mode allows you to trace the path of a filament by pressing and
holding the left mouse button. The path is finished when the button is
lifted.
* Line modes allows filaments to be labelled via piecewise linear line segments.
Pressing the right mouse button activates this mode and drops the first line
marker. Right-clicking on another location will then draw a line from the last
marker. Simpy repeat the process until the filament is labelled. Left-clicking
will finish drawing and register the label.

It is possible to change the line width using the slider on the left-hand
panel. The width is applied to the last filament that was drawn, allowing
you to use a different width for each filament.

Errors can be corrected by clicking "Clear last label" or "Clear all labels".
Clicking "Toggle average" will show the average label for the micrograph,
averaged over all masks that have been uploaded. (Note that nothing will be
shown if the micrograph has not yet been labelled.) If you don't want to label
the current micrograph, simply click "New micrograph" to get another random
micrograph. Finally, to upload a completed micgrograph label, click on
"Upload labels".

# Docker

To run the filament labeller withing a Docker container, simply run:

```bash
docker-compose up -d
```

On Linux/macOS you can run as a your regular user with:

```bash
UID=$(id -u) GID=$(id -g) docker-compose up -d
```

Once again, the labeller can be accessed at [http://127.0.0.1:8000/label](http://127.0.0.1:8000/label).

(Note that this assumes that you have manually added micrographs to the
`app/label/static/micrographs` directory.)

To shutdown:

```bash
docker-compose down
```

To follow logs:

```bash
docker-compose logs -f
```

If you want to start afresh, i.e. delete the micrograph database and any labels, run:

```bash
PROOF_CLEAN_START=1 docker-compose up -d
```

On Windows you would need to do the following (assuming PowerShell):

```powershell
$env:PROOF_CLEAN_START=1; docker-compose up -d
```

Then remove the environment variable when you're done:

```powershell
Remove-Item Env:\PROOF_CLEAN_START
```
