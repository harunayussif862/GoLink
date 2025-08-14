from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import RoleApplication, RoleForm, RoleApplicationFile
import json

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'user_type', 'phone_number')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name', 'phone_number')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_email(self, value):
        """
        Normalize email to lowercase and check for uniqueness.
        """
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number')
        )

        user.set_password(validated_data['password'])
        user.save()

        return user

class RoleApplicationFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleApplicationFile
        fields = ('file', 'field_name')

class RoleApplicationSerializer(serializers.ModelSerializer):
    files = RoleApplicationFileSerializer(many=True, read_only=True)

    class Meta:
        model = RoleApplication
        fields = ('id', 'role_form', 'form_data', 'status', 'created_at', 'files')
        read_only_fields = ('status', 'created_at', 'files')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class RoleApplicationAdminSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    role_form = serializers.StringRelatedField()
    files = RoleApplicationFileSerializer(many=True, read_only=True)

    class Meta:
        model = RoleApplication
        fields = ('id', 'user', 'role_form', 'form_data', 'status', 'created_at', 'files')
        read_only_fields = ('user', 'role_form', 'form_data', 'created_at', 'files')


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)
    otp_code = serializers.CharField(required=False, min_length=6, max_length=6)

    def validate(self, data):
        if data['new_password1'] != data['new_password2']:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        return data
