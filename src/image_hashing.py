import os
import argparse
import math
import time
import imutils
from imutils import paths
import cv2
from tqdm import tqdm

# TODO: Add to unit tests

def dhash(image, hash_size=8):
    # convert the image to grayscale and resize the grayscale image,
    # adding a single column (width) so we can compute the horizontal
    # gradient
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size))
    # compute the (relative) horizontal gradient between adjacent
    # column pixels
    diff = resized[:, 1:] > resized[:, :-1]
    # convert the difference image to a hash and return it
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])


def async_open_and_hash(image_path, hash_size=8):
    # load the input image and compute the hash
    image = cv2.imread(image_path)
    try:
        hash_val = dhash(image,hash_size)
    except cv2.error:
        raise RuntimeError(f'Failed to hash image: {image}')
    
    # grab all image paths with that hash, add the current image
    # path to it, and store the list back in the hashes dictionary
    return hash_val, image_path
