import cv2
import numpy as np


def normalize(v):
    """
    Returns vector v normalized to length 1
    Args:
        v: array to normalize

    Returns:
    normalized vector
    """
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def calculate_horizontal_gradient(image, image_size=8):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (image_size + 1, image_size))
    # compute the (relative) horizontal gradient between adjacent
    # column pixels
    diff = resized[:, 1:] - resized[:, :-1]
    return diff


def calculate_gradient_vector(image, vector_size=8):
    """
    Calculates the normalized gradient vector for an image
    Args:
        image: An opened cv2 image to find the gradient vector
        vector_size: the size of the vector to output

    Returns:
        numpy array of vector_size and length 1
    """
    diff = calculate_horizontal_gradient(image, vector_size)
    # Flatten the image
    flatten = diff.flatten()
    # diff_vector = diff.mean(axis=1)
    return normalize(flatten)


def async_open_and_gradient(image_path, **kwargs):
    # load the input image and compute the hash
    image = cv2.imread(image_path)
    try:
        gradient_vector = calculate_gradient_vector(image, **kwargs)
    except cv2.error:
        raise RuntimeError(f'Failed to calculate image gradient: {image}')

    # grab all image paths with that hash, add the current image
    # path to it, and store the list back in the hashes dictionary
    return gradient_vector, image_path


def image_similarity(image1_gradient, image1_path, image2_gradient, image2_path):
    # compute dot product
    dot_product = max(min(np.dot(image1_gradient, image2_gradient), 1), -1)
    angle = np.arccos(dot_product)  # angle of 0 means exactly the same, 2pi = perfectly opposite
    percentage = 1 - (angle/(2*np.pi))
    return percentage, image1_path, image2_path


if __name__ == "__main__":
    image = cv2.imread("../tests/images/wolf.jpg")
    gradient_img = calculate_horizontal_gradient(image, 50)
    cv2.imshow("image", gradient_img)
    cv2.waitKey()