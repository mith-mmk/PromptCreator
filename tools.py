#!/usr/bin/env python
import importlib
import sys
args = sys.argv
tool = args[1]
print(args[1])
sys.argv = args[1:]
importlib.import_module(f"tools.{tool}")
