from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('user', 'User'),
        ('driver', 'Driver'),
        ('seller', 'Seller'),
        ('service_provider', 'Service Provider'),
        ('job_poster', 'Job Poster'),
    )

    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='user')
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)

    # Fields for business information and document uploads can be added here later
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_address = models.CharField(max_length=255, blank=True, null=True)

    # Role status
    is_role_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username

class RoleApplication(models.Model):
    ROLE_CHOICES = (
        ('driver', 'Driver'),
        ('seller', 'Seller'),
        ('service_provider', 'Service Provider'),
        ('job_poster', 'Job Poster'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_applications')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    document1 = models.FileField(upload_to='documents/')
    document2 = models.FileField(upload_to='documents/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'
