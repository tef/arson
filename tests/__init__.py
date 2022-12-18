import os.path
import sys
FILENAME = os.path.normpath(__file__)
PROJECT_ROOT = os.path.split(os.path.dirname(FILENAME))[0]
MODULE_PATH = os.path.join(PROJECT_ROOT, "src")
sys.path.append(MODULE_PATH)
