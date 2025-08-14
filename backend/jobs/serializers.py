from rest_framework import serializers
from .models import Job, JobCategory, JobApplication, ApplicationNote
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


class ApplicationNoteSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    class Meta:
        model = ApplicationNote
        fields = ('id', 'author', 'body', 'created_at')
        read_only_fields = ('author', 'created_at')


from django.urls import reverse


class JobApplicationSerializer(serializers.ModelSerializer):
    applicant = UserSerializer(read_only=True)
    job = serializers.StringRelatedField(read_only=True)
    notes = ApplicationNoteSerializer(many=True, read_only=True)
    resume_url = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = ('id', 'job', 'applicant', 'cover_letter', 'resume', 'resume_url', 'status', 'applied_at', 'notes')
        read_only_fields = ('applicant', 'job', 'status', 'applied_at', 'notes', 'resume', 'resume_url')
        extra_kwargs = {
            'resume': {'write_only': True}
        }

    def get_resume_url(self, obj):
        request = self.context.get('request')
        if not request:
            return None

        # Only the job owner or an admin can get the download URL
        if request.user.is_staff or obj.job.employer == request.user:
            return request.build_absolute_uri(reverse('jobs:job-application-resume-download', kwargs={'pk': obj.pk}))
        return None
