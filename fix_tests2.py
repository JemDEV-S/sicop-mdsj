import re

with open('frontend/src/components/tabla/DataTable.test.tsx', 'r') as f:
    dt_test = f.read()

# Fix the placement of the test
dt_test = re.sub(r"\}\);\s+it\('renderiza el estado de carga", "  it('renderiza el estado de carga", dt_test)
dt_test += "});\n"

with open('frontend/src/components/tabla/DataTable.test.tsx', 'w') as f:
    f.write(dt_test)

# Fix jsdom globally or add pragma
files = [
    'frontend/src/features/auth/RequireAuth.test.tsx',
    'frontend/src/features/auth/RequireRole.test.tsx',
    'frontend/src/app/router.test.tsx',
    'frontend/src/pages/publico/DirectorioProveedores.test.tsx'
]

for file in files:
    try:
        with open(file, 'r') as f:
            content = f.read()
        if '@vitest-environment jsdom' not in content:
            content = '/**\n * @vitest-environment jsdom\n */\n' + content
            with open(file, 'w') as f:
                f.write(content)
    except Exception as e:
        pass

