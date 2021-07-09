import os
from imutils import paths

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen

from src.duplicate_finder import HashDuplicateFinderController, DuplicateFinderProgressLayout
from src.duplicate_finder_screen import DuplicateFinderScreen
from src.duplicate_manager_screen import DuplicateManagerScreen

from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')


class Picture(Widget):
    source = StringProperty(None)


class StartMenuScreen(Screen):
    # TODO: Fix the buttons add name of software
    # TODO: Fix file system with touch pad
    # TODO: Make directory selection a pop up
    # TODO: Add way to select multiple paths
    # TODO: Add way to include or not include subdirectories
    # TODO: Add progress bar pop up when finding images in each directory is taking a while
    # TODO: Add method selector
    def filter(self, directory, filename):
        return os.path.isdir(os.path.join(directory, filename))


class MyScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super(MyScreenManager, self).__init__(**kwargs)
        self.add_widget(StartMenuScreen(name='start_menu'))
        self.add_widget(DuplicateManagerScreen(name='manage_duplicates'))
        self.loading_screen = DuplicateFinderScreen(duplicate_finder_controller=HashDuplicateFinderController(),
                                                    duplicate_finder_layout=DuplicateFinderProgressLayout(),
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
