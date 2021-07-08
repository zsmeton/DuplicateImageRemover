from kivy.uix.screenmanager import Screen

from src.duplicate_finder import DuplicateFinderController, DuplicateFinderLayout


# TODO: Refactor so that this doesn't have a start search which is called by screen manager use screen transitions \
#  and a string property as well remove other bindings and instead set them in the kivy language
class DuplicateFinderScreen(Screen):
    def __init__(self, duplicate_finder_controller: DuplicateFinderController,
                 duplicate_finder_layout: DuplicateFinderLayout, **kwargs):
        super(DuplicateFinderScreen, self).__init__(**kwargs)
        self.controller = duplicate_finder_controller
        self.layout = duplicate_finder_layout
        # Bind controller and layout
        self.controller.layout = self.layout
        self.layout.controller = self.controller
        self.controller.add_widget(self.layout)
        # Bind events for controller
        self.controller.bind(on_finish=self.search_finished)
        self.controller.bind(on_cancel=self.search_canceled)
        self.add_widget(self.controller)

    def start_search(self, images):
        self.controller.find(images)

    def search_canceled(self, *args):
        self.manager.cancel_search()

    def search_finished(self, instance, *args):
        self.manager.search_finished(instance.duplicate_images)
