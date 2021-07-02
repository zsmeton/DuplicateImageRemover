from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors.compoundselection import CompoundSelectionBehavior
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.properties import StringProperty, NumericProperty

from kivy.factory import Factory

# TODO: Create selectable images class and add deletion of images when delete button pressed
# TODO: Add slider to control image size
# TODO: Add sorting button
#

class SelectionRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior,
                                 RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''


class SelectableGridDataView(RecycleDataViewBehavior, GridLayout):
    selected = BooleanProperty(False) # Whether the current view is selected or not
    selectable = BooleanProperty(True) # Whether the current view can be selected
    widgetclass = StringProperty('None')  # The type of widgets this grid contains

    def __init__(self, **kwargs):
        super(SelectableGridDataView, self).__init__(**kwargs)
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
        ''' Catch and handle the view changes '''
        # Set selection
        self.selected = False
        # Set index
        self.index = index
        # Set selection
        self.selected_nodes[self.index] = data.get('selected', set())
        # Remove old widgets
        self.clear_widgets()
        # Add new widgets
        widget_type = Factory.get(self.widgetclass)
        for i, kwargs in enumerate(data['data']):
            new_widget = widget_type(index=i, **kwargs)
            self.add_widget(new_widget)
            new_widget.apply_selection(i, i in self.selected_nodes[self.index])

        return super(SelectableGridDataView, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """
        Consumes a touch event
        Args:
            touch: the touch

        Returns:
        """
        return True

    def select_with_touch(self, index, touch=None):
        """
        Performs selection of self and selected widget
        Args:
            index: the selected widget
            touch: the touch event

        Returns: Whether the LayoutSelection selected this grid
        """
        # TODO: Figure out what this code below is doing
        print('select_with_touch', self.index, index, self.selected_nodes)
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
            False if it wasn't already
        """
        if node not in self.selected_nodes.get(self.index, set()):
            self.selected_nodes.get(self.index, set()).add(node)
            self.widgets[node].apply_selection(node, True)
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
        if node not in self.selected_nodes.get(self.index, {}):
            self.widgets[node].apply_selection(node, False)
            return False
        else:
            self.selected_nodes[self.index].remove(node)
            self.widgets[node].apply_selection(node, False)
            return True

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        rv.data[index]['selected'] = self.selected_nodes[index]


class SelectableLabel(Label):
    ''' Add selection support to the Label '''
    source = StringProperty('C:\\Users\\zsmet\\Pictures\\Saved Pictures\\1458021454503.jpg')
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)
    index = NumericProperty(0)

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


class DuplicateManager(RecycleView):
    def __init__(self, **kwargs):
        super(DuplicateManager, self).__init__(**kwargs)
        self.data = [{'data': [{'text': str(i)} for i in range(5)]} for x in range(100)]

    def remove_selected(self):
        # Set data to data without selection
        new_data = []
        for i, group in enumerate(self.data):
            unselected_data = [elem for i, elem in enumerate(group['data']) if i not in group.get('selected', set())]
            if unselected_data:
                new_group = {'data': unselected_data}
                new_data.append(new_group)

        # Clear layout managers selection
        selected = set(self.layout_manager.selected_nodes)
        for select in selected:
            self.layout_manager.deselect_node(select)

        self.data = new_data



