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

class FormField(models.Model):
    FIELD_TYPE_CHOICES = (
        ('text', 'Text'),
        ('textarea', 'Text Area'),
        ('file', 'File'),
        ('image', 'Image'),
        ('checkbox', 'Checkbox'),
    )
    role_form = models.ForeignKey('RoleForm', on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    required = models.BooleanField(default=True)

    def __str__(self):
        return self.label

class RoleForm(models.Model):
    name = models.CharField(max_length=255, unique=True)
    role = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class RoleApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_applications')
    role_form = models.ForeignKey(RoleForm, on_delete=models.PROTECT, null=True, blank=True)
    form_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.role_form.name}'
