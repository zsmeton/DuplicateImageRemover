import os
from imutils import paths
import pickle

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen

from src.duplicate_finder import HashDuplicateFinderController, DuplicateFinderProgressLayout, \
    DuplicateFinderEstimatingLayout, GradientDuplicateFinderController
from src.duplicate_finder_screen import DuplicateFinderScreen
from src.duplicate_manager_screen import DuplicateManagerScreen

from kivy.config import Config
from kivy import Logger

Config.set('graphics', 'fullscreen', '0')

TESTING = False
LARGE_IMAGE_TEST = True
LARGE_TEST_IMAGE_FILE = "../tests/large_test_image_paths.pkl"
SMALL_TEST_IMAGE_FILE = "../tests/small_test_image_paths.pkl"
TEST_IMAGE_FILE = LARGE_TEST_IMAGE_FILE if LARGE_IMAGE_TEST else SMALL_TEST_IMAGE_FILE


# TODO: Set custom window title and icon
# TODO: Set custom taskbar icon
# TODO: Figure out how to deploy this as an app
# TODO: Change run mode to not be debug
# TODO: Add integration/unit testing for GUI elements
# TODO: Figure out how to add file, edit, help bar
# TODO: Add logging to various parts of the program
# TODO: use pyler native file chooser 


class Picture(Widget):
    source = StringProperty(None)


class StartMenuScreen(Screen):
    # TODO: Add name of software
    # TODO: Fix file system with touch pad
    # TODO: Make directory selection a pop up
    # TODO: Add way to select multiple paths
    # TODO: Add way to include or not include subdirectories
    # TODO: Add progress bar pop up when finding images in each directory is taking a while
    # TODO: Add method selector
    # TODO: Add configurations for different methods and a view for them
    def filter(self, directory, filename):
        return os.path.isdir(os.path.join(directory, filename))


class MyScreenManager(ScreenManager):
    image_paths = ListProperty()
    duplicate_images = ListProperty()

    def __init__(self, **kwargs):
        super(MyScreenManager, self).__init__(**kwargs)
        self.start_screen = StartMenuScreen(name='start_menu')
        self.loading_screen = DuplicateFinderScreen(duplicate_finder_controller=HashDuplicateFinderController(),
                                                    duplicate_finder_layout=DuplicateFinderEstimatingLayout(),
                                                    name='loading_screen')
        self.manage_duplicates = DuplicateManagerScreen(name='manage_duplicates')

        self.add_widget(self.start_screen)
        self.add_widget(self.loading_screen)
        self.add_widget(self.manage_duplicates)

        # Set screen to start menu to start
        if TESTING:
            with open(TEST_IMAGE_FILE, "rb") as fin:
                test_dup_images = pickle.load(fin)

            self.search_finished(test_dup_images)
        else:
            self.current = 'start_menu'

    def cancel_search(self):
        self.current = 'start_menu'

    def start_search(self, search_directory):
        Logger.info(f"Searching {search_directory} for images")
        # TODO: Add error handling
        self.image_paths = list(paths.list_images(search_directory))
        self.current = 'loading_screen'
        self.loading_screen.start_search(self.image_paths)

    def search_finished(self, duplicate_images):
        num_duplicates = sum([len(elem) for elem in duplicate_images])
        Logger.info(f"Found {num_duplicates} duplicate images")

        if not TESTING and num_duplicates > 0:
            Logger.debug(f"Saving duplicate images to {TEST_IMAGE_FILE}")
            with open(TEST_IMAGE_FILE, "wb") as fout:
                pickle.dump(list(duplicate_images), fout)

        self.duplicate_images = duplicate_images
        # TODO: Add error handling
        self.manage_duplicates.duplicate_images = self.duplicate_images
        self.current = 'manage_duplicates'


class DuplicateImageApp(App):
    def build(self):
        return MyScreenManager()


if __name__ == '__main__':
    DuplicateImageApp().run()
