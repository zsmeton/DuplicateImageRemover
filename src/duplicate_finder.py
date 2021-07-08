import threading
from multiprocessing import Pool
import platform
import functools

from kivy.properties import ObjectProperty, ListProperty, AliasProperty, StringProperty, NumericProperty
from kivy.event import EventDispatcher
from kivy.clock import mainthread
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock
from src import image_hashing

# Features
# TODO: Add widget which shows estimate and done/current
# TODO: Add back button

class DuplicateFinderLayout(FloatLayout):
    controller = ObjectProperty()
    __events__ = ('on_start', 'on_stop', 'on_cancel', 'on_resume', 'on_finish')

    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_cancel(self):
        pass

    def on_resume(self):
        pass

    def on_finish(self):
        pass


class DuplicateFinderStoppableLayout(DuplicateFinderLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_progress_bar_ev = None

    def on_start(self):
        self._start_update_progress_bar()

    def on_resume(self):
        self._start_update_progress_bar()

    def on_stop(self):
        self._stop_update_progress_bar()

    def on_cancel(self):
        self._stop_update_progress_bar()

    def on_finish(self):
        self._stop_update_progress_bar()

    def _stop_update_progress_bar(self):
        """
        Cancels the event scheduled to update the progress bar if it exists

        Returns:
        """
        ev = self._update_progress_bar_ev

        if ev is not None:
            ev.cancel()

    def _start_update_progress_bar(self):
        """
        Creates a scheduled event to update the progress bar if one doesn't already exist

        Returns:
        """
        ev = self._update_progress_bar_ev

        if ev is None:
            ev = self._update_progress_bar_ev = Clock.schedule_interval(self._update_progress_bar, .1)
        ev()

    def _update_progress_bar(self, *args):
        """
        Updates the progress bar value to the controllers progress
        Returns:
        """
        if self.controller:
            self.ids.progress_bar.max = self.controller.progress.total
            self.ids.progress_bar.value = self.controller.progress.index


class DuplicateFinderProgress(EventDispatcher):
    """
    Stores the DuplicateFinderControllers current progress on finding duplicates
    """
    path = StringProperty("")  # Last path processed
    index = NumericProperty(0)  # Current index in list of image paths processed
    total = NumericProperty(0)  # Number of images to check


class DuplicateFinderController(RelativeLayout):
    """
    Abstract Base Class for a Duplicate Image Finder
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

        # Set max progress and pause play button
        new_progress = DuplicateFinderProgress(index=0, total=len(image_paths))
        self.progress = new_progress

        # Start the duplicate finding thread
        self.duplicate_images = []

        # Shortcut if image_paths is empty
        if not image_paths:
            self.state = 'running'
            self.state = 'finished'
            return

        self.thread = threading.Thread(target=self.__find_duplicates__, args=(image_paths,))
        self.thread.start()

        # change state
        self.state = 'running'

    def __find_duplicates__(self, image_paths, **kwargs):
        """Finds all of the duplicate items in the image list and stores them in duplicate
        Called internally as a seperate thread, should set state to finished and dispatch on_finished event
        when complete
        """
        raise NotImplementedError

    @mainthread
    def start_stop(self):
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
        """
        Cancels the current thread finding the duplicate images should kill the corresponding thread as well
        """
        # change state
        self.state = 'canceled'

    @mainthread
    def resume(self):
        """Resumes the current thread which was finding duplicate images
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
        """ Default start handler """
        pass

    @mainthread
    def on_stop(self, *args):
        """ Default stop handler """
        pass

    @mainthread
    def on_cancel(self, *args):
        """ Default cancel handler """
        if self.thread and platform.system() == 'Windows':
            self.thread.join()

    @mainthread
    def on_resume(self, *args):
        """ Default resume handler """
        pass

    @mainthread
    def on_finish(self, *args):
        """ Default finish handler
        """
        if self.thread and platform.system() == 'Windows':
            self.thread.join()


class HashDuplicateFinderController(DuplicateFinderController):
    def __init__(self, num_threads=4, **kwargs):
        super().__init__(**kwargs)
        self.hashes = dict()
        self.num_threads = num_threads

    def __find_duplicates__(self, image_paths, **kwargs):
        """Returns a list where each entry is a list of duplicate image paths

        Raises:
            ThreadInProgressError: Cannot get duplicates while running

        Returns:
            list[list[str]]: list of duplicates
        """
        # TODO: Add error handling to improper images or improper paths

        # clear old data
        self.hashes = dict()

        # Compute hashes
        pool = Pool(processes=self.num_threads)
        partial_hash = functools.partial(image_hashing.async_open_and_hash, hash_size=16)
        results = pool.imap_unordered(partial_hash, image_paths)
        pool.close()

        for result in results:
            while self.state == 'stopped':
                continue
            if self.state == 'canceled':
                # stop the pool and exit the loop
                pool.terminate()
                if platform.system() == 'Windows':
                    pool.join()
                break
            else:
                if result is not None:
                    hash_val, image_path = result
                    # grab all image paths with that hash_val, add the current image
                    # path to it, and store the list back in the hashes dictionary
                    p = self.hashes.get(hash_val, [])
                    p.append(image_path)
                    self.hashes[hash_val] = p

                # update progress
                new_progress = DuplicateFinderProgress(index=self.progress.index + 1, total=len(image_paths))
                self.progress = new_progress
        else:
            pool.join()
            # Completed duplicate image search
            # set duplicates
            self.duplicate_images = [images for images in self.hashes.values() if len(images) > 1]
            # set state to finished and call finished event
            self.state = 'finished'
