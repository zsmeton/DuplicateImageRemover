import threading
from multiprocessing import Pool, Value
import platform
import functools
import time
import cv2
from python_algorithms.basic.union_find import UF

from kivy.properties import ObjectProperty, ListProperty, AliasProperty, StringProperty, NumericProperty
from kivy.event import EventDispatcher
from kivy.clock import mainthread
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from kivy.factory import Factory
from src import image_hashing, image_gradient, running_average
from src.stoppable_pool import StoppablePool

# Features
# TODO: Improve estimate time algorithm
# TODO: Add back button
# TODO: Fix this stuff so the pool gets terminated on application close
# TODO: Fix pooling so errors thrown in pool get handled (pop up for user or dismissed)
# TODO: Add caching of info in duplicate controllers for if we cancel, change a param and re-run
# TODO: Create a HOG based duplicate finder
# TODO: Create n-dimensional neighbor/percentage based finder for efficient neighbor checking
# TODO: Create duplicate finder base class for methods which use feature vectors
# TODO: Create base function which takes data, a function, and performs StoppablePool
#  with pause and cancel and returns result


class DuplicateFinderProgress(EventDispatcher):
    """
    Stores the DuplicateFinder progress
    """
    path = StringProperty("")  # Last path processed
    index = NumericProperty(0)  # Current index in list of image paths processed
    total = NumericProperty(10)  # Number of images to check


class DuplicateFinderProgressBase(RelativeLayout, DuplicateFinderProgress):
    """
    Base class for various DuplicateFinder progress bars
    """
    pass


class DuplicateFinderProgressBar(DuplicateFinderProgressBase):
    """
    Standard progress bar for DuplicateFinder views
    """
    pass


class DuplicateFinderEstimatingProgressBar(DuplicateFinderProgressBase):
    """ Progress bar with estimate text
    """
    estimate_text_prefix = StringProperty("eta: ")
    estimate_text = StringProperty("")
    pass


class DuplicateFinderLayout(FloatLayout):
    controller = ObjectProperty()
    __events__ = ('on_start', 'on_stop', 'on_cancel', 'on_resume', 'on_finish')

    def on_start(self):
        """ Start event handler
        """
        pass

    def on_stop(self):
        """ Stop event handler
        """
        pass

    def on_cancel(self):
        """ Cancel event handler
        """
        pass

    def on_resume(self):
        """ Resume event handler
        """
        pass

    def on_finish(self):
        """ Finish event handler
        """
        pass


class DuplicateFinderProgressLayoutBase(DuplicateFinderLayout):
    progress_bar = ObjectProperty()

    def __init__(self, **kwargs):
        # unregister if already registered...
        Factory.unregister('Placeholder')
        Factory.register('Placeholder', cls=self.placeholder)

        super().__init__(**kwargs)

        self._update_progress_bar_ev = None
        self._update_dt = .05

    def on_start(self):
        """ Start event handler
        """
        if super().on_start():
            return True
        self._start_update_progress_bar()

    def on_resume(self):
        """ Resume event handler
        """
        if super().on_resume():
            return True
        self._start_update_progress_bar()

    def on_stop(self):
        """ Stop event handler
        """
        if super().on_stop():
            return True
        self._stop_update_progress_bar()

    def on_cancel(self):
        """ Cancel event handler
        """
        if super().on_cancel():
            return True
        self._stop_update_progress_bar()

    def on_finish(self):
        """ Finish event handler
        """
        if super().on_finish():
            return True
        self._stop_update_progress_bar()

    def _stop_update_progress_bar(self):
        """ Cancels the event scheduled to update the progress bar if it exists
        """
        ev = self._update_progress_bar_ev

        if ev is not None:
            ev.cancel()

    def _start_update_progress_bar(self):
        """ Creates a scheduled event to update the progress bar if one doesn't already exist
        """
        ev = self._update_progress_bar_ev

        if ev is None:
            ev = self._update_progress_bar_ev = Clock.schedule_interval(self._update_progress_bar, self._update_dt)
        ev()

    def _update_progress_bar(self, *args):
        """ Updates the progress bar value to the controllers progress

        Returns:
        """
        if self.controller:
            self.progress_bar.path = self.controller.progress.path
            self.progress_bar.index = self.controller.progress.index
            self.progress_bar.total = self.controller.progress.total


class DuplicateFinderProgressLayout(DuplicateFinderProgressLayoutBase):
    placeholder = DuplicateFinderProgressBar


class DuplicateFinderEstimatingLayout(DuplicateFinderProgressLayout):
    placeholder = DuplicateFinderEstimatingProgressBar

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elapsed_time = 0
        self.last_time = None
        self.running_operation_time_average = running_average.RunningAverage(20)

    def on_start(self):
        if super().on_start():
            return True
        self.elapsed_time = 0
        self.last_time = time.time()

    def on_stop(self):
        if super().on_stop():
            return True
        self.last_time = None

    def on_resume(self):
        if super().on_resume():
            return True
        self.last_time = time.time()

    def _calculate_remaining_time(self):
        # Check if we can/ should update
        if self.last_time is None or self.controller is None:
            return None

        # Nice variable names
        total_ops = self.controller.progress.total
        performed_ops = self.controller.progress.index if self.controller.progress.index > 0 else 1
        current_time = time.time()

        # Update elapsed time and last time
        self.elapsed_time += current_time - self.last_time
        self.last_time = current_time

        # Update time per operation
        time_per_operation = self.elapsed_time / performed_ops
        self.running_operation_time_average.add(time_per_operation)
        time_per_operation = self.running_operation_time_average.average

        # Calculate remaining time
        remaining_operations = total_ops - performed_ops
        remaining_time_est = remaining_operations * time_per_operation

        return remaining_time_est

    def _time_to_str(self, time):
        # Get seconds
        total_seconds = round(time)
        display_seconds = total_seconds % 60
        seconds_str = str(display_seconds) + " seconds" if display_seconds > 0 else ""

        # Get minutes
        total_minutes = total_seconds // 60
        display_minutes = total_minutes % 60
        minutes_str = str(display_minutes) + " minutes " if display_minutes > 0 else ""

        # Get hours
        display_hours = total_minutes // 60
        hours_str = str(display_hours) + " hours " if display_hours > 0 else ""

        # Format string
        time_str = hours_str + minutes_str + seconds_str
        return time_str

    def _update_progress_bar(self, *args):
        super()._update_progress_bar(*args)

        remaining_time = self._calculate_remaining_time()
        if remaining_time:
            self.progress_bar.estimate_text = self._time_to_str(remaining_time)


class DuplicateFinderController(RelativeLayout):
    """
    Abstract Base Class for a Duplicate Image Finder Controller
    """
    layout = ObjectProperty(baseclass=DuplicateFinderLayout)
    duplicate_images = ListProperty([])
    progress = ObjectProperty(DuplicateFinderProgress())

    __events__ = ('on_start', 'on_stop', 'on_cancel', 'on_resume', 'on_finish')

    def __init__(self, **kwargs):
        super(DuplicateFinderController, self).__init__(**kwargs)

        # Member variables
        self.thread = None
        self._state_options = ['rest', 'running', 'stopped', 'canceled', 'finished']
        # rest -> running
        # running -> stopped, canceled, finished
        # stopped -> running, canceled
        # canceled -> running
        # finished -> running
        self._state_transitions = {'rest': {'running': 'on_start'},
                                   'running': {'stopped': 'on_stop', 'canceled': 'on_cancel', 'finished': 'on_finish'},
                                   'stopped': {'running': 'on_resume', 'canceled': 'on_cancel'},
                                   'canceled': {'running': 'on_start'},
                                   'finished': {'running': 'on_start'}
                                   }
        self._state = 'rest'

    # Controls #
    def find(self, image_paths):
        """Starts a thread to find which images from the image path are duplicates

        Args:
            image_paths (list[str]): A list of paths to images

        Raises:
            ValueError: Thrown when the image paths are invalid (not a list of strings)
            RuntimeError: Thrown if the logic tries to find images while the finder is already working
        """
        if not isinstance(image_paths, list) or not all([isinstance(path, str) for path in image_paths]):
            raise ValueError(f"Invalid argument image_paths must be a list of strings but got {image_paths}")
        if self.state == "running" or self.state == "stopped":
            raise RuntimeError(f"Cannot transition from {self.state} to running using find")

        # Set max progress
        self.progress = DuplicateFinderProgress(index=0, total=len(image_paths))

        # Start the duplicate finding thread
        self.duplicate_images = []

        # Shortcut if image_paths is empty
        if not image_paths:
            self.state = 'running'
            self.state = 'finished'
            return

        self.thread = threading.Thread(target=self._find_duplicates, args=(image_paths,))
        self.thread.start()

        # change state
        self.state = 'running'

    def _find_duplicates(self, image_paths, **kwargs):
        """
        Finds all of the duplicate items in the image list and stores them in ``self.duplicate_images``
        in the form of List[List[str]].

        Called internally as a separate thread, should react to and set ``self.state``:
            ``stopped`` -> pause current action and resume when state changes to ``running``

            ``canceled`` -> stop current action and return

            ``finished`` -> set this as the state before returning from the function

        Args:
            image_paths: list of image paths to check for duplicates
            **kwargs:
        """
        raise NotImplementedError

    @mainthread
    def start_stop(self):
        """ Toggles the state between start and stop
        """
        if self.state == 'running':
            self.stop()
        elif self.state == 'stopped':
            self.resume()

    @mainthread
    def stop(self):
        """ Pauses the current thread finding the duplicate images
        """
        # change state
        self.state = 'stopped'

    @mainthread
    def cancel(self):
        """ Cancels the current thread finding the duplicate images should kill the corresponding thread as well
        """
        # change state
        self.state = 'canceled'

    @mainthread
    def resume(self):
        """ Resumes the current thread which was finding duplicate images
        """
        # change state
        self.state = 'running'

    # Getters and Setters #
    def get_state(self):
        return self._state

    def set_state(self, next_state):
        # Ensure next_state is a valid option
        if next_state not in self._state_options:
            raise ValueError(f"Invalid state cannot set state to {next_state}")

        # Change the state by
        #   Performing transition checks
        if next_state not in self._state_transitions[self._state]:
            raise ValueError(f"Invalid transition cannot set state to {next_state} from {self._state}")
        #   Setting the next_state
        old_next_state = self._state
        self._state = next_state
        #   Dispatching the transition event
        self.dispatch(self._state_transitions[old_next_state][next_state])
        #   Dispatch the event for the layout
        if self.layout:
            self.layout.dispatch(self._state_transitions[old_next_state][next_state])

    # Create state member
    state = AliasProperty(get_state, set_state, bind=[])

    # Events #
    @mainthread
    def on_start(self, *args):
        """ Default start handler
        """
        pass

    @mainthread
    def on_stop(self, *args):
        """ Default stop handler
        """
        pass

    @mainthread
    def on_cancel(self, *args):
        """ Default cancel handler
        """
        if self.thread:
            self.thread.join()

    @mainthread
    def on_resume(self, *args):
        """ Default resume handler
        """
        pass

    @mainthread
    def on_finish(self, *args):
        """ Default finish handler
        """
        if self.thread:
            self.thread.join()


class HashDuplicateFinderController(DuplicateFinderController):
    def __init__(self, num_threads=4, **kwargs):
        super().__init__(**kwargs)
        self.hashes = dict()
        self.num_threads = num_threads

    def _find_duplicates(self, image_paths, **kwargs):
        # TODO: Add error handling for improper images or improper paths

        # clear old data
        self.hashes = dict()
        self.progress.total = len(image_paths)

        # Compute hashes
        partial_hash = functools.partial(image_hashing.async_open_and_hash, hash_size=16)
        pool = StoppablePool(fn=partial_hash, args=[(image_path,) for image_path in image_paths],
                             num_workers=self.num_threads)

        for result in pool:
            while self.state == 'stopped':
                # Don't do anything else in the loop while stopped
                continue
            if self.state == 'canceled':
                # stop the pool and exit the loop
                pool.terminate()
                break
            else:
                if result is not None:
                    hash_val, image_path = result
                    # grab all image paths with that hash_val, add the current image
                    # path to it, and store the list back in the hashes dictionary
                    p = self.hashes.get(hash_val, [])
                    p.append(image_path)
                    self.hashes[hash_val] = p

                    # update progress path
                    self.progress.path = image_path

                # update progress index
                self.progress.index += 1

        else:
            # Completed duplicate image search
            # set duplicates
            self.duplicate_images = [images for images in self.hashes.values() if len(images) > 1]
            # set state to finished and call finished event
            self.state = 'finished'


class GradientDuplicateFinderController(DuplicateFinderController):
    def __init__(self, similarity_threshold=.90, num_threads=4, **kwargs):
        super().__init__(**kwargs)
        self.num_threads = num_threads
        self.similarity_threshold = similarity_threshold

    def _compute_gradients(self, image_paths):
        image_gradients = []

        partial_gradient = functools.partial(image_gradient.async_open_and_gradient, vector_size=8)
        pool = StoppablePool(fn=partial_gradient, args=[(image_path,) for image_path in image_paths],
                             num_workers=self.num_threads)

        for result in pool:
            while self.state == 'stopped':
                # Don't do anything else in the loop while stopped
                continue
            if self.state == 'canceled':
                # stop the pool and exit the loop
                pool.terminate()
                return
            else:
                if result is not None:
                    # add gradient to lsit
                    _, image_path = result

                    image_gradients.append(result)

                    # update progress path
                    self.progress.path = "Calculating gradients: " + image_path

                # update progress index
                self.progress.index += 1

        return image_gradients

    def _calculate_similarity(self, image_gradients):
        # update progress path
        self.progress.path = "Calculating similarities..."

        # Create pool of images to compare
        xtable_gradients = []
        for i, (image1_gradient, image1_path) in enumerate(image_gradients):
            for image2_gradient, image2_path in image_gradients[i+1:]:
                xtable_gradients.append((image1_gradient, image1_path, image2_gradient, image2_path))

        # Create a union find data structure
        # Run over all the image pairings (O(n^2))
        # Calculate the % similarity in their image gradients
        # If they have a similarity > some factor
        #   perform union on the two images
        image_index = {image_path: i for i, (_, image_path) in enumerate(image_gradients)}
        union_find = UF(len(image_gradients))
        pool = StoppablePool(fn=image_gradient.async_image_gradient_similarity, args=xtable_gradients, num_workers=self.num_threads)

        for result in pool:
            while self.state == 'stopped':
                # Don't do anything else in the loop while stopped
                continue
            if self.state == 'canceled':
                # stop the pool and exit the loop
                pool.terminate()
                return
            else:
                if result is not None:
                    percentage, image1_path, image2_path = result

                    if percentage > self.similarity_threshold:
                        union_find.union(image_index[image1_path], image_index[image2_path])

                # update progress index
                self.progress.index += 1

        # Create list of duplicates from union_find data structure
        sets_of_images = dict()
        for path, i in image_index.items():
            set_id = union_find.find(i)
            p = sets_of_images.get(set_id, [])
            p.append(path)
            sets_of_images[set_id] = p

        return [images for images in sets_of_images.values() if len(images) > 1]

    def _find_duplicates(self, image_paths, **kwargs):
        # TODO: Add error handling for improper images or improper paths

        # clear old data
        image_count = len(image_paths)
        gradient_operation_count = image_count
        similarity_operation_count = ((image_count-1)**2 + (image_count-1)) / 2
        self.progress.total = similarity_operation_count + gradient_operation_count

        # Compute gradients for all images
        image_gradients = self._compute_gradients(image_paths)

        # Find similarities
        self.duplicate_images = self._calculate_similarity(image_gradients)

        self.state = 'finished'
