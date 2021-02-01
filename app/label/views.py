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

    # Make sure that the micrograph hasn't already been labelled by this IP.
    # Only try this a maximum of 100*num_micrographs times.
    num_attempts = 1
    while ip in micrograph.ip_addresses and num_attempts < 100*num_micrographs:
        index = randint(0, num_micrographs-1)
        micrograph = micrographs[randint(0, index)]
        num_attempts += 1

    # Insert the micrograph, index, and IP address into the response.
    response["micrograph"] = micrograph.path
    response["index"] = index
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
    index = request.GET.get("index")

    # Log the the micrograph is being processed.
    logger.info(f"Processing micrograph index {index} from IP {ip}")

    # Get the dataURL.
    data_url = request.GET.get("dataUrl")

    # Get the serialized SVG image.
    svg_serialized = request.GET.get("svgSerialized")

    # Call the Celery task to process the upload.
    process_micrograph_mask.delay(ip, index, data_url, svg_serialized)

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

    # Get the name of the current average image.
    average = request.GET.get("average")

    # Initialise response dictionary.
    response = {}

    logger.info(f"Generating average for image {index}")

    # Call the Celery task to generate the average mask. Don't delay since we
    # require that this task is run before we can return a response.
    response["average"] = create_average_mask(index, average)

    return JsonResponse(response)

def _get_ip_addresss(request):
    """
    Helper function to get the IP address of the client
    making the GET request.
    """
    if request.method == "GET":
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
