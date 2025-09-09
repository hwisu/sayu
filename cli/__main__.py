#!/usr/bin/env python3
"""Sayu CLI entry point for module execution"""

import sys
from .main import cli

if __name__ == "__main__":
    # Support both direct execution and module execution
    cli(prog_name="sayu")