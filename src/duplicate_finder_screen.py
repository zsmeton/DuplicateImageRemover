from kivy.properties import ObjectProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.progressbar import ProgressBar

from src.duplicate_finder import FindDuplicateDispatcher, HashFindDuplicateDispatcher


# TODO: Change logic so that screen changes occur via events (using kv file instead of hard coded)
# dynamic loading of widgets https://stackoverflow.com/questions/38649664/can-the-kivy-language-access-inherited-layouts-and-widgets

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

    def search_finished(self, instance):
        self.manager.search_finished(instance.duplicate_images)
