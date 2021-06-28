import threading
from multiprocessing import Pool
import platform
import functools

from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, ListProperty, AliasProperty
from kivy.event import EventDispatcher
from kivy.clock import mainthread
from src import image_hashing
from src.progress import Progress


# TODO: Make a widget which is the loading bar, pause/play, and cancel button which contains a DuplicateDispatcher
# TODO: Add in pause and resume buttons
class FindDuplicateDispatcher(Widget, EventDispatcher):
    """
    Abstract Base Class for a Duplicate Image Finder
    """
    duplicate_images = ListProperty([])
    progress = ObjectProperty(baseclass=Progress)

    def __init__(self, **kwargs):
        self.register_event_type('on_start')
        self.register_event_type('on_stop')
        self.register_event_type('on_cancel')
        self.register_event_type('on_finish')
        self.register_event_type('on_resume')
        super(FindDuplicateDispatcher, self).__init__(**kwargs)

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
        self.progress = Progress(current=0, max_amount=len(image_paths))

        # Start the duplicate finding thread
        self.duplicate_images = []
        self.thread = threading.Thread(target=self.__find_duplicates__, args=(image_paths,))
        self.thread.daemon = True
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


class HashFindDuplicateDispatcher(FindDuplicateDispatcher):
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
                self.progress = Progress(current=self.progress.current + 1, max_amount=self.progress.max)
        else:
            pool.join()
            # Completed duplicate image search
            # set duplicates
            self.duplicate_images = [images for images in self.hashes.values() if len(images) > 1]
            # set state to finished and call finished event
            self.state = 'finished'
