from io import BytesIO
from PIL import Image, ImageOps

import base64
import imageio
import logging
import numpy as np
import os
import pickle
import uuid

from proof.celery import app
from celery.schedules import crontab
from .models import Micrograph

logger = logging.getLogger(__name__)

@app.task
def process_micrograph_mask(ip, index, data_url, svg_serialized):
    """
    Process the upload of micrograph filament labels as a background task.


    Parameters
    ----------

    ip : str
        The IP address of the client.

    index : int
        The index of the micrograph in the Django database.

    data_url : base64
        The data URL for the micrograph label mask.

    svg_serialized : str
        The serialized SVG image.
    """

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
    mask_name = f"{mask_dir}/" + f"{micrograph.num_labels}".rjust(6, "0")

    # Decode the image, convert to grayscale and threshold to create a binary iamge.
    image = Image.open(BytesIO(base64.b64decode(data_url.split(",")[1])))
    image = image.convert("L")
    image = image.point(lambda x: 0 if x>10 else 255, "1")
    image.save(mask_name + ".png")

    # Write the SVG to file.
    with open(mask_name + ".svg", "w") as f:
        f.write(svg_serialized)

    # Reload the mask as a NumPy array. Make sure this is a 64-bit int since
    # we'll be accumulating the data, i.e. it will go beyond the range of 0-255.
    image = imageio.imread(mask_name + ".png").astype("uint64")

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

    try:
        # Save the updated micrograph record.
        micrograph.save()

        # Log that a the micrograph was updated.
        logger.info(f"Successfully updated record for micrograph '{name}'")

    except:
        # Log that a concurrency issue occurred.
        logger.warning(f"Database concurrency issue for micrograph '{name}'")

        # Re-execute the task if the record has been modified.
        process_micrograph_mask.delay(ip, index, data_url, svg_serialized)

@app.task
def create_average_mask(index, average):
    """
    Write the average mask for a micrograph to disk and return the path to
    the image.


    Parameters
    ----------

    index : int
        The index of the micrograph in the Django database.

    average : str
        The name of the previous average mask that has been served to the
        client.


    Returns
    -------

    path : str
        The path to the average mask.
    """

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
        return f"static/{filename}.png"

    else:
        return "NULL"

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Compute the variance for each set of micrograph masks every hour.
    sender.add_periodic_task(
        crontab(hour="*", minute=0, day_of_week="*"),
        compute_mask_variance.s(),
    )

@app.task
def compute_mask_variance():
    # Log that the periodic variance computation has started.
    logger.info(f"Starting micrograph mask variance computation...")

    # Get the micrographs in the database.
    micrographs = Micrograph.objects.all()

    # Loop over all of the micrographs.
    for micrograph in micrographs:

        # Store the number of labels for this micrograph.
        num_labels = micrograph.num_labels

        # Only compute the variance if there are multiple labels.
        if num_labels > 1:

            # Try to compute the variance until successful. This avoids concurrency
            # issues when a micrograph record is updated while the variance is
            # being calculated.
            while True:

                # Get the name of the micrograph with no path or extension.
                name = micrograph.path.split("/")[2].split(".")[0]

                # Get the current average.
                current_average = pickle.loads(base64.b64decode(micrograph.average))

                # Convert to one-dimensional NumPy array in range 0 to 1.
                avg_array = (current_average/num_labels).flatten() / 255

                # Zero the variance for this micrograph.
                variance = 0

                # Loop over all of the labels for this micrograph.
                for label in range(0, micrograph.num_labels):

                    # Create the directory name for the masks.
                    mask_dir = f"label/masks/{name}"

                    # Create name of the micrograph label mask.
                    mask_name = f"{mask_dir}/" + f"{label}".rjust(6, "0") + ".png"

                    # Load the mask as a NumPy array. Make sure this is a 64-bit int.
                    image = imageio.imread(mask_name).astype("uint64")

                    # Convert to one-dimensional NumPy array in range 0 to 1.
                    img_array = image.flatten() / 255

                    # Accumulate the variance.
                    variance = sum((img_array-avg_array)**2) / len(img_array)

                # Normalise the variance.
                variance /= num_labels

                try:
                    micrograph.variance = variance
                    micrograph.save()

                    # Log that a the micrograph was updated.
                    logger.info(f"Computed mask variance for micrograph '{name}'")

                    # Micrograph record updated. Terminate the while loop.
                    break

                except:
                    # Log that a concurrency issue occurred.
                    logger.warning(f"Database concurrency issue for micrograph '{name}'")

                    # Concurrency error. Re-load the latest micrograph records.
                    micrographs = Micrograph.objects.all()

                    # Return to the top of the while loop.
                    continue

    logger.info(f"Endend micrograph mask variance computation.")
