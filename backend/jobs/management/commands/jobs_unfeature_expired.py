from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job

class Command(BaseCommand):
    help = 'Un-features jobs whose featured_until date has passed.'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_jobs = Job.objects.filter(
            is_featured=True,
            featured_until__lt=now
        )

        count = expired_jobs.count()
        if count > 0:
            expired_jobs.update(is_featured=False, featured_until=None)
            self.stdout.write(self.style.SUCCESS(f'Successfully un-featured {count} expired jobs.'))
        else:
            self.stdout.write(self.style.SUCCESS('No expired featured jobs to un-feature.'))
