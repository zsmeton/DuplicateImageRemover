import os

from kivy.clock import Clock
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.stacklayout import StackLayout
from kivy.properties import BooleanProperty, ObjectProperty, ListProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.properties import StringProperty, NumericProperty

from kivy.factory import Factory
from kivy import Logger


# Optional Hard-Feature
# TODO: Add undo handling so if ctrl z is pressed the last action is undone \
#  (for now that could be just restoring the most recently deleted images) \
#  maybe store those images in a directory and then delete on shutdown, if images are there when the program starts \
#  could load to screen resuming the session (in case of bad exit)

# Features
# TODO: Add deletion of images when delete button pressed
#   but make sure that their is a debug mode of some sort where the images are not actually deleted
# TODO: Add slider to control image size
# TODO: Add preview mode or detailed view mode (size, date created, etc)
# TODO: Add clear selection button
# TODO: Add sorting button
# TODO: Add back button
# TODO: Custom checkbox so it is more visible on white images

# Optimize
# TODO: Find way to reduce impact of loading images on window speed (pre setting width/height, lazy do_layout, other)
# TODO: Fix scroll bar issues when deleting images


class ImageGroupsLayout(FocusBehavior, LayoutSelectionBehavior,
                        RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class ImageGroupDataView(RecycleDataViewBehavior, StackLayout):
    index = NumericProperty(0)  # The selection index for the widget in the recycle view
    selected = BooleanProperty(False)  # Whether the current view is selected or not
    selectable = BooleanProperty(True)  # Whether the current view can be selected
    widgetclass = StringProperty('None')  # The type of widgets this grid contains

    def __init__(self, **kwargs):
        super(ImageGroupDataView, self).__init__(**kwargs)
        self.selected_nodes = {}  # Dictionary of indexes to selected subwidgets

    def refresh_view_attrs(self, rv, index, data):
        """
        Catches and handles changes to the view (updates the view)

        Args:
            rv: The associated RecycleView
            index: The index of the current view
            data: The data used to build the view, should contain a data element which stores a list to each element

        Returns:

        """
        # Reset the view
        self.index = index
        # Selection status
        self.selected = len(data.get('selected', set())) > 0
        self.selected_nodes[self.index] = data.get('selected', set())
        # Widgets
        self.clear_widgets()
        widget_type = Factory.get(self.widgetclass)  # Dynamically get the selection status based on the widget class
        for i, kwargs in enumerate(data.get('data', [])):
            new_widget = widget_type(index=i, **kwargs)
            self.add_widget(new_widget, index=i)
            new_widget.apply_selection(i, i in self.selected_nodes[self.index])

        return super(ImageGroupDataView, self).refresh_view_attrs(rv, index, data)

    def select_with_touch(self, index, touch=None):
        """
        Performs selection of self and selected widget
        Args:
            index: the selected widget
            touch: the touch event

        Returns: Whether the LayoutSelection selected this grid
        """
        # toggle selection of the child
        if not self.select_node(index):
            self.deselect_node(index)

        # Toggle selection of self
        if self.selectable:
            # Only call selection on this widget if:
            # Case 1: currently not selected and has selected children
            if not self.selected and self.selected_nodes.get(self.index, set()):
                return self.parent.select_with_touch(self.index, touch)
            # Case 2: currently selected and has no selected children
            elif self.selected and not self.selected_nodes.get(self.index, set()):
                return self.parent.select_with_touch(self.index, touch)

    def select_node(self, node):
        """
        Selects the subwidgets if not already selected, also calls apply_selection on child node
        Args:
            node: Index of the widget to select

        Returns:
            True if the node was selected
            False if it was already selected
        """
        # TODO: Add type error handling
        if node >= len(self.children) or node < 0:
            raise ValueError(f"Invalid node index of {node} with {len(self.children)} selectable nodes")

        if node not in self.selected_nodes.get(self.index, set()):
            self.selected_nodes.get(self.index, set()).add(node)
            self.children[node].apply_selection(node, True)
            return True
        else:
            return False

    def deselect_node(self, node):
        """
        Deselects the subwidgets if already selected, also calls apply_selection on child node
        Args:
            node: Index of the widget to deselect

        Returns:
            True if the node was deselected
            False if it wasn't already
        """
        # TODO: Add type error handling
        if node >= len(self.children) or node < 0:
            raise ValueError(f"Invalid node index of {node} with {len(self.children)} selectable nodes")

        if node not in self.selected_nodes.get(self.index, {}):
            return False
        else:
            self.selected_nodes[self.index].remove(node)
            self.children[node].apply_selection(node, False)
            return True

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        rv.data[index]['selected'] = self.selected_nodes[index]


class SelectableImage(RelativeLayout):
    ''' Add selection support to the Label '''
    index = NumericProperty(0)
    source = StringProperty()
    image_ratio = NumericProperty()
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def __init__(self, index, **kwargs):
        super(SelectableImage, self).__init__(**kwargs)
        self.index = index

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(SelectableImage, self).on_touch_down(touch):
            Logger.debug("selecting image")
            self.parent.select_with_touch(self.index, touch)
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            Logger.debug(f"detailing image: {self.source}")
            return True

    def apply_selection(self, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected


class ImageGroupsRecycleView(RecycleView):
    info_selection = ObjectProperty()
    duplicate_images = ListProperty()

    def __init__(self, **kwargs):
        super(ImageGroupsRecycleView, self).__init__(**kwargs)
        self.data = []
        self.images_to_remove = []

    def on_duplicate_images(self, *args):
        self.data = [{'data': [{'source': image_path, 'image_ratio': image_ratio}
                               for image_path, image_ratio in duplicate_group]}
                     for duplicate_group in self.duplicate_images]

    def remove_selected(self):
        # Set data to data without selection
        new_data = []
        for i, group in enumerate(self.data):
            unselected_data = [elem for i, elem in enumerate(group['data']) if i not in group.get('selected', set())]
            selected_data = [elem for i, elem in enumerate(group['data']) if i in group.get('selected', set())]

            for data in selected_data:
                image_path, ratio = data.values()
                self.images_to_remove.append(image_path)

            if len(unselected_data) > 1:
                new_group = {'data': unselected_data}
                new_data.append(new_group)

        # Clear layout managers selection
        selected = self.layout_manager.selected_nodes[:]
        for select in selected:
            self.layout_manager.deselect_node(select)

        self.data = new_data
        Clock.schedule_once(self.remove_images)

    def remove_images(self, dt):
        for image_path in self.images_to_remove:
            os.remove(image_path)

        self.images_to_remove = []
