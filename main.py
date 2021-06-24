import threading
import time
from multiprocessing import Pool, Value
from ctypes import c_bool
import os

from imutils import paths
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.logger import Logger
from kivy.uix.scatter import Scatter
from kivy.properties import StringProperty, ObjectProperty, ListProperty, BooleanProperty, BoundedNumericProperty, \
    OptionProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.progressbar import ProgressBar
from kivy.event import EventDispatcher
from kivy.clock import Clock

import image_hashing


# TODO: Fix logic so that we use changes to properties to change screens from duplicate image finder (maybe do some doodling)
# TODO: Using properties like running, finished, found_duplicates, canceled

# TODO: Change logic so that screen changes occur via events

# TODO: Make a widget which is the loading bar, pause/play, and cancel button which is also a child of DuplicateDispatcher

# TODO: Add in pause and resume buttons

class Progress:
    def __init__(self, current=0, max_amount=100):
        self._current = 0
        self._max = 100
        # Set max before current to avoid current getting set out of bounds before max is increased
        self.max = max_amount
        self.current = current

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, max):
        # TODO: add type check
        # Error checks
        if max < 0:
            raise ValueError(f"Cannot set max to less than 0 {max}")
        if self.current > max:
            raise ValueError(f"Cannot set max {max} to less than current {self.current}")
        # Set it
        self._max = max

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, current):
        # TODO: add type check
        if self.max >= current >= 0:
            self._current = current
        else:
            raise ValueError(f"Cannot set current value greater than max {self.max} or less than 0")


# TODO: Change logic so that the state is set by the events
class FindDuplicateDispatcher(Widget, EventDispatcher):
    """
    Abstract Base Class for a Duplicate Image Finder
    """
    duplicate_images = ListProperty([])
    progress = ObjectProperty(baseclass=Progress)
    state = OptionProperty('rest', options=['rest', 'running', 'stopped', 'canceled', 'finished'])

    def __init__(self, **kwargs):
        self.register_event_type('on_start')
        self.register_event_type('on_stop')
        self.register_event_type('on_cancel')
        self.register_event_type('on_finish')
        super(FindDuplicateDispatcher, self).__init__(**kwargs)

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
        self.thread.start()

        # change state and dispatch events
        self.state = 'running'
        self.dispatch('on_start', image_paths)

    def __find_duplicates__(self, image_paths, **kwargs):
        """Finds all of the duplicate items in the image list and stores them in duplicate
        Called internally as a seperate thread, should set state to finished and dispatch on_finished event
        when complete
        """
        raise NotImplementedError

    def stop(self):
        """ Pauses the current thread finding the duplicate images
        """
        # Check for valid transition
        if self.state != 'running':
            raise RuntimeError(f"Cannot transition from {self.state} to stopped")

        # change state and dispatch events
        self.state = 'stopped'
        self.dispatch('on_stop')

    def cancel(self):
        """Cancels the current thread finding the duplicate images should kill the corresponding thread as well
        """
        # Check for valid transition
        if self.state != 'running' and self.state != 'stopped':
            raise RuntimeError(f"Cannot transition from {self.state} to canceled")

        # change state, stop the thread, and dispatch events
        self.state = 'canceled'
        self.dispatch('on_cancel')

    def resume(self):
        """Resumes the current thread which was finding duplicate images
        """
        # Check for valid transition
        if self.state != 'stopped':
            raise RuntimeError(f"Cannot transition from {self.state} to running using resume")

        # change state and dispatch events
        self.state = 'running'
        self.dispatch('on_resume')

    # TODO: Look into if default handlers are always called
    # TODO: Add transition checking to default event handlers

    def on_start(self, *args):
        """ Default start handler """
        self.state = 'running'

    def on_stop(self, *args):
        """ Default stop handler """
        self.state = 'stopped'

    def on_cancel(self, *args):
        """ Default cancel handler """
        self.state = 'canceled'
        #self.thread.join()

    def on_resume(self, *args):
        """ Default resume handler """
        self.state = 'running'

    def on_finish(self, *args):
        """ Default finish handler
        """
        self.state = 'finished'
        #self.thread.join()


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
        multiple_results = [pool.apply_async(image_hashing.async_open_and_hash, (image_path, 16))
                            for image_path in image_paths]

        # Get iterator to pool
        result_iter = iter(multiple_results)
        # Grab results unless stopped or canceled
        while True:
            if self.state == 'stopped':
                continue
            elif self.state == 'canceled':

                # stop the pool and exit the loop
                pool.terminate()
                break
            else:
                try:
                    # Get results and perform hash
                    result = next(result_iter).get()

                    if result is not None:
                        hash_val, image_path = result
                        # grab all image paths with that hash_val, add the current image
                        # path to it, and store the list back in the hashes dictionary
                        p = self.hashes.get(hash_val, [])
                        p.append(image_path)
                        self.hashes[hash_val] = p

                    # update progress
                    self.progress = Progress(current=self.progress.current + 1, max_amount=self.progress.max)
                except StopIteration:
                    # Completed duplicate image search
                    # set duplicates
                    self.duplicate_images = [images for images in self.hashes.values() if len(images) > 1]
                    # set state to finished and call finished event
                    self.state = 'finished'
                    self.dispatch('on_finish', self.duplicate_images)
                    # stop the pool and exit the loop
                    pool.close()
                    pool.join()
                    return


class DuplicateFinderScreen(Screen):
    # TODO: Add loading bar message 
    # TODO: (files finished, files to go, predicted time to finish)
    progress_bar = ObjectProperty()

    def __init__(self, duplicate_image_finder: FindDuplicateDispatcher, **kwargs):
        super(DuplicateFinderScreen, self).__init__(**kwargs)
        self.progress_bar = ProgressBar()
        self.add_widget(self.progress_bar)
        self.duplicate_image_finder = duplicate_image_finder
        self.duplicate_image_finder.bind(progress=self.on_progress)
        self.duplicate_image_finder.bind(on_finish=self.search_finished)
        self.add_widget(self.duplicate_image_finder)

    def on_progress(self, instance, *args):
        # TODO: add error handling for val
        self.progress_bar.max = instance.progress.max
        self.progress_bar.value = instance.progress.current

    def start_search(self, images):
        self.duplicate_image_finder.find(images)

    def stop_search(self):
        self.duplicate_image_finder.stop()

    def cancel_search(self):
        self.duplicate_image_finder.cancel()

    def resume_search(self):
        self.duplicate_image_finder.resume()

    def search_finished(self, instance, duplicate_images):
        self.manager.search_finished(duplicate_images)


class Picture(Widget):
    source = StringProperty(None)


class StartMenuScreen(Screen):
    # TODO: Fix the buttons add name of software
    # TODO: Fix file system with touch pad
    # TODO: add method selector
    def filter(self, directory, filename):
        return os.path.isdir(os.path.join(directory, filename))


class ManageDuplicatesScreen(Screen):
    # TODO: Implement the duplicate image selector
    pass


class MyScreenManager(ScreenManager):
    # TODO: Add config for how long between checking find duplicates
    # TODO: Add config for screen names
    def __init__(self, **kwargs):
        super(MyScreenManager, self).__init__(**kwargs)
        # self.search_directory = "/home/zsmeton/Dropbox/Images/google_dup/"
        self.add_widget(StartMenuScreen(name='start_menu'))
        self.add_widget(ManageDuplicatesScreen(name='manage_duplicates'))
        self.loading_screen = DuplicateFinderScreen(duplicate_image_finder=HashFindDuplicateDispatcher(),
                                                    name='loading_screen')
        self.add_widget(self.loading_screen)
        self.duplicates = None

        # Set screen to start menu to start
        self.current = 'start_menu'

    def cancel_search(self):
        self.loading_screen.cancel_search()
        self.current = 'start_menu'

    def start_search(self, search_directory):
        # TODO: Add error handling
        image_paths = list(paths.list_images(search_directory))
        self.current = 'loading_screen'
        self.loading_screen.start_search(image_paths)

    def search_finished(self, duplicate_images):
        print(duplicate_images)
        # TODO: Add error handling
        self.current = 'manage_duplicates'


class DuplicateImageApp(App):
    def build(self):
        return MyScreenManager()


if __name__ == '__main__':
    DuplicateImageApp().run()

    # duplicateFinder = HashFindDuplicateDispatcher()
    # duplicateFinder.bind(progress=print_progress)

    # duplicateFinder.find(list(paths.list_images("~/Dropbox/Images")))

    # time.sleep(5)

    # duplicateFinder.stop()
    # print("Yup")

    # time.sleep(1)

    # duplicateFinder.find(list(paths.list_images("~/Dropbox/Images")))

    # time.sleep(5)

    # duplicateFinder.stop()
    # print("Yup")
