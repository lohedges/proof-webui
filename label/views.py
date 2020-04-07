from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from io import BytesIO
from PIL import Image, ImageOps
from random import randint

import base64
import imageio
import numpy as np
import os
import pickle
import uuid

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
        num_attemps += 1

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

    # Get the name of the micrograph with no path or extension.
    name = micrograph.path.split("/")[2].split(".")[0]

    # Increment the number of micrograph labels.
    micrograph.num_labels += 1

    # Record that this IP address has labelled the micrograph. The IP address
    # can appear multiple times if they have labelled all of the current m#icrographs.
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

    # Reload the mask as a NumPy array. Make sure this is a 64-bit int since
    # we'll be accumulating the data, i.e. it will go beyond the range of 0-255.
    image = imageio.imread(mask_name).astype("uint64")

    # Add to the running average.
    if micrograph.num_labels > 1:
        # Get the current average.
        current_average = pickle.loads(base64.b64decode(micrograph.average))

        # Convert images to one-dimensional NumPy arrays in range 0 to 1.
        img_array = image.flatten() / 255
        avg_array = (current_average/micrograph.num_labels).flatten() / 255

        # Work out the "similarity" for this mask.
        similarity = sum((img_array-avg_array)**2) / len(img_array)
        micrograph.similarity += similarity

        # Update the running average.
        image += current_average

    # Serialize the image and convert to base64.
    image_bytes = pickle.dumps(image)
    image_bytes = base64.b64encode(image_bytes)

    # Store the updated average.
    micrograph.average = image_bytes

    # Save the updated micrograph record.
    micrograph.save()

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

    # Get the micrograph in the database.
    micrograph = Micrograph.objects.get(pk=index)

    # Only process average if a label has been uploaded.
    if micrograph.num_labels > 0:
        # Load the current average label.
        current_average = pickle.loads(base64.b64decode(micrograph.average))
        current_average = (current_average / micrograph.num_labels).astype("uint8")

        # Delete the existing image.
        if average:
            filename = f"label/static/{average.split('static/')[1]}"
            if os.path.exists(filename):
                os.remove(filename)

        # Create a random 64-bit integer string for the file.
        filename = str(uuid.uuid1().int>>64)

        # Write the average labels to disk.
        imageio.imwrite(f"label/static/{filename}.png", current_average)

        # Insert the micrograph, index, and IP address into the response.
        response["average"] = f"static/{filename}.png"

    else:
        response["average"] = "NULL"

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
