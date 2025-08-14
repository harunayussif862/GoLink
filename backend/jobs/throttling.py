from rest_framework.throttling import UserRateThrottle

class JobApplicationRateThrottle(UserRateThrottle):
    scope = 'job_apply'
