import re

with open('frontend/src/components/tabla/DataTable.tsx', 'r') as f:
    dt = f.read()

# Replace manualPagination revert
dt = dt.replace("manualPagination: pageCount !== undefined,", "manualPagination: manualPagination ?? (pageCount !== undefined),")

# Add internal pagination state
dt = re.sub(
    r"const \[sorting, setSorting\] = useState<SortingState>\(\[\]\);",
    "const [sorting, setSorting] = useState<SortingState>([]);\n  const [internalPagination, setInternalPagination] = useState({ pageIndex: 0, pageSize: 10 });",
    dt
)

# Replace state and onPaginationChange
dt = re.sub(
    r"    onPaginationChange,\n    state: \{\n      sorting,\n      \.\.\.\(pagination \? \{ pagination \} : \{\}\),\n    \},",
    "    onPaginationChange: onPaginationChange ?? setInternalPagination,\n    state: {\n      sorting,\n      pagination: pagination ?? internalPagination,\n    },",
    dt
)

with open('frontend/src/components/tabla/DataTable.tsx', 'w') as f:
    f.write(dt)

