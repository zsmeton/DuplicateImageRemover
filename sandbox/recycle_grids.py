from kivy.app import App
from kivy.lang import Builder
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors.compoundselection import CompoundSelectionBehavior
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.properties import ObjectProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.factory import Factory

from kivy.config import Config

Config.set('graphics', 'fullscreen', '0')

Builder.load_string('''
<SelectableLabel>:
    # Draw a background to indicate selection
    canvas.before:
        Color:
            rgba: (.0, 0.9, .1, .3) if self.selected else (0, 0, 0, 1)
        Rectangle:
            pos: self.pos
            size: self.size

<GridDataView>:
    widgetclass: 'SelectableLabel'
    padding: 20
    cols: 2
    multiselect: True
    touch_multiselect: True

<RV>:
    viewclass: 'GridDataView'
    SelectableRecycleBoxLayout:
        default_size: None, None
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'
        multiselect: True
        touch_multiselect: True

<MyScreen>:
    BoxLayout:
        orientation: 'vertical'
        RV:
            id: _recycle_view
        Button:
            text: 'Delete'
            on_release: _recycle_view.remove_selected()

''')

# TODO: Add deletion behavior
class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class GridDataView(CompoundSelectionBehavior, RecycleDataViewBehavior, GridLayout):
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)
    widgetclass = StringProperty('None')
    widgets = ListProperty([])

    def __init__(self, **kwargs):
        super(GridDataView, self).__init__(**kwargs)
        self.index = None

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        # Set index
        self.index = index
        # Remove old widgets
        self.clear_widgets()
        self.widgets = []
        # Add new widgets
        widget_type = Factory.get(self.widgetclass)
        for i, kwargs in enumerate(data['data']):
            new_widget = widget_type(index=i, **kwargs)
            self.add_widget(new_widget)
            self.widgets.append(new_widget)

        return super(GridDataView, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(GridDataView, self).on_touch_down(touch):
            return True

    def select_with_touch(self, index, touch=None):
        ''' Add selection on touch down '''
        # TODO: Figure out what this code below is doing
        print('select_with_touch', self.index, index, self.selected_nodes)
        # toggle selection of the child
        if not self.select_node(index):
            self.deselect_node(index)

        # handle my own selection
        if self.selectable:
            # Case 1: currently not selected and should be
            if not self.selected and self.selected_nodes:
                return self.parent.select_with_touch(self.index, touch)
            # Case 2: currently selected and shouldn't be
            elif self.selected and not self.selected_nodes:
                return self.parent.select_with_touch(self.index, touch)

    def select_node(self, node):
        result = super(GridDataView, self).select_node(node)
        self.widgets[node].apply_selection(node, result)
        return result

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected

class SelectableLabel(Label):
    ''' Add selection support to the Label '''
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def __init__(self, index, **kwargs):
        super(SelectableLabel, self).__init__(**kwargs)
        self.index = index

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected


class RV(RecycleView):
    def __init__(self, **kwargs):
        super(RV, self).__init__(**kwargs)
        self.data = [{'data': [{'text': str(i)} for i in range(5)]} for x in range(100)]

    def remove_selected(self):
        # Get the selected nodes
        selected = set(self.layout_manager.selected_nodes)
        print(selected)
        # For each node
        #for select in selected:
        #    if issubclass(select, CompoundSelectionBehavior):
        #        # perform remove on selected nodes
        #        self.data[select]
        # Get a list without the selected nodes
        #new_data = [val for i, val in enumerate(self.data) if i not in selected]
        # Deselect the nodes in the manager
        #for idx in selected:
        #    self.layout_manager.deselect_node(idx)
        # Set data to only include none selected nodes
        #self.data = new_data


class MyScreen(Screen):
    pass


class TestApp(App):
    def build(self):
        return MyScreen()


if __name__ == '__main__':
    TestApp().run()