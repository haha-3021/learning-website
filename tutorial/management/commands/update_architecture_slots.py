# management/commands/update_architecture_slots.py
from django.core.management.base import BaseCommand
from tutorial.models import ArchitectureSlot

class Command(BaseCommand):
    help = 'Update architecture slots to match the image structure'

    def handle(self, *args, **options):
        # Delete existing slots
        ArchitectureSlot.objects.all().delete()
        self.stdout.write('Deleted existing architecture slots')
        
        # Create new slots from views.py function
        from tutorial.views import create_default_slots
        create_default_slots()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully updated architecture slots to match image structure')
        )