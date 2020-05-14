#!/usr/bin/env python

# Python script to generate initial micrograph records for the Django database.

import glob
import json
import os

# Figure out which directory we're in.
if os.path.isdir("static/micrographs"):
    base = ""
elif os.path.isdir("label/static/micrographs"):
    base = "label/"
else:
    raise Exception("Please run this script from within the top-level "
                    "or 'label' directory.")

# Glob all of the micrograph PNG images.
micrographs = glob.glob(base + "static/micrographs/*png")

# Create a list to store the JSON object.
data = []

# Loop over each micrograph and create a model entry.
print("Generating micrograph records...")
for pk, micrograph in enumerate(micrographs):
    micrograph = micrograph.strip(base)
    record = {
               "model" : "label.Micrograph",
               "pk" : pk,
               "fields" : {
                             "path" : micrograph
                          }
             }
    data.append(record)
    print(f" {record}")
print("Done!")

# Dump the JSON data to a fixture file.
with open(base + "fixtures/micrographs.json", "w") as f:
    json.dump(data, f, indent=2)
