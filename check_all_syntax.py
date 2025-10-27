import os
import py_compile
import sys

errors = []

for root, dirs, files in os.walk('.'):
    # Skip hidden directories and __pycache__
    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                py_compile.compile(filepath, doraise=True)
            except (py_compile.PyCompileError, SyntaxError) as e:
                errors.append({'file': filepath, 'error': str(e)})

print("=== SYNTAX ERRORS FOUND ===\n")
for i, error in enumerate(errors, 1):
    print(f"{i}. {error['file']}")
    print(f"   {error['error']}")
    print()

print(f"Total syntax errors found: {len(errors)}")
