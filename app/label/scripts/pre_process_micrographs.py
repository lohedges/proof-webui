#!/usr/bin/env python

# Python script to pre-process raw micrographs for web use.

from skimage import exposure
from skimage import io
from skimage import transform

import argparse
import glob
import mrcfile
import os
import skimage

parser = argparse.ArgumentParser(description="Pre-process MRC files for web use.")
parser.add_argument("--directory", help="The path to the raw MRC files.",
                                   default="label/raw_micrographs",
                                   type=str)
args = parser.parse_args()

# Store the micgrograph directory.
micrograph_directory = args.directory

# Make sure the directory exists.
if not os.path.isdir(micrograph_directory):
    raise IOError(f"Directory doesn't exist: {micrograph_directory}")

# Glob all of the mrc files in the directory.
micrographs = glob.glob(f"{micrograph_directory}/*.mrc")

# Pre-process all of the micrographs.
for idx, micrograph in enumerate(micrographs):
    filename = os.path.basename(micrograph)
    print(f"Processing micrograph: {filename}")

    with mrcfile.open(micrograph, permissive=True) as mrc:
        h = mrc.header
        d = mrc.data

    d = exposure.equalize_hist(d)
    normalised = skimage.img_as_ubyte(d)
    resized = transform.resize(normalised, (800, 800))

    filename = filename.split(".")[0]
    io.imsave(f"label/static/micrographs/{filename}.png", resized)
