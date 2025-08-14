from rest_framework import serializers
from .models import Job, JobCategory
from accounts.serializers import UserSerializer

class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = ('id', 'name')

class JobSerializer(serializers.ModelSerializer):
    employer = UserSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=JobCategory.objects.all(), source='category', write_only=True, required=False, allow_null=True
    )
    category = JobCategorySerializer(read_only=True)

    class Meta:
        model = Job
        fields = (
            'id', 'employer', 'category', 'category_id', 'title', 'description',
            'salary_range', 'location', 'job_type', 'status',
            'vip_only', 'created_at', 'updated_at'
        )
        read_only_fields = ('employer', 'status', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['employer'] = self.context['request'].user
        return super().create(validated_data)
