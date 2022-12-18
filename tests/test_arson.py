import unittest
import arson

class ArsonTest(unittest.TestCase):

    def test_arson(self):
        self.assertTrue(arson.run_tests(arson.parse, arson.dump))

if __name__ == '__main__':
    unittest.main()
