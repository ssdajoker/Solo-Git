import os
import py_compile
import sys

errors = []

for root, dirs, files in os.walk('sologit'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                py_compile.compile(filepath, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"{filepath}: {e}")

for error in errors:
    print(error)

print(f"\nTotal syntax errors found: {len(errors)}")
sys.exit(len(errors))
