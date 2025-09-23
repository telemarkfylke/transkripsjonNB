#!/usr/bin/env python3
"""
Test script for the MLX-based transkriber function
Tests only the improved transkriber function with audio_king.mp3
"""

import os
import sys
import time
from pathlib import Path

# Add the lib directory to the Python path
sys.path.append('./lib')

# Import the transkriber function
from hugintranskriptlib import transkriber

def test_mlx_transkriber():
    """Test the MLX-based transkriber function"""

    print("🇳🇴 MLX Norwegian Transcription Test")
    print("=" * 50)

    # Test file paths
    test_file = "kurs_00.mp3"
    test_path = "./testfiles/"

    # Check if test file exists
    full_path = os.path.join(test_path, test_file)
    if not os.path.exists(full_path):
        print(f"❌ Test file not found: {full_path}")
        return False

    print(f"📁 Test file: {full_path}")
    print(f"📂 Test path: {test_path}")
    print(f"🎵 File name: {test_file}")
    print()

    # Create output directory if it doesn't exist
    os.makedirs("./ferdig_tekst", exist_ok=True)

    try:
        # Start timing
        start_time = time.time()

        print("🚀 Starting MLX transcription...")
        print("-" * 30)

        # Call the transkriber function
        transkriber(test_path, test_file)

        # Calculate total time
        total_time = time.time() - start_time

        print("-" * 30)
        print(f"✅ Transcription completed in {total_time:.2f} seconds")
        print()

        # Check if output files were created
        base_name = test_file.split('.')[0]
        srt_file = f"./ferdig_tekst/{base_name}.srt"
        txt_file = f"./ferdig_tekst/{base_name}.txt"

        print("📋 Output Files:")
        if os.path.exists(srt_file):
            print(f"✅ SRT file created: {srt_file}")
            with open(srt_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()
                print(f"   📏 SRT file size: {len(srt_content)} characters")
        else:
            print(f"❌ SRT file not found: {srt_file}")

        if os.path.exists(txt_file):
            print(f"✅ TXT file created: {txt_file}")
            with open(txt_file, 'r', encoding='utf-8') as f:
                txt_content = f.read()
                print(f"   📏 TXT file size: {len(txt_content)} characters")
                print()
                print("📝 Transcription preview (first 200 characters):")
                print("-" * 40)
                print(txt_content[:200].strip())
                if len(txt_content) > 200:
                    print("...")
                print("-" * 40)
        else:
            print(f"❌ TXT file not found: {txt_file}")

        return True

    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting MLX transkriber test...")
    print()

    success = test_mlx_transkriber()

    print()
    if success:
        print("🎉 Test completed successfully!")
    else:
        print("💥 Test failed!")

    sys.exit(0 if success else 1)