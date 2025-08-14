from rest_framework import permissions

class IsVipEmployer(permissions.BasePermission):
    """
    Allows access only to users who are verified VIP Employers.
    """
    message = 'Only VIP Employers can perform this action.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_vip_employer

class IsJobOwner(permissions.BasePermission):
    """
    Allows access only to the user who owns the job posting.
    """
    message = 'You do not have permission to edit this job posting.'

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the owner of the job.
        return obj.employer == request.user

class IsApplicant(permissions.BasePermission):
    """
    Allows access only to the user who submitted the application.
    """
    def has_object_permission(self, request, view, obj):
        return obj.applicant == request.user

class IsJobOwnerOfApplication(permissions.BasePermission):
    """
    Allows access only to the user who owns the job associated with the application.
    """
    def has_object_permission(self, request, view, obj):
        return obj.job.employer == request.user
