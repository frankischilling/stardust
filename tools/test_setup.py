"""
Setup Test Script
Verifies that all dependencies are installed and basic functionality works.
Run this before using the bot to ensure everything is configured correctly.
"""
import sys

def test_imports():
    """Test that all required packages can be imported"""
    print("Testing imports...")
    try:
        import cv2
        print("✓ OpenCV imported successfully")
    except ImportError:
        print("✗ OpenCV not found. Run: pip install opencv-python")
        return False
    
    try:
        import numpy
        print("✓ NumPy imported successfully")
    except ImportError:
        print("✗ NumPy not found. Run: pip install numpy")
        return False
    
    try:
        import pyautogui
        print("✓ PyAutoGUI imported successfully")
    except ImportError:
        print("✗ PyAutoGUI not found. Run: pip install pyautogui")
        return False
    
    try:
        import mss
        print("✓ MSS imported successfully")
    except ImportError:
        print("✗ MSS not found. Run: pip install mss")
        return False
    
    return True

def test_screen_capture():
    """Test that screen capture works"""
    print("\nTesting screen capture...")
    try:
        import mss
        import numpy as np
        
        with mss.mss() as sct:
            # Capture a small area
            monitor = {"top": 0, "left": 0, "width": 100, "height": 100}
            screen_img = np.array(sct.grab(monitor))
            print(f"✓ Screen capture works (captured {screen_img.shape})")
        return True
    except Exception as e:
        print(f"✗ Screen capture failed: {e}")
        return False

def test_bot_utils():
    """Test that bot_utils module can be imported"""
    print("\nTesting bot_utils module...")
    try:
        import sys
        import os
        # Add scripts directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
        import bot_utils
        print("✓ bot_utils imported successfully")
        print(f"  - find_image function: {hasattr(bot_utils, 'find_image')}")
        print(f"  - find_color function: {hasattr(bot_utils, 'find_color')}")
        print(f"  - human_like_move function: {hasattr(bot_utils, 'human_like_move')}")
        return True
    except Exception as e:
        print(f"✗ bot_utils import failed: {e}")
        return False

def test_templates_directory():
    """Check if templates directory exists"""
    print("\nTesting templates directory...")
    import os
    if os.path.exists("templates"):
        print("✓ Templates directory exists")
        return True
    else:
        print("✗ Templates directory not found. Creating it...")
        os.makedirs("templates")
        print("✓ Created templates directory")
        return True

def main():
    print("=" * 60)
    print("Bot Setup Test")
    print("=" * 60)
    print()
    
    all_passed = True
    all_passed &= test_imports()
    all_passed &= test_screen_capture()
    all_passed &= test_bot_utils()
    all_passed &= test_templates_directory()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed! Your setup looks good.")
        print("\nNext steps:")
        print("1. Run: python calibrate_game_area.py")
        print("2. Run: python color_picker.py")
        print("3. Create template images in templates/ directory")
        print("4. Configure woodcutter.py with your values")
        print("5. Run: python woodcutter.py")
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()

