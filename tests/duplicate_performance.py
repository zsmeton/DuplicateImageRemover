from enum import Enum
import os
import cv2
import numpy as np
import itertools

from src import image_hashing, image_gradient

# TODO: Create better printing system for near tests
# TODO: Add graphing of values for near test (f1, confusion matrix)
# TODO: Create more performance tests
# TODO: Optional, improve design to remove model type interface


class ModelType(Enum):
    PERFECT = 0
    NEAR = 1


class DuplicateFinderModel:
    type = ModelType.PERFECT

    def __init__(self, name="Base Model", **kwargs):
        self.name = name
        pass

    def score_perfect(self, images, actual_sims):
        sims = self.calculate_similarities(images)
        tp, fn, fp, tn = DuplicateFinderModel._calculate_score(sims, actual_sims)

        self._print_confusion(tp, fn, fp, tn)
        print()
        self._print_f1(tp, fn, fp)

    def score_near(self, images, actual_sims):
        raise NotImplementedError()

    def calculate_similarities(self, images):
        """
        Calculate the similarity between a set of images
        Args:
            images: list of opened images from opencv

        Returns: matrix of similarities with values below diagonal = 0
                [[0, 1, 0.5],[0,0, 1],[0,0,0.8]]
        """
        raise NotImplementedError()

    @staticmethod
    def _calculate_score(model_sims, actual_sims):
        """
        Calculates the confusion matrix entries for the prediction
        Args:
            model_sims: models predicted similarity matrix all entries should be 0 or 1
            actual_sims: actual similarity matrix all entries should be 0 or 1

        Returns:
            true_positive, false_negative, false_positive, true_negative
        """
        true_positive, false_negative, false_positive, true_negative = (0, 0, 0, 0)

        for i, model_row in enumerate(model_sims):
            for j, model_sim in enumerate(model_row):
                if j > i:
                    actual_sim = actual_sims[i][j]
                    if model_sim >= 1 and actual_sim >= 1:
                        true_positive += 1
                    elif model_sim < 1 and actual_sim >= 1:
                        false_negative += 1
                    elif model_sim >= 1 and actual_sim < 1:
                        false_positive += 1
                    else:
                        true_negative += 1

        return true_positive, false_negative, false_positive, true_negative

    @staticmethod
    def _calculate_f1(true_positive, false_negative, false_positive):
        if true_positive < 0 or false_negative < 0 or false_positive < 0:
            raise ValueError("All metrics used to calculate the 1 score must be positive")

        if true_positive + false_positive + false_negative == 0:
            return 1

        f1 = true_positive / (true_positive + 0.5 * (false_positive + false_negative))
        return f1

    @staticmethod
    def _print_confusion(true_positive, false_negative, false_positive, true_negative, spacing=6):
        print(" " * spacing, f"{'PP':{spacing}}", f"{'PN':{spacing}}")
        print(f"{'AP':{spacing}}", f"{str(true_positive):{spacing}}", f"{str(false_negative):{spacing}}")
        print(f"{'AN':{spacing}}", f"{str(false_positive):{spacing}}", f"{str(true_negative):{spacing}}")

    @staticmethod
    def _print_f1(true_positive, false_negative, false_positive, spacing=6):
        f1 = DuplicateFinderModel._calculate_f1(true_positive, false_negative, false_positive)
        print(f"{'f1:':{spacing}}", f"{f1:1.2f}")


class HashDuplicateFinderModel(DuplicateFinderModel):
    type = ModelType.PERFECT

    def __init__(self, hash_size=8, name="DHash", **kwargs):
        super().__init__(name=name, **kwargs)
        self.hash_size = hash_size
        self.hashes = None

    def _calculate_hashes(self, images):
        self.hashes = dict()
        for i, image in enumerate(images):
            # Calculate image hash
            hash_val = image_hashing.dhash(image, self.hash_size)
            # Add image to hash list
            p = self.hashes.get(hash_val, [])
            p.append(i)
            self.hashes[hash_val] = p

    def _calculate_similarity_matrix_from_hashes(self, size):
        similarity_matrix = np.zeros((size, size))

        # set similarity to one for all the duplicate image intersections above diagonal
        duplicate_idx_list = [duplicate_idx for duplicate_idx in self.hashes.values() if len(duplicate_idx) > 1]
        for duplicates in duplicate_idx_list:
            for image1_idx in duplicates:
                for image2_idx in duplicates:
                    if image2_idx > image1_idx:
                        similarity_matrix[image1_idx][image2_idx] = 1

        return similarity_matrix

    def calculate_similarities(self, images):
        # Calculate hashes
        self._calculate_hashes(images)
        # Return similarity matrix
        return self._calculate_similarity_matrix_from_hashes(len(images))


class ToleranceSimilarDuplicateFinderModel(DuplicateFinderModel):
    type = ModelType.NEAR

    def __init__(self, tolerances=None, name="Tolerance Base", **kwargs):
        super().__init__(name=name, **kwargs)
        if tolerances is None:
            tolerances = [0.05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, .98, 1]
        self.tolerances = tolerances

    def score_near(self, images, actual_sims):
        # Calculate similarity matrix
        sims = self.calculate_similarities(images)
        # For each tolerance run score_perfect on "stepped" sim matrix
        # "Stepped" meaning if similarity > tolerance the cell is set to 1 and if not 0
        for tolerance in self.tolerances:
            stepped_matrix = [[1 if similarity >= tolerance else 0 for similarity in row] for row in sims]
            print(f"tolerance: {tolerance:1.2f}")
            true_positive, false_negative, false_positive, true_negative = self._calculate_score(stepped_matrix,
                                                                                                 actual_sims)
            self._print_confusion(true_positive, false_negative, false_positive, true_negative)
            print()
            self._print_f1(true_positive, false_negative, false_positive)


class GradientDuplicateFinderModel(ToleranceSimilarDuplicateFinderModel):
    name = "Gradient"

    def __init__(self, vector_size=8, name="Gradient", **kwargs):
        super().__init__(name=name, **kwargs)
        self.vector_size = vector_size
        self.gradients = []

    def _calculate_gradients(self, images):
        self.gradients = [image_gradient.calculate_gradient_vector(image, self.vector_size) for image in images]

    def _calculate_similarity_matrix_from_gradients(self):
        similarity_matrix = np.zeros((len(self.gradients), len(self.gradients)))

        for i, row in enumerate(similarity_matrix):
            for j, elem in enumerate(row):
                if j > i:
                    # Set element equal to the image_similarity
                    similarity_matrix[i][j] = image_gradient.gradient_similarity(self.gradients[i], self.gradients[j])

        return similarity_matrix

    def calculate_similarities(self, images):
        # Calculate gradients
        self.gradients = []
        self._calculate_gradients(images)
        # Use gradients to calculate similarity matrix and return it
        return self._calculate_similarity_matrix_from_gradients()


class PerformanceTest:
    def __init__(self, directory):
        self.directory = directory
        self.file = os.path.join(directory, "config.txt")
        # Create all member variables
        self.images = None
        self.image_paths = None
        self.near_idxs_list = None
        self.duplicate_idxs_list = None
        self.near_matrix = None
        self.perfect_matrix = None
        self.path_index = None
        # Read the data
        self._read_test()
        # initialize images and matrices
        self._open_images()
        self._fill_perfect_matrix()
        self._fill_near_matrix()

    def _read_test(self):
        # TODO: add error checking
        self.path_index = dict()
        self.image_paths = []
        self.duplicate_idxs_list = []
        self.near_idxs_list = []

        # Read in the data
        with open(self.file, 'r') as fin:
            self._read_name(fin)
            self._read_images(fin)
            self._read_similar_list(fin, next_section='similar:', similarity_idxs_list=self.duplicate_idxs_list)
            self._read_similar_list(fin, next_section=None, similarity_idxs_list=self.near_idxs_list)

    def _read_name(self, fin):
        for line in fin:
            line = line.strip()
            # skip blank lines
            if not line or line == 'name:':
                continue
            elif line == 'images:':
                break
            else:
                self.name = line
        else:
            raise EOFError("Invalid file format: expected images section")

    def _read_images(self, fin):
        for line in fin:
            line = line.strip()
            # skip blank lines
            if not line:
                continue
            elif line == 'duplicates:':
                break
            else:
                self.path_index[line] = len(self.image_paths)
                self.image_paths.append(os.path.join(self.directory, "images", line))

        else:
            raise EOFError("Invalid file format: expected duplicate section")

    def _read_similar_list(self, fin, next_section, similarity_idxs_list):
        for line in fin:
            line = line.strip()
            if not line:
                continue
            if line == next_section:
                break
            else:
                similar_idx = [self.path_index[img_path] for img_path in line.split() if img_path]
                similarity_idxs_list.append(similar_idx)
        else:
            if next_section:
                raise EOFError(f"Invalid file format: expected {next_section} section")

    def _get_similarity_matrix(self, similar_idxs_list):
        """
        Returns a similarity matrix for given list of similar indexes
        Args:
            similar_idxs_list: list of index list ex: [[0,1],[2,3]]

        Returns:
            a matrix where 1s are placed in all the indexes where two similar indexes cross
            though not below the diagonal ex: [[0,1,0,0],[0,0,0,0],[0,0,0,1],[0,0,0,0]]
        """
        similarity_matrix = np.zeros((len(self.image_paths), len(self.image_paths)))

        # set similarity to one for all the duplicate image intersections above diagonal
        for duplicates in similar_idxs_list:
            for image1_idx in duplicates:
                for image2_idx in duplicates:
                    if image2_idx > image1_idx:
                        similarity_matrix[image1_idx][image2_idx] = 1

        return similarity_matrix

    def _fill_perfect_matrix(self):
        # Set matrix to created perfect matrix
        self.perfect_matrix = self._get_similarity_matrix(self.duplicate_idxs_list)

    def _fill_near_matrix(self):
        """
        Creates and fills the values for the nearly similar matrix
        """
        combined_near_perfect_idx = list(itertools.chain(self.duplicate_idxs_list, self.near_idxs_list))
        self.near_matrix = self._get_similarity_matrix(combined_near_perfect_idx)

    def _open_images(self):
        # TODO: add error checking
        self.images = [cv2.imread(image_path) for image_path in self.image_paths]


class DuplicatePerformanceTestManager:
    def __init__(self, models=None, tests=None):
        if models is None:
            models = []
        self.models = models

        if tests is None:
            tests = []
        self.tests = tests

    def add_model(self, model: DuplicateFinderModel):
        # TODO: Error check argument is model
        self.models.append(model)

    def clear_models(self):
        self.models = []

    def add_test(self, test: PerformanceTest):
        # TODO: Error check argument is test
        self.tests.append(test)

    def clear_tests(self):
        self.tests = []

    def run(self, test: PerformanceTest, spacing=30):
        print("=" * spacing)
        print(test.name)
        print("=" * spacing)
        for model in self.models:
            if model.type == ModelType.PERFECT:
                print(f"{model.name}" + "-" * (spacing - len(model.name)))
                model.score_perfect(test.images, test.perfect_matrix)
                print("-" * spacing)
            else:
                print(f"{model.name}" + "-" * (spacing - len(model.name)))
                print("Perfect scoring:")
                model.score_perfect(test.images, test.perfect_matrix)
                print()
                print("Near scoring:")
                model.score_near(test.images, test.near_matrix)
                print("-" * spacing)

    def run_all(self, **kwargs):
        for test in self.tests:
            self.run(test, **kwargs)


if __name__ == "__main__":
    # Create manager
    manager = DuplicatePerformanceTestManager()

    # Create models
    hash_model = HashDuplicateFinderModel()
    manager.add_model(hash_model)
    grad_8_model = GradientDuplicateFinderModel(name="Gradient-8",
                                                tolerances=[.6, .7, .75, .8, .85, .9, .95, .98, 1.0])
    manager.add_model(grad_8_model)
    grad_32_model = GradientDuplicateFinderModel(name="Gradient-32",
                                                 tolerances=[.6, .7, .75, .8, .85, .9, .95, .98, 1.0])
    manager.add_model(grad_32_model)

    # Create tests
    p1 = PerformanceTest(os.path.join("performance_tests", "basic"))
    manager.add_test(p1)
    p2 = PerformanceTest(os.path.join("performance_tests", "highly_similar"))
    manager.add_test(p2)

    # run tests
    manager.run_all()
