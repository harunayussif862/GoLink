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

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='user')
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)

    # Fields for business information and document uploads can be added here later
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_address = models.CharField(max_length=255, blank=True, null=True)
    document = models.FileField(upload_to='documents/', blank=True, null=True)

    # Role status
    is_role_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username
