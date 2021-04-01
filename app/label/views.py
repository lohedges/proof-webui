from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from io import BytesIO
from PIL import Image, ImageOps
from random import randint

import base64
import imageio
import logging
import numpy as np
import os
import pickle
import uuid

from .models import Micrograph
from .tasks import create_average_mask, process_micrograph_mask

logger = logging.getLogger(__name__)

# Determine whether proof is being run locally.
if os.environ.get("PROOF_LOCAL") != None:
    proof_local = True
else:
    proof_local = False

def index(request):
    """
    Render the labeller landing page.
    """
    return render(request, "index.html", {})

def micrograph(request):
    """
    Serve a random micrograph image to the client, making sure that the
    image hasn't previously been sent to the same IP addresss.
    """
    # Initialise response dictionary.
    response = {}

    # Get the IP address of the client.
    ip = _get_ip_addresss(request)

    # Get the micrographs in the database.
    micrographs = Micrograph.objects.all()

    # Store the number of micrographs.
    num_micrographs = len(micrographs)

    # Choose a random micrograph.
    index = randint(0, num_micrographs-1)
    micrograph = micrographs[randint(0, index)]

    # Whether labelling is finished for this IP address.
    is_finished = True

    # Make sure that the micrograph hasn't already been labelled by this IP.
    # Only try this a maximum of 100*num_micrographs times. We could store
    # IP addresses as a separate model and log the micrographs that have been
    # labelled by each IP, but this will suffice.
    num_attempts = 1
    for x in range(0, 100*num_micrographs):
        index = randint(0, num_micrographs-1)
        micrograph = micrographs[index]
        if not ip in micrograph.ip_addresses:
            is_finished = False
            break

    # Insert the micrograph, index, and IP address into the response.
    if not is_finished:
        response["micrograph"] = micrograph.path
        response["index"] = index
        response["ip"] = ip
    else:
        response["micrograph"] = "static/complete.png"
        response["index"] = -1
        response["ip"] = ip

    # Log the micrograph and IP address.
    logger.info(f"Serving micrograph index {index} to IP {ip}")

    return JsonResponse(response)

def upload(request):
    """
    Handle the upload of micrograph filament labels.
    """

    # Get the IP address of the client.
    ip = _get_ip_addresss(request)

    # Get the index of the micrograph.
    index = request.POST.get("index")

    # Log the the micrograph is being processed.
    logger.info(f"Processing micrograph index {index} from IP {ip}")

    # Get the dataURL.
    data_url = request.POST.get("dataUrl")

    # Get the serialized SVG image.
    svg_serialized = request.POST.get("svgSerialized")

    # Call the Celery task to process the upload. Don't delay if running
    # locally since we require that this task is run before we can
    # return a response.
    if proof_local:
        process_micrograph_mask(ip, int(index), data_url, svg_serialized)
    else:
        process_micrograph_mask.delay(ip, int(index), data_url, svg_serialized)

    # Dummy response for now.
    response = {}

    return JsonResponse(response)

def average(request):
    """
    Serve an image showing the average labels for the current
    micrograph.
    """

    # Get the index of the current micrograph.
    index = request.GET.get("index")

    # Index is set to -1 if labelling is complete.
    if int(index) >= 0:

        # Get the name of the current average image.
        average = request.GET.get("average")

        # Initialise response dictionary.
        response = {}

        logger.info(f"Generating average for image {index}")

        # Call the Celery task to generate the average mask. Don't delay if
        # running locally since we require that this task is run before we can
        # return a response.
        if proof_local:
            response["average"] = create_average_mask(int(index), average)
        else:
            response["average"] = create_average_mask.delay(int(index), average)

        return JsonResponse(response)

    else:
        return JsonResponse({"average" : "NULL"})

def _get_ip_addresss(request):
    """
    Helper function to get the IP address of the client
    making the GET request.
    """
    if request.method in ["GET", "POST"]:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[-1].strip()
        elif request.META.get("HTTP_X_REAL_IP"):
            ip = request.META.get("HTTP_X_REAL_IP")
        else:
            ip = request.META.get("REMOTE_ADDR")

        return ip
    else:
        return None
