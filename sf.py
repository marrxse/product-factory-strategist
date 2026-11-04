#!/usr/bin/env python3
"""Стратег Фабрики продуктов — точка входа CLI. Справка: python3 sf.py --help"""
import sys

from sflib.cli import main

if __name__ == "__main__":
    sys.exit(main())
