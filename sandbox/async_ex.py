from kivy.app import App
from kivy.uix.popup import Popup
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.uix.progressbar import ProgressBar

import threading
from src.image_hashing import async_open_and_hash
from multiprocessing import Pool
from imutils import paths

class PopupBox(Popup):
    progress_bar = ObjectProperty()

    def __init__(self, size, **kwa):
        super(PopupBox, self).__init__(**kwa)
        self.progress_bar = ProgressBar(max=size)
        self.content = self.progress_bar

    def increment_progress(self):
        self.progress_bar.value += 1
    

class ExampleApp(App):
    def build(self):
        self.hashes = {}
        self.image_paths = list(paths.list_images("/home/zsmeton/Dropbox/Images/google_dup/"))

    def show_popup(self):
        self.pop_up = Factory.PopupBox(len(self.image_paths))
        self.pop_up.open()

    def process_button_click(self):
        # Open the pop up
        self.show_popup()

        # Call some method that may take a while to run.
        # I'm using a thread to simulate this
        mythread = threading.Thread(target=self.do_100_things)
        mythread.start()

    def do_100_things(self):
        # loop over our image paths and make hashes
        with Pool(processes=4) as pool:
            multiple_results = [pool.apply_async(async_open_and_hash, (image_path, 16)) 
                                for image_path in self.image_paths]
            for res in multiple_results:
                result = res.get()
                if result is not None:
                    h,image_path = result
                    # grab all image paths with that hash, add the current image
                    # path to it, and store the list back in the hashes dictionary
                    p = self.hashes.get(h, [])
                    p.append(image_path)
                    self.hashes[h] = p

                    self.pop_up.increment_progress()

        # Once the long running task is done, close the pop up.
        self.pop_up.dismiss()

if __name__ == "__main__":
    ExampleApp().run()