from collections import deque


class RunningAverage:
    """
    Data structure which keeps track of a running average given the next value
    """
    def __init__(self, k_points=None):
        """

        Args:
            k_points: The number of values to use for the running average, None will use all data
        """
        self.average = 0

        if not isinstance(k_points, (int, type(None))):
            raise ValueError("k_points must be a positive integer or None")
        if k_points is not None and k_points <= 0:
            raise ValueError("Cannot have running average with 0 or less values")
        self._k_points = k_points
        self._total = 0
        self._values = deque()

    def add(self, num):
        """ Adds a number to the running average, updating the average

        Args:
            num: number to add to the series

        Returns:
        """
        if not isinstance(num, (int, float)):
            raise ValueError("Cannot perform running average on non-number")

        self._total += num
        self._values.append(num)

        if self._k_points and len(self._values) > self._k_points:
            self._total -= self._values.popleft()

        self.average = self._total / len(self._values)