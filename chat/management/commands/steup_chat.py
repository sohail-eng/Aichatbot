from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Setup the chat application'
    
    def handle(self, *args, **options):
        self.stdout.write('Setting up Django Chat App...')
        
        # Create media directories
        os.makedirs('media/uploads', exist_ok=True)
        self.stdout.write(self.style.SUCCESS('✓ Created media directories'))
        
        # Create superuser if none exists
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS('✓ Created admin user (admin/admin123)'))
        
        self.stdout.write(self.style.SUCCESS('Setup complete!'))
        self.stdout.write('Next steps:')
        self.stdout.write('1. Install Ollama and run: ollama pull llama3')
        self.stdout.write('2. Start Redis server')
        self.stdout.write('3. Run: python manage.py runserver')
