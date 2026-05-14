import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import validate_config
from db.client import test_connection

if __name__ == "__main__":
    print("─" * 40)
    print("PROSPEX — Module 1 DB Test")
    print("─" * 40)

    try:
        validate_config()
    except EnvironmentError as e:
        print(e)
        sys.exit(1)

    success = test_connection()
    sys.exit(0 if success else 1)
