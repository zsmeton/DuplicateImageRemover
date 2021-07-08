from weakref import ref

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen
from kivy.event import EventDispatcher
from kivy.clock import Clock

from kivy.config import Config

Config.set('graphics', 'fullscreen', '0')

Builder.load_string('''
<ProgressingWidget>:
    BoxLayout:
        ProgressBar:
            id: _progress
            max: 10
            value: 0
        Button:
            id: _button
            text: "++"
            on_release: root.controller.push()
''')


class DuplicateFinderProgress(EventDispatcher):
    """
    Stores the DuplicateFinderControllers current progress on finding duplicates
    """
    path = StringProperty("")  # Last path processed
    index = NumericProperty(0)  # Current index in list of image paths processed
    total = NumericProperty(0)  # Number of images to check


class MainView(RelativeLayout):
    progress = ObjectProperty(DuplicateFinderProgress())

    def push(self):
        self.progress.total = 100
        self.progress.index = (self.progress.index + 1) % 100
        print(self.progress.index)


class ProgressingWidget(FloatLayout):
    controller = ObjectProperty(baseclass=MainView)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_progress_ev = Clock.schedule_interval(self._update_progress, .1)

    def _update_progress(self, *args):
        if self.controller:
            self.ids._progress.max = self.controller.progress.total
            self.ids._progress.value = self.controller.progress.index


class MyScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.main = MainView()
        self.progressing = ProgressingWidget()
        self.progressing.controller = self.main
        self.main.add_widget(self.progressing)
        self.add_widget(self.main)


class TestApp(App):
    def build(self):
        return MyScreen()


if __name__ == '__main__':
    TestApp().run()
