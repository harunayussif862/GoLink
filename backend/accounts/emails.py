from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone

def send_password_change_email(user, request):
    """
    Sends an email notification to the user after a successful password change.
    """
    subject = _("Your GoLink Password Was Changed")

    # Get client IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    context = {
        'username': user.username,
        'ip_address': ip,
        'timestamp': timezone.now(),
    }

    html_message = render_to_string('emails/password_change_body.html', context)
    plain_message = render_to_string('emails/password_change_body.txt', context)

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False, # In production, this should be True with proper logging
    )
