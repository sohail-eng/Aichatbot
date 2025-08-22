from django.core.management.base import BaseCommand
from ai_services.foundry_service import LlamaService

class Command(BaseCommand):
    help = 'Test AI service connection'
    
    def handle(self, *args, **options):
        llama_service = LlamaService()
        
        self.stdout.write('Testing Llama3 connection...')
        
        if llama_service.health_check():
            self.stdout.write(self.style.SUCCESS('✓ Llama3 service is running'))
            
            # Test response
            response = llama_service.generate_response("Hello, how are you?")
            self.stdout.write(f'Test response: {response[:100]}...')
        else:
            self.stdout.write(self.style.ERROR('✗ Llama3 service is not available'))
            self.stdout.write('Make sure Ollama is running and llama3 model is installed')