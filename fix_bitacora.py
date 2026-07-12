import re

with open('Docs/bitacora-agente.md', 'r') as f:
    b = f.read()

t38_note = "\n- **Fix retroactivo de estado de paginación (DataTable):** Se corrigió un bug silencioso donde el paso parcial del objeto `state: { sorting }` sobreescribía la paginación interna (client-side) forzándola siempre a la página 1. Se implementó un estado local `internalPagination` como fallback para garantizar que la tabla funcione correctamente de manera autónoma cuando no recibe props de paginación desde el servidor."

# find ## T-38
if '## T-38' in b:
    start_idx = b.find('## T-38')
    decisiones_idx = b.find('### Decisiones tomadas', start_idx)
    insert_idx = decisiones_idx + len('### Decisiones tomadas')
    b = b[:insert_idx] + t38_note + b[insert_idx:]
    with open('Docs/bitacora-agente.md', 'w') as f:
        f.write(b)
