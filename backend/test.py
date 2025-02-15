from django.test import TestCase

class BasicTestCase(TestCase):
    def test_basic_addition(self):
        """Test if 1 + 1 equals 2"""
        self.assertEqual(1 + 1, 2)
    