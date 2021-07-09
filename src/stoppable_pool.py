import multiprocessing as mp
from functools import partial
import queue
import time


class StoppableConsumer(mp.Process):
    def __init__(self, input_queue, result_queue, finish_flag, **kwargs):
        super().__init__(**kwargs)
        self.input_queue = input_queue
        self.result_queue = result_queue
        self.finish_flag = finish_flag

    def run(self) -> None:
        while True:
            try:
                task = self.input_queue.get_nowait()
                self.result_queue.put(task())
            except queue.Empty:
                # If we still aren't signalled to be done, try again
                if not self.finish_flag.value:
                    continue
                else:
                    break


class StoppablePool:
    def __init__(self, data, fn, num_workers=4):
        # Create all the tasks
        self._tasks = [partial(fn, elem) for elem in data]
        self._processes = []
        # Create shared memory
        self._input_queue = mp.Queue()
        self._output_queue = mp.Queue()
        self._finish_flag = mp.Value('b', False)
        # Create data count trackers
        self._num_input_data_given = 0
        self._num_output_data_received = 0
        # Set the number of workers
        self._num_workers = min(num_workers, len(data))

    def __iter__(self):
        if not self._processes:
            # Add some data to the input queue
            [self._input_queue.put(elem) for elem in self._tasks[:self._num_workers]]
            self._num_input_data_given = self._num_workers
            # Create the processes
            self._processes = [StoppableConsumer(self._input_queue, self._output_queue, finish_flag=self._finish_flag) for
                               i in range(self._num_workers)]
            # Start the processes
            [process.start() for process in self._processes]

        return self

    def __next__(self):
        # Input data
        if self._num_input_data_given < len(self._tasks):
            # Add data to input queue if we can
            self._input_queue.put(self._tasks[self._num_input_data_given])
            self._num_input_data_given += 1
        elif not self._finish_flag.value:
            # No data, then set the finish flag if that hasn't been set
            self._finish_flag.value = True

        # Output data
        if self._num_output_data_received < len(self._tasks):
            # Get data from output queue
            result = self._output_queue.get()
            self._num_output_data_received += 1
            return result
        else:
            # Join all the processes
            [process.join() for process in self._processes]
            # Stop the iter
            raise StopIteration

    def terminate(self):
        # Stop and join all the processes
        self._finish_flag.value = True
        [process.join() for process in self._processes]
        # Clear all the data
        self._tasks = []
        self._processes = []
        self._num_input_data_given = 0
        self._num_output_data_received = 0
        self._num_workers = 0


if __name__ == "__main__":
    import math

    nums = [i for i in range(100)]

    for res in StoppablePool(nums, math.sin):
        print(res)

    pool = StoppablePool(nums, math.sin)
    for i, res in enumerate(pool):
        print(res)
        if i > 10:
            print("terminating")
            pool.terminate()

