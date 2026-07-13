import re

with open('frontend/src/store/auth.test.ts', 'r') as f:
    content = f.read()

if '@vitest-environment jsdom' not in content:
    content = '/**\n * @vitest-environment jsdom\n */\n' + content
    with open('frontend/src/store/auth.test.ts', 'w') as f:
        f.write(content)

