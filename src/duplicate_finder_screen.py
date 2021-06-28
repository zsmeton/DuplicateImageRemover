from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.progressbar import ProgressBar
from kivy.uix.boxlayout import BoxLayout

from src.duplicate_finder import DuplicateFinder, HashDuplicateFinder


class DuplicateFinderScreen(Screen):
    def __init__(self, duplicate_image_finder: DuplicateFinder, **kwargs):
        super(DuplicateFinderScreen, self).__init__(**kwargs)
        self.duplicate_image_finder = duplicate_image_finder
        self.duplicate_image_finder.bind(on_finish=self.search_finished)
        self.duplicate_image_finder.bind(on_cancel=self.search_canceled)
        self.add_widget(self.duplicate_image_finder)

    def start_search(self, images):
        self.duplicate_image_finder.find(images)

    def search_canceled(self, *args):
        self.manager.cancel_search()

    def search_finished(self, instance, *args):
        self.manager.search_finished(instance.duplicate_images)
