import os
from imutils import paths

from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ObjectProperty, ListProperty, AliasProperty
from kivy.uix.screenmanager import ScreenManager, Screen

from src.duplicate_finder import FindDuplicateDispatcher, HashFindDuplicateDispatcher
from src.duplicate_finder_screen import DuplicateFinderScreen

# TODO: Make FindDuplicateDispatcher a widget with progress bar and buttons which DuplicateFinderScreen contains


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
