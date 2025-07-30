#!/usr/bin/env python3
"""
Health check script for Hugin Transcription Service
Validates all dependencies and configuration before running the main service
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Add lib directory to path
sys.path.append(str(Path(__file__).parent))

def setup_logging():
    """Set up logging for health check"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - HEALTH_CHECK - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is 3.10+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        return False, f"Python {version.major}.{version.minor} is too old. Requires Python 3.10+"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"

def check_environment_variables():
    """Check if all required environment variables are set"""
    required_vars = [
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_CONTAINER_NAME", 
        "OPENAI_API_KEY",
        "LOGIC_APP_CHAT_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        return False, f"Missing environment variables: {', '.join(missing_vars)}"
    
    return True, "All environment variables present"

def check_system_dependencies():
    """Check if system dependencies are available"""
    dependencies = {
        'ffmpeg': 'ffmpeg -version',
    }
    
    missing = []
    for name, command in dependencies.items():
        try:
            subprocess.run(command.split(), stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE, check=True, timeout=10)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing.append(name)
    
    if missing:
        return False, f"Missing system dependencies: {', '.join(missing)}"
    
    return True, "All system dependencies available"

def check_python_imports():
    """Check if all Python dependencies can be imported"""
    imports_to_test = [
        ('azure.storage.blob', 'Azure Blob Storage SDK'),
        ('openai', 'OpenAI API client'),
        ('transformers', 'Transformers library'),
        ('torch', 'PyTorch'),
        ('ffmpeg', 'ffmpeg-python'),
        ('docx', 'python-docx'),
        ('requests', 'requests library'),
        ('dotenv', 'python-dotenv'),
    ]
    
    failed_imports = []
    for module, description in imports_to_test:
        try:
            __import__(module)
        except ImportError:
            failed_imports.append(f"{module} ({description})")
    
    if failed_imports:
        return False, f"Failed to import: {', '.join(failed_imports)}"
    
    return True, "All Python dependencies importable"

def check_directories():
    """Check if required directories exist and are writable"""
    required_dirs = ['blobber', 'ferdig_tekst', 'oppsummeringer', 'logs']
    
    issues = []
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        
        if not dir_path.exists():
            try:
                dir_path.mkdir(exist_ok=True)
            except PermissionError:
                issues.append(f"Cannot create directory: {dir_name}")
                continue
        
        if not os.access(dir_path, os.W_OK):
            issues.append(f"Directory not writable: {dir_name}")
    
    if issues:
        return False, '; '.join(issues)
    
    return True, f"All directories available: {', '.join(required_dirs)}"

def check_whisper_model():
    """Check if WhisperX model can be loaded"""
    try:
        # Set up environment for ffmpeg
        os.environ['PATH'] = '/opt/homebrew/bin:' + os.environ.get('PATH', '')
        
        from transformers import pipeline
        
        # Try to load the model (this will use cached version if available)
        asr = pipeline("automatic-speech-recognition", 
                      "NbAiLab/nb-whisper-medium", 
                      device="mps")  # Use Metal Performance Shaders on Apple Silicon
        
        return True, "WhisperX model loaded successfully"
        
    except Exception as e:
        return False, f"WhisperX model loading failed: {str(e)}"

def check_library_imports():
    """Check if local library can be imported"""
    try:
        from lib import hugintranskriptlib as htl
        
        # Test a few key functions exist
        required_functions = ['transkriber', 'send_email', 'download_blob']
        missing_functions = []
        
        for func_name in required_functions:
            if not hasattr(htl, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            return False, f"Missing functions in library: {', '.join(missing_functions)}"
        
        return True, "Local library imported successfully"
        
    except ImportError as e:
        return False, f"Cannot import local library: {str(e)}"

def main():
    """Run all health checks"""
    logger = setup_logging()
    logger.info("Starting Hugin Transcription Service health check...")
    
    checks = [
        ("Python Version", check_python_version),
        ("Environment Variables", check_environment_variables),
        ("System Dependencies", check_system_dependencies),
        ("Python Dependencies", check_python_imports),
        ("Directory Structure", check_directories),
        ("Local Library", check_library_imports),
        ("WhisperX Model", check_whisper_model),
    ]
    
    all_passed = True
    results = []
    
    for check_name, check_func in checks:
        try:
            passed, message = check_func()
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{status} - {check_name}: {message}")
            results.append((check_name, passed, message))
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            logger.error(f"❌ ERROR - {check_name}: Unexpected error - {str(e)}")
            results.append((check_name, False, f"Unexpected error: {str(e)}"))
            all_passed = False
    
    # Summary
    logger.info("-" * 60)
    if all_passed:
        logger.info("🎉 All health checks passed! Service is ready to run.")
        return 0
    else:
        failed_checks = [name for name, passed, _ in results if not passed]
        logger.error(f"💥 Health check failed. Issues with: {', '.join(failed_checks)}")
        logger.error("Please resolve the above issues before running the service.")
        return 1

if __name__ == "__main__":
    # Load environment variables
    try:
        import dotenv
        dotenv.load_dotenv()
    except ImportError:
        pass  # dotenv not available, environment variables should be set externally
    
    sys.exit(main())