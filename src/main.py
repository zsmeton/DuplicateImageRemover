import os
from imutils import paths

from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen

from src.duplicate_finder import DuplicateFinder, HashDuplicateFinder
from src.duplicate_finder_screen import DuplicateFinderScreen


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
    def __init__(self, **kwargs):
        super(MyScreenManager, self).__init__(**kwargs)
        self.add_widget(StartMenuScreen(name='start_menu'))
        self.add_widget(ManageDuplicatesScreen(name='manage_duplicates'))
        self.loading_screen = DuplicateFinderScreen(duplicate_image_finder=HashDuplicateFinder(),
                                                    name='loading_screen')
        self.add_widget(self.loading_screen)

        # Set screen to start menu to start
        self.current = 'start_menu'

    def cancel_search(self):
        self.current = 'start_menu'

    def start_search(self, search_directory):
        print(search_directory)
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
