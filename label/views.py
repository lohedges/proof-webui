from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from PIL import Image, ImageOps
from random import randint
from io import BytesIO

import base64
import os

from .models import Micrograph

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

    # Choose a random micrograph.
    index = randint(0, len(micrographs)-1)
    micrograph = micrographs[randint(0, index)]

    # Make sure that the micrograph hasn't already been labelled by this IP.
    while ip in micrograph.ip_addresses:
        index = randint(0, len(micrographs)-1)
        micrograph = micrographs[randint(0, index)]

    # Insert the micrograph, index, and IP address into the response.
    response["micrograph"] = micrograph.path
    response["index"] = index
    response["ip"] = ip

    return JsonResponse(response)

def upload(request):
    """
    Handle the upload of micrograph filament labels.
    """

    # Get the IP address of the client.
    ip = _get_ip_addresss(request)

    # Get the index of the micrograph.
    index = request.GET.get("index")

    # Get the dataURL.
    data_url = request.GET.get("dataUrl")

    # Get the micrograph from the database.
    micrograph = Micrograph.objects.get(id=str(index))

    # Make sure this micrograph hasn't already been labelled.
    if ip in micrograph.ip_addresses:
        raise ValueError("This IP address has alread submitted a label for "
                         "this micrograph.")

    # Get the name of the micrograph with no path or extension.
    name = micrograph.path.split("/")[2].split(".")[0]

    # Increment the number of micrograph labels.
    micrograph.num_labels += 1

    # Record that this IP address has labelled the micrograph.
    micrograph.ip_addresses.append(ip)

    # Create the directory name for the masks.
    mask_dir = f"label/masks/{name}"

    # Create a mask directory for this micrograph if it doesn't already exist.
    if not os.path.isdir(mask_dir):
        os.makedirs(mask_dir)

    # Create name of the micrograph label mask.
    mask_name = f"{mask_dir}/" + f"{micrograph.num_labels}".rjust(6, "0") + ".png"

    # Decode the image, convert to grayscale and threshold to create a binary iamge.
    image = Image.open(BytesIO(base64.b64decode(data_url.split(",")[1])))
    image = image.convert("L")
    image = image.point(lambda x: 0 if x>10 else 255, "1")
    image.save(mask_name)

    # Save the updated micrograph record.
    micrograph.save()

    response = {}

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
