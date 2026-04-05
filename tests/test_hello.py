import unittest

class TestHello(unittest.TestCase):
    def test_hello(self):
        self.assertEqual("hello", "hello")

if __name__ == "__main__":
    unittest.main()
