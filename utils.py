# utils.py
import os
import sys

def resource_path(rel_path):
    """
    Return absolute path to resource, works for dev and for PyInstaller bundle.
    Usage:
        path = resource_path("templates/myfile.txt")
    """
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, rel_path)
