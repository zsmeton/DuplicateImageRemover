import cv2
from kivy.logger import Logger


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
    if image is None:
        Logger.warning(f"Failed to load image {image_path}")
        return None
    image_ratio = image.shape[1] / image.shape[0]
    try:
        hash_val = dhash(image, hash_size)
    except cv2.error:
        Logger.warning(f'Failed to hash image: {image}')
        return None

    # grab all image paths with that hash, add the current image
    # path to it, and store the list back in the hashes dictionary
    return hash_val, image_path, image_ratio
