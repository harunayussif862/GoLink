from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from .models import Category, Product, Cart, CartItem, Order, ProductReview, SellerReview, RefundRequest
from wallets.models import Wallet

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


class CartAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(username='seller', email='seller@example.com', password='password', user_type='seller', is_role_verified=True)
        cls.buyer = User.objects.create_user(username='buyer', email='buyer@example.com', password='password')
        cls.product = Product.objects.create(seller=cls.seller, title='Test Product', price=10.00, stock_quantity=10)
        cls.cart = Cart.objects.get(user=cls.buyer)
        cls.cart_item = CartItem.objects.create(cart=cls.cart, product=cls.product, quantity=1)

    def setUp(self):
        self.client.force_authenticate(user=self.buyer)
        self.cart_url = reverse('ecommerce:cart-list')
        self.add_item_url = reverse('ecommerce:cart-add-item')
        self.update_item_url = reverse('ecommerce:cart-update-item', kwargs={'pk': self.cart_item.pk})
        self.remove_item_url = reverse('ecommerce:cart-remove-item', kwargs={'pk': self.cart_item.pk})

    def test_view_cart(self):
        """
        Ensure a user can view their cart.
        """
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)

    def test_add_item_to_cart(self):
        """
        Ensure a user can add an item to their cart.
        """
        product2 = Product.objects.create(seller=self.seller, title='Another Product', price=20.00, stock_quantity=5)
        data = {'product_id': product2.id, 'quantity': 2}
        response = self.client.post(self.add_item_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 2)

    def test_update_cart_item(self):
        """
        Ensure a user can update the quantity of an item in their cart.
        """
        data = {'quantity': 5}
        response = self.client.patch(self.update_item_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['items'][0]['quantity'], 5)

    def test_remove_cart_item(self):
        """
        Ensure a user can remove an item from their cart.
        """
        response = self.client.delete(self.remove_item_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.cart.items.count(), 0)


class CheckoutAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(username='seller', email='seller@example.com', password='password', user_type='seller', is_role_verified=True)
        cls.buyer = User.objects.create_user(username='buyer', email='buyer@example.com', password='password')
        cls.product = Product.objects.create(seller=cls.seller, title='Test Product', price=100.00, stock_quantity=10)
        cls.cart = Cart.objects.get(user=cls.buyer)
        CartItem.objects.create(cart=cls.cart, product=cls.product, quantity=2)

        # Give buyer enough balance
        buyer_wallet = Wallet.objects.get(user=cls.buyer)
        buyer_wallet.balance = 500
        buyer_wallet.save()

        # Create GoLink platform user
        User.objects.create_superuser(
            username='golink_platform',
            email='platform@golink.com',
            password='password'
        )

    def setUp(self):
        self.client.force_authenticate(user=self.buyer)
        self.checkout_url = reverse('ecommerce:checkout')

    def test_successful_checkout(self):
        """
        Ensure a user can successfully checkout.
        """
        response = self.client.post(self.checkout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check buyer's wallet
        buyer_wallet = Wallet.objects.get(user=self.buyer)
        self.assertEqual(buyer_wallet.balance, 300) # 500 - 200

        # Check seller's wallet
        seller_wallet = Wallet.objects.get(user=self.seller)
        self.assertEqual(seller_wallet.balance, 180) # 200 - 20 (10% commission)

        # Check GoLink's wallet
        golink_user = User.objects.get(username='golink_platform')
        golink_wallet = Wallet.objects.get(user=golink_user)
        self.assertEqual(golink_wallet.balance, 20)

        # Check order creation
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.total_price, 200)
        self.assertEqual(order.items.count(), 1)

        # Check cart is cleared
        self.assertEqual(self.cart.items.count(), 0)

    def test_checkout_empty_cart(self):
        """
        Ensure a user cannot checkout with an empty cart.
        """
        self.cart.items.all().delete()
        response = self.client.post(self.checkout_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_insufficient_balance(self):
        """
        Ensure a user cannot checkout with insufficient balance.
        """
        buyer_wallet = Wallet.objects.get(user=self.buyer)
        buyer_wallet.balance = 100
        buyer_wallet.save()
        response = self.client.post(self.checkout_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReviewAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(username='seller', email='seller@example.com', password='password', user_type='seller', is_role_verified=True)
        cls.buyer = User.objects.create_user(username='buyer', email='buyer@example.com', password='password')
        cls.product = Product.objects.create(seller=cls.seller, title='Test Product', price=10.00, stock_quantity=10)

    def setUp(self):
        self.client.force_authenticate(user=self.buyer)
        self.product_review_url = reverse('ecommerce:product-reviews-list', kwargs={'product_pk': self.product.pk})
        self.seller_review_url = reverse('ecommerce:seller-reviews-list', kwargs={'seller_pk': self.seller.pk})

    def test_create_product_review(self):
        """
        Ensure a user can create a review for a product.
        """
        data = {'rating': 5, 'review': 'Great product!'}
        response = self.client.post(self.product_review_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProductReview.objects.count(), 1)

    def test_create_seller_review(self):
        """
        Ensure a user can create a review for a seller.
        """
        data = {'rating': 4, 'review': 'Good seller.'}
        response = self.client.post(self.seller_review_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SellerReview.objects.count(), 1)


class RefundAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(username='seller', email='seller@example.com', password='password', user_type='seller', is_role_verified=True)
        cls.buyer = User.objects.create_user(username='buyer', email='buyer@example.com', password='password')
        cls.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        cls.order = Order.objects.create(user=cls.buyer, total_price=100.00)

    def test_create_refund_request(self):
        """
        Ensure a user can create a refund request for their order.
        """
        self.client.force_authenticate(user=self.buyer)
        data = {'order': self.order.id, 'reason': 'Product was damaged.'}
        url = reverse('ecommerce:refunds-list')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RefundRequest.objects.count(), 1)

    def test_approve_refund_request(self):
        """
        Ensure an admin/seller can approve a refund request.
        """
        self.client.force_authenticate(user=self.admin_user)
        refund_request = RefundRequest.objects.create(order=self.order, reason='Test')
        url = reverse('ecommerce:refunds-approve', kwargs={'pk': refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'approved')

    def test_reject_refund_request(self):
        """
        Ensure an admin/seller can reject a refund request.
        """
        self.client.force_authenticate(user=self.admin_user)
        refund_request = RefundRequest.objects.create(order=self.order, reason='Test')
        url = reverse('ecommerce:refunds-reject', kwargs={'pk': refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refund_request.refresh_from_db()
        self.assertEqual(refund_request.status, 'rejected')

    def test_buyer_cannot_approve_refund(self):
        """
        Ensure a buyer cannot approve a refund request.
        """
        self.client.force_authenticate(user=self.buyer)
        refund_request = RefundRequest.objects.create(order=self.order, reason='Test')
        url = reverse('ecommerce:refunds-approve', kwargs={'pk': refund_request.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
