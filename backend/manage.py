#!/usr/bin/env python
import os
import sys

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "educheck_project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
