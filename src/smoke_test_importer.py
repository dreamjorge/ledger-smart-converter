import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))
from generic_importer import GenericImporter

def test_initialization():
    rules_path = Path("config/rules.yml")
    print(f"Testing with rules: {rules_path}")
    
    try:
        # Test Santander LikeU
        print("Testing Santander LikeU init...")
        santander = GenericImporter(rules_path, "santander_likeu")
        print(f"SUCCESS: Account={santander.acc_name}, Closing Day={santander.closing_day}")
        
        # Test HSBC
        print("Testing HSBC init...")
        hsbc = GenericImporter(rules_path, "hsbc")
        print(f"SUCCESS: Account={hsbc.acc_name}, Closing Day={hsbc.closing_day}")
        
        print("\nAll initializations successful!")
        return True
    except Exception as e:
        print(f"FAILURE: {e}")
        return False

if __name__ == "__main__":
    if test_initialization():
        sys.exit(0)
    else:
        sys.exit(1)
