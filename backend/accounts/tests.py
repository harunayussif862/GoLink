from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

User = get_user_model()

class UserModelTests(TestCase):

    def test_create_user(self):
        """
        Test creating a new user with a username and password.
        """
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpassword'))
        self.assertEqual(user.user_type, 'user')
        self.assertFalse(user.is_role_verified)

    def test_create_superuser(self):
        """
        Test creating a new superuser.
        """
        admin_user = User.objects.create_superuser(username='super', email='super@example.com', password='password123')
        self.assertEqual(admin_user.username, 'super')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_user_str(self):
        """
        Test the string representation of the user model.
        """
        user = User.objects.create_user(username='testuser', password='testpassword')
        self.assertEqual(str(user), 'testuser')

    def test_create_driver(self):
        """
        Test creating a user with the 'driver' role.
        """
        driver = User.objects.create_user(
            username='driver1',
            password='password123',
            user_type='driver',
            phone_number='1234567890',
            business_name='Test Driver',
            is_role_verified=True
        )
        self.assertEqual(driver.user_type, 'driver')
        self.assertEqual(driver.phone_number, '1234567890')
        self.assertEqual(driver.business_name, 'Test Driver')
        self.assertTrue(driver.is_role_verified)

    def test_phone_number_uniqueness(self):
        """
        Test that the phone_number field is unique.
        """
        User.objects.create_user(username='user1', password='password123', phone_number='9876543210')
        with self.assertRaises(IntegrityError):
            User.objects.create_user(username='user2', password='password123', phone_number='9876543210')
