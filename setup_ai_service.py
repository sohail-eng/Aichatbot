#!/usr/bin/env python3
"""
AI Service Setup Script
This script helps you set up the AI service for the chat application.
"""

import sys
import subprocess
import requests
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print("✅ Python version is compatible")
    return True


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import django as django
        import channels as channels
        import httpx as httpx

        print("✅ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False


def test_ai_service_connection():
    """Test connection to AI service"""
    try:
        response = requests.get("http://localhost:8080/v1/models", timeout=5)
        if response.status_code == 200:
            print("✅ AI service is running and accessible")
            return True
        else:
            print(f"⚠️  AI service responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to AI service at localhost:8080")
        return False
    except Exception as e:
        print(f"❌ Error testing AI service: {e}")
        return False


def check_ollama():
    """Check if Ollama is available"""
    try:
        result = subprocess.run(
            ["ollama", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("✅ Ollama is installed")
            return True
        else:
            print("❌ Ollama is not working properly")
            return False
    except FileNotFoundError:
        print("❌ Ollama is not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False


def setup_ollama():
    """Setup Ollama with a model"""
    print("\n🐐 Setting up Ollama...")

    # Check if llama2 model is available
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10
        )
        if "llama2" in result.stdout:
            print("✅ Llama2 model is already available")
            return True
    except Exception:
        pass

    # Pull llama2 model
    print("📥 Pulling llama2 model (this may take a while)...")
    try:
        subprocess.run(["ollama", "pull", "llama2"], check=True)
        print("✅ Llama2 model downloaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to pull llama2 model: {e}")
        return False


def update_settings_for_ollama():
    """Update settings.py to use Ollama"""
    settings_file = Path("chat_project/settings.py")

    if not settings_file.exists():
        print("❌ settings.py not found")
        return False

    try:
        content = settings_file.read_text()

        # Update AI_CONFIG for Ollama
        ollama_config = """# AI Configuration
AI_CONFIG = {
    'LLAMA_API_URL': 'http://localhost:11434/v1/chat/completions',  # Ollama endpoint
    'MODEL_NAME': 'llama2',
    'MAX_TOKENS': 2048,
    'TEMPERATURE': 0.7,
}"""

        # Replace the existing AI_CONFIG
        import re

        pattern = r"# AI Configuration\s+AI_CONFIG = \{.*?\}"
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, ollama_config, content, flags=re.DOTALL)
            settings_file.write_text(content)
            print("✅ Updated settings.py for Ollama")
            return True
        else:
            print("⚠️  Could not find AI_CONFIG in settings.py")
            return False

    except Exception as e:
        print(f"❌ Error updating settings.py: {e}")
        return False


def main():
    """Main setup function"""
    print("🤖 AI Service Setup for Chat Application")
    print("=" * 50)

    # Check prerequisites
    if not check_python_version():
        return False

    if not check_dependencies():
        return False

    print("\n🔍 Checking AI service availability...")

    # Test current AI service
    if test_ai_service_connection():
        print("\n🎉 AI service is already working!")
        return True

    print("\n📋 AI Service Options:")
    print("1. Setup Ollama (local, free)")
    print("2. Use Foundry Local (local, requires license)")
    print("3. Use OpenAI API (cloud, requires API key)")
    print("4. Use Google AI Studio (cloud, requires API key)")
    print("5. Skip AI service setup (limited functionality)")

    choice = input("\nEnter your choice (1-5): ").strip()

    if choice == "1":
        if check_ollama():
            if setup_ollama():
                if update_settings_for_ollama():
                    print("\n🎉 Ollama setup complete!")
                    print("Start Ollama with: ollama serve")
                    print(
                        "Then start the chat application with: python manage.py runserver"
                    )
                    return True
        else:
            print("\n📥 Installing Ollama...")
            print("Please visit: https://ollama.ai/")
            print("Follow the installation instructions for your platform")
            return False

    elif choice == "2":
        print("\n📥 Installing Foundry Local...")
        print("Please visit: https://foundry.local/")
        print("Follow the installation instructions")
        print("Then start with: foundry local")
        return False

    elif choice == "3":
        print("\n🔑 OpenAI API Setup:")
        api_key = input("Enter your OpenAI API key: ").strip()
        if api_key:
            # Update settings for OpenAI
            settings_file = Path("chat_project/settings.py")
            content = settings_file.read_text()

            openai_config = f"""# AI Configuration
AI_CONFIG = {{
    'LLAMA_API_URL': 'https://api.openai.com/v1/chat/completions',
    'MODEL_NAME': 'gpt-3.5-turbo',
    'MAX_TOKENS': 2048,
    'TEMPERATURE': 0.7,
    'API_KEY': '{api_key}',
}}"""

            import re

            pattern = r"# AI Configuration\s+AI_CONFIG = \{.*?\}"
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, openai_config, content, flags=re.DOTALL)
                settings_file.write_text(content)
                print("✅ Updated settings.py for OpenAI API")
                return True

        print("❌ Invalid API key")
        return False

    elif choice == "4":
        print("\n🔑 Google AI Studio Setup:")
        api_key = input("Enter your Google AI Studio API key: ").strip()
        if api_key:
            # Update settings for Google AI Studio
            settings_file = Path("chat_project/settings.py")
            content = settings_file.read_text()

            google_ai_config = f"""# AI Configuration
AI_CONFIG = {{
    'LLAMA_API_URL': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:streamGenerateContent',
    'MODEL_NAME': 'gemini-pro',
    'MAX_TOKENS': 2048,
    'TEMPERATURE': 0.7,
    'API_KEY': '{api_key}',
}}"""

            import re

            pattern = r"# AI Configuration\s+AI_CONFIG = \{.*?\}"
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, google_ai_config, content, flags=re.DOTALL)
                settings_file.write_text(content)
                print("✅ Updated settings.py for Google AI Studio")
                return True

        print("❌ Invalid API key")
        return False

    elif choice == "5":
        print("\n⚠️  AI service setup skipped")
        print("The application will work for file uploads and database connections")
        print("but chat functionality will be limited")
        return True

    else:
        print("❌ Invalid choice")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
