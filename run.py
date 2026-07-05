#!/usr/bin/env python3
"""
Hedge Fund Holdings Tracker — runner script.

Quick start:
  python run.py --cik 0001067983 --compare       # Berkshire with QoQ
  python run.py --name "Tiger Global" --compare  # search by name
  python run.py --help
"""
import sys
from src.cli import main

if __name__ == "__main__":
    main(sys.argv[1:])
