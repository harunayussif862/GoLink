from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Category, Product

User = get_user_model()

class EcommerceAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='password',
            user_type='seller',
            is_role_verified=True
        )
        cls.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='password'
        )
        cls.category = Category.objects.create(name='Electronics', slug='electronics')
        cls.product = Product.objects.create(
            seller=cls.seller,
            category=cls.category,
            title='Laptop',
            description='A cool laptop',
            price=1200.00,
            stock_quantity=10
        )
        cls.product_list_url = reverse('ecommerce:all_products')
        cls.category_list_url = reverse('ecommerce:categories')
        cls.product_management_url = reverse('ecommerce:products-list')

    def test_list_products(self):
        """
        Ensure any user can list products.
        """
        response = self.client.get(self.product_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Laptop')

    def test_list_categories(self):
        """
        Ensure any user can list categories.
        """
        response = self.client.get(self.category_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Electronics')

    def test_seller_can_create_product(self):
        """
        Ensure a verified seller can create a product.
        """
        self.client.force_authenticate(user=self.seller)
        data = {
            'title': 'Mouse',
            'description': 'A nice mouse',
            'price': '25.00',
            'stock_quantity': 50,
            'category_id': self.category.id
        }
        response = self.client.post(self.product_management_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)

    def test_buyer_cannot_create_product(self):
        """
        Ensure a buyer cannot create a product.
        """
        self.client.force_authenticate(user=self.buyer)
        data = {
            'title': 'Keyboard',
            'description': 'A mechanical keyboard',
            'price': '100.00',
            'stock_quantity': 20
        }
        response = self.client.post(self.product_management_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
