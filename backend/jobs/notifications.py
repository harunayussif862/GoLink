from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from notifications.models import Notification

def send_new_application_notification(application):
    """
    Notifies the job employer about a new application.
    """
    job = application.job
    employer = job.employer
    applicant = application.applicant

    # Create in-app notification
    Notification.objects.create(
        recipient=employer,
        message=f"You have a new application from {applicant.username} for your job posting '{job.title}'."
    )

    # Send email
    subject = f"New Application for: {job.title}"
    context = {
        'job_title': job.title,
        'applicant_name': applicant.username,
        'employer_name': employer.username,
    }
    html_message = render_to_string('emails/new_application.html', context)
    plain_message = render_to_string('emails/new_application.txt', context)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [employer.email],
        html_message=html_message,
        fail_silently=True # Should not block the application flow
    )

def send_application_status_update_notification(application):
    """
    Notifies the applicant about a status change on their application.
    """
    job = application.job
    applicant = application.applicant

    # Create in-app notification
    Notification.objects.create(
        recipient=applicant,
        message=f"Your application for '{job.title}' has been updated to '{application.get_status_display()}'."
    )

    # Send email
    subject = f"Your application status for '{job.title}' has been updated"
    context = {
        'job_title': job.title,
        'applicant_name': applicant.username,
        'new_status': application.get_status_display(),
    }
    html_message = render_to_string('emails/application_status_update.html', context)
    plain_message = render_to_string('emails/application_status_update.txt', context)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [applicant.email],
        html_message=html_message,
        fail_silently=True
    )


def send_job_status_update_notification(job):
    """
    Notifies an employer that their job post's status has been updated by an admin.
    """
    employer = job.employer

    Notification.objects.create(
        recipient=employer,
        message=f"The status of your job posting '{job.title}' has been updated to '{job.get_status_display()}'."
    )
    # TODO: Add email notification


def send_job_featured_notification(job):
    """
    Notifies an employer that their job has been successfully featured.
    """
    employer = job.employer
    Notification.objects.create(
        recipient=employer,
        message=f"Your job posting '{job.title}' is now featured until {job.featured_until.strftime('%Y-%m-%d %H:%M')}."
    )
    # TODO: Add email notification

def send_feature_expiring_notification(job):
    """
    Notifies an employer that their featured job is expiring soon.
    """
    employer = job.employer
    Notification.objects.create(
        recipient=employer,
        message=f"Your featured job posting '{job.title}' is expiring soon."
    )
    # TODO: Add email notification
