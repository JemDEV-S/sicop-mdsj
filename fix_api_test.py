import re

with open('frontend/src/lib/api-client.test.ts', 'r') as f:
    content = f.read()

# Replace string URLs with Regex in mockApi
content = content.replace("mockApi.onGet('/protegido')", "mockApi.onGet(/\\/protegido/)")
# And the global mock
content = content.replace("mockGlobal.onPost('http://localhost:8000/api/v1/auth/refresh')", "mockGlobal.onPost(/\\/auth\\/refresh/)")

with open('frontend/src/lib/api-client.test.ts', 'w') as f:
    f.write(content)

