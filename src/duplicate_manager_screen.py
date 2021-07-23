from kivy.properties import ListProperty
from kivy.uix.screenmanager import Screen
from src.duplicate_manager import ImageGroupsRecycleView


class DuplicateManagerScreen(Screen):
    duplicate_images = ListProperty()


if __name__ == "__main__":
    from kivy.lang import Builder
    from kivy.app import App
    import textwrap
    from kivy.config import Config

    Config.set('graphics', 'fullscreen', '0')

    root = Builder.load_string(textwrap.dedent('''\
        <SelectableImage>:
            size_hint: None, None
            height: 200
            width: image.image_ratio*root.height
            on_selected: check.active = root.selected
            AsyncImage:
                id: image
                source: root.source
            CheckBox:
                color: [1,1,1,1]
                background_checkbox_down: 'atlas://data/images/defaulttheme/checkbox_radio_on'
                background_checkbox_normal: 'atlas://data/images/defaulttheme/checkbox_radio_off'
                pos_hint: {'x': 0.05, 'y': 0.9}
                size_hint: None, None
                size: 10, 10
                id: check

        <ImageGroupDataView>:
            default_size: None, None
            size_hint: 1, None
            height: self.minimum_height
            widgetclass: 'SelectableImage'
            padding: 20
            multiselect: True
            touch_multiselect: True

        <ImageGroupsRecycleView>:
            viewclass: 'ImageGroupDataView'
            ImageGroupsLayout:
                default_size: None, None
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                multiselect: True
                touch_multiselect: True


        <DuplicateManagerScreen>:
            BoxLayout:
                orientation: 'vertical'
                ImageGroupsRecycleView:
                    id: _recycle_view
                Button:
                    size_hint_y: 0.05
                    text: 'Delete'
                    on_release: _recycle_view.remove_selected()
        '''))


    class DuplicateManagerApp(App):

        def build(self):
            return DuplicateManagerScreen()


    DuplicateManagerApp().run()