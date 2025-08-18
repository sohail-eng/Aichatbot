import asyncio
from django.core.management.base import BaseCommand
from ai_services.foundry_service import FoundryService

class Command(BaseCommand):
    help = 'Test AI service connection'
    
    def handle(self, *args, **options):
        asyncio.run(self._test_ai_service())
    
    async def _test_ai_service(self):
        llama_service = FoundryService()
        
        self.stdout.write('Testing AI service connection...')
        
        if llama_service.health_check():
            self.stdout.write(self.style.SUCCESS('✓ AI service is running'))
            
            # Test response
            try:
                response_chunks = []
                async for chunk in llama_service.generate_streaming_response("Hello, how are you?"):
                    response_chunks.append(chunk)
                response = ''.join(response_chunks)
                self.stdout.write(f'Test response: {response[:100]}...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error getting response: {e}'))
        else:
            self.stdout.write(self.style.ERROR('✗ AI service is not available'))
            self.stdout.write('Make sure your AI service is running and accessible')