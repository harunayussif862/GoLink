import django_filters
from .models import Job

class JobFilter(django_filters.FilterSet):
    location = django_filters.CharFilter(lookup_expr='icontains')
    salary_range = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Job
        fields = ['location', 'job_type', 'salary_range', 'category']
