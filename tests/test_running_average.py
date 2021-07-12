from unittest import TestCase
from src.running_average import RunningAverage


class TestRunningAverage(TestCase):
    pass


class TestInit(TestRunningAverage):
    def test_initial_average(self):
        r = RunningAverage()
        self.assertEqual(r.average, 0)

    def test_initial_invalid_k(self):
        self.assertRaises(ValueError, RunningAverage, k_points=0)
        self.assertRaises(ValueError, RunningAverage, k_points=-1)
        self.assertRaises(ValueError, RunningAverage, k_points="s")


class TestAdd(TestRunningAverage):
    def test_int_3(self):
        r = RunningAverage(k_points=3)
        r.add(1)
        self.assertEqual(r.average, 1)
        r.add(2)
        self.assertEqual(r.average, 1.5)
        r.add(3)
        self.assertEqual(r.average, 2)
        r.add(4)
        self.assertEqual(r.average, 3)
        r.add(0)
        self.assertEqual(r.average, 7 / 3)

    def test_int_none(self):
        r = RunningAverage(k_points=None)
        r.add(1)
        self.assertEqual(r.average, 1)
        r.add(2)
        self.assertEqual(r.average, 1.5)
        r.add(3)
        self.assertEqual(r.average, 2)
        r.add(4)
        self.assertEqual(r.average, 10 / 4)
        r.add(0)
        self.assertEqual(r.average, 10 / 5)

    def test_str(self):
        r = RunningAverage(k_points=None)
        self.assertRaises(ValueError, r.add, "hello")
