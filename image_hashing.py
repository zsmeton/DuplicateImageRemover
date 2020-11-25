import os
import argparse
import math
import time
from multiprocessing import Pool
import imutils
from imutils import paths
import cv2
from tqdm import tqdm


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

def create_montage_width_constrained(image_paths, image_dim=(300,300), montage_width=3):
    """
    Creates a numpy array for cv2 montage display with a specific width
    :param list[string] image_paths: List of image paths to open and turn into montage
    :param tuple[int,int] optional image_dim: The desired dimensions for each image in the montage 
    (width,height)
    :param int optional width: Width of the montage
    """
    # Create image list
    num_images = len(image_paths)
    images = []
    for image_path in image_paths:
        image = cv2.imread(image_path)
        images.append(image)

    # Find dimensions of padded image
    montage_height = int(math.ceil(float(num_images) / float(montage_width)))
    montage = imutils.build_montages(images, image_dim, (montage_width, montage_height))[0]
    return montage 

def get_image_hashes(image_paths, threads=1, loading_bar=False):
    """Hashes all of the images in the directory path and returns a dictionary with the
    hash as the key and a list of image paths as the values.

    Args:
        directory_path (str): Path to the directory containing the images to hash.
        threads (int, optional): Number of processes spawned to find hashes
        loading_bar (bool, optional): Whether or not to display a loading bar. Defaults to False.

    Returns:
        dict: image dictionary
    """
    if not isinstance(threads, int):
        raise ValueError("threads must be an integer")
    if threads < 1:
        raise ValueError(f"threads must be greater than 0, which {threads} is not")
    if not isinstance(loading_bar, bool):
        raise ValueError(f"loading_bar should be a boolean value")

    hashes = {}
    # loop over our image paths and make hashes
    with Pool(processes=threads) as pool:
        multiple_results = [pool.apply_async(async_open_and_hash, (image_path, 16)) 
                            for image_path in image_paths]
        for res in tqdm(multiple_results, desc='hashing images', disable=(not loading_bar)):
            result = res.get()
            if result is not None:
                h,image_path = result
                # grab all image paths with that hash, add the current image
                # path to it, and store the list back in the hashes dictionary
                p = hashes.get(h, [])
                p.append(image_path)
                hashes[h] = p

    return hashes

def get_duplicates_from_hash_dict(hashed_images):
    """Turns a hashed image dictionary into a list of duplicates

    Args:
        hashed_images (dict[int,list[str]]): dictionary with key of hash and value
        a list of images with the same hash

    Returns:
        list[list[str]]: list containing lists of duplicate images
    """
    duplicates = []
    for images in hashed_images.values():
        if len(images) > 1:
            duplicates.append(images)
    return duplicates

if __name__ == "__main__":
    # Get the width of the command line
    cmd_rows, cmd_columns = os.popen('stty size', 'r').read().split()
    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--dataset", required=True,
        help="path to input dataset")
    ap.add_argument("-r", "--remove", type=int, default=-1,
        help="whether or not duplicates should be removed (i.e., dry run)")
    ap.add_argument("-t", "--threads", type=int, default=4,
        help="how many threads to use when hashing images")
    args = vars(ap.parse_args())

    # grab the paths to all images in our input dataset directory and
    # then initialize our hashes dictionary
    print("[INFO] computing image hashes...")
    image_paths = list(paths.list_images(args["dataset"]))
    hash_dict = get_image_hashes(image_paths, threads=args["threads"], loading_bar=True)
    duplicate_images = get_duplicates_from_hash_dict(hash_dict)

    # loop over the duplicate images
    for images in duplicate_images:
        # check to see if there is more than one image with the same hash
        images = sorted(images)[::-1]
        # check to see if this is a dry run
        if args["remove"] <= 0:
            # create montage for the hash
            montage = create_montage_width_constrained(images)
            
            # show the montage for the hash
            print("[INFO] images:")
            for image_path in images:
                print(f"\t{image_path}")
            cv2.imshow("Montage", montage)
            cv2.waitKey(0)
        else:
            montage = None
            # create montage for the hash
            montage = create_montage_width_constrained(images)    
            # show the montage for the hash
            print("[INFO] images:")
            for image_path in images:
                print(f"\t{image_path}")
            
            ok_flag = True
            while ok_flag:
                cv2.imshow("Montage", montage)
                k = cv2.waitKey(1) & 0xFF
                if k == ord('d'):
                    print("deleting photos")
                    # TODO: Add actual deleting of photos
                    ok_flag = False
                elif k != 255:
                    ok_flag = False
            time.sleep(0.5)