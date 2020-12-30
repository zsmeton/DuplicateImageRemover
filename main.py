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
from kivy.properties import StringProperty, ObjectProperty, ListProperty, BooleanProperty, BoundedNumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.progressbar import ProgressBar
from kivy.event import EventDispatcher
from kivy.clock import Clock

import image_hashing

class ThreadInProgressError(Exception):
    pass


class DuplicateFinderScreen(Screen):
    # TODO: Add loading bar message 
    # TODO: (files finished, files to go, predicted time to finish)
    progress_bar = ObjectProperty()
    
    def __init__(self, **kwargs):
        super(DuplicateFinderScreen, self).__init__(**kwargs)
        self.progress_bar = ProgressBar()
        self.add_widget(self.progress_bar)
    
    def set_max_progress(self, val):
        # TODO: add error handling for val
        self.progress_bar.max = val

    def increment_progress(self, val=1):
        self.progress_bar.value += val

class FindDuplicateDispatcher(Widget):
    """
    Abstract Base Class for a Duplicate Image Finder
    """
    duplicateImages = ListProperty([])
    progress = BoundedNumericProperty(0,min=0,max=100)
    running = BooleanProperty(False)
    finished = BooleanProperty(False)
    cancel = BooleanProperty(False)
    
    def __init__(self, **kwargs):
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
            raise ValueError(f"image_paths must be a list of strings but got {image_paths}")
        if self.running:
            raise RuntimeError("Cannot start a duplicate image search while a search is in progress")
        
        # Set running tokens
        self.finished =  False
        self.running = True
        self.cancel = False

        # Set max progress
        self.progress = 1
        #self.property('progress').set_max(self, len(image_paths))
        
        
        # Start the duplicate finding thread
        self.duplicateImages = []
        self.thread = threading.Thread(target=self.__find_duplicates__, args=(image_paths,))
        self.thread.start()
        

    def __find_duplicates__(self, image_paths, **kwargs):
        """Finds all of the duplicate items in the image list and stores them in duplicate
        Called internally as a seperate thread
        """
        raise NotImplementedError
    
    def stop(self):
        self.cancel = True
    
    def on_cancel(self, instance, pos):
        """ Performs operations to halt __find_duplicates__ in its tracks """
        raise NotImplementedError


class HashFindDuplicateDispatcher(FindDuplicateDispatcher):
    def __init__(self, num_threads=4, **kwargs):
        super().__init__(**kwargs)
        self.hashes = dict()
        self.num_threads = num_threads
        self.cancel_shared = Value(c_bool,self.cancel)
    
    def __find_duplicates__(self, image_paths, **kwargs):
        """Returns a list where each entry is a list of duplicate image paths

        Raises:
            ThreadInProgressError: Cannot get duplicates while running

        Returns:
            list[list[str]]: list of duplicates
        """
        # TODO: Add error handling to improper images or improper paths
        # Compute hashes
        with Pool(processes=self.num_threads) as pool:
            multiple_results = [pool.apply_async(image_hashing.async_open_and_hash, (image_path, 16))
                                for image_path in image_paths]
            for res in multiple_results:
                print("hey")
                # Check cancelation token
                if self.cancel_shared:
                    break
                
                # Get results and perform hash
                result = res.get()
                if result is not None:
                    hash_val,image_path = result
                    # grab all image paths with that hash_val, add the current image
                    # path to it, and store the list back in the hashes dictionary
                    p = self.hashes.get(hash_val, [])
                    p.append(image_path)
                    self.hashes[hash_val] = p

                # update progress
                self.progress = self.progress + 1
                print("yo")
            
            else:
                # Completed duplicate image search
                # set duplicates
                self.duplicateImages = [images for images in self.hashes.values() if len(images) > 1]
                
        # set running and finished
        self.finished = True
        self.running = False
    
    def on_cancel(self, instance, pos):
        """ Performs operations to halt __find_duplicates__ in its tracks """
        print("on_cancel")
        with self.cancel_shared.get_lock():
            self.cancel_shared = self.cancel
    
    def on_progress(self, instance, pos):
        print("YO HO IN ON_PROGYBOI")



class DuplicateFinder(Widget):
    def __init__(self, image_paths=None, screen_name='duplicate_search_screen', **kwargs):
        # TODO: Add error handling for image paths
        super().__init__(**kwargs)
        self.screen = DuplicateFinderScreen(name=screen_name)
        self.image_paths = image_paths
        self.thread = None
        self.duplicates = []
        
    def set_image_paths(self, image_paths):
        """Sets the paths for the images the duplicate finder will search

        Args:
            image_paths ([type]): [description]

        Raises:
            ThreadInProgressError: Cannot change the image paths when duplicate finder is running
            ValueError: Must set image paths to a list of strings
        """
        # TODO: add error handling for image paths
        if self.is_running():
            raise ThreadInProgressError("Cannot set image path while duplicate finder \
                is searching for images.")

        self.image_paths = image_paths

    def start(self):
        """Starts the threaded process of finding duplicate images

        Raises:
            ThreadInProgressError: Cannot start while running
        """
        if self.is_running():
            raise ThreadInProgressError("Cannot set image path while duplicate finder \
                is searching for images. ")
        # Set max progress
        self.screen.set_max_progress(len(self.image_paths))
        # Start the duplicate finding thread
        self.duplicates = []
        self.thread = threading.Thread(target=self.find_duplicates)
        self.thread.start()
    
    def kill(self):
        # TODO: FInd way to kill the find duplicate process and anything spawned from it
        raise NotImplementedError

    def is_running(self):
        """Returns true if the duplicate finder is currently running find_duplicates

        Returns:
            bool:
        """
        return self.thread is not None and self.thread.is_alive()

    def find_duplicates(self, **kwargs):
        """Finds all of the duplicate items in the image list and stores them in duplicate
        Usually called internally as a seperate thread
        """
        raise NotImplementedError
    
    def get_duplicates(self):
        """Returns a list where each entry is a list of duplicate image paths

        Raises:
            ThreadInProgressError: Cannot get duplicates while running

        Returns:
            list[list[str]]: list of duplicates
        """
        if self.is_running():
            raise ThreadInProgressError("Cannot set image path while duplicate finder \
                is searching for images.")
        return self.duplicates


class HashDuplicateFinder(DuplicateFinder):
    def __init__(self, num_threads=4, **kwargs):
        super().__init__(**kwargs)
        self.hashes = dict()
        self.num_threads = num_threads
    
    def find_duplicates(self, **kwargs):
        """Returns a list where each entry is a list of duplicate image paths

        Raises:
            ThreadInProgressError: Cannot get duplicates while running

        Returns:
            list[list[str]]: list of duplicates
        """
        # TODO: Add error handling to improper images or improper paths
        # Compute hashes
        with Pool(processes=self.num_threads) as pool:
            multiple_results = [pool.apply_async(image_hashing.async_open_and_hash, (image_path, 16))
                                for image_path in self.image_paths]
            for res in multiple_results:
                print("yup")
                result = res.get()
                if result is not None:
                    hash_val,image_path = result
                    # grab all image paths with that hash_val, add the current image
                    # path to it, and store the list back in the hashes dictionary
                    p = self.hashes.get(hash_val, [])
                    p.append(image_path)
                    self.hashes[hash_val] = p

                # update screen
                self.screen.increment_progress()
        
        # Find duplicates
        self.duplicates = [images for images in self.hashes.values() if len(images) > 1]


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
        #self.search_directory = "/home/zsmeton/Dropbox/Images/google_dup/"
        self.add_widget(StartMenuScreen(name='start_menu'))
        self.add_widget(ManageDuplicatesScreen(name='manage_duplicates'))
        self.duplicate_finder = None
        self.duplicates = None
        
        # Set screen to start menu to start
        self.current = 'start_menu'
    
    def find_duplicates(self, search_directory):
        # TODO: Add error handling
        image_paths = list(paths.list_images(search_directory))
        if self.duplicate_finder is None:
            self.duplicate_finder = HashDuplicateFinder(image_paths=image_paths, screen_name='loading_screen')
            self.add_widget(self.duplicate_finder.screen)
        else:
            self.duplicate_finder.set_image_paths(image_paths)
        self.current = 'loading_screen'
        self.duplicate_finder.start()
        Clock.schedule_once(self.check_if_duplicates_have_been_found)
    
    def check_if_duplicates_have_been_found(self, dt):
        if not self.duplicate_finder.is_running():
            self.duplicates = self.duplicate_finder.get_duplicates()
            self.current = 'manage_duplicates'
        else:
            Clock.schedule_once(self.check_if_duplicates_have_been_found)


class DuplicateImageApp(App):
    def build(self):
        return MyScreenManager()

def print_progress(instance, pos):
    print(instance.progress)

def print_finished(instance, pos):
    print(instance)

if __name__ == '__main__':
    DuplicateImageApp().run()

    #duplicateFinder = HashFindDuplicateDispatcher()
    #duplicateFinder.bind(progress=print_progress)

    #duplicateFinder.find(list(paths.list_images("~/Dropbox/Images")))

    #time.sleep(5)

    #duplicateFinder.stop()
    #print("Yup")

    #time.sleep(1)

    #duplicateFinder.find(list(paths.list_images("~/Dropbox/Images")))

    #time.sleep(5)

    #duplicateFinder.stop()
    #print("Yup")

