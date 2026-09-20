"""Small explicit UI catalog; paths verified against mainspec_v2.json."""
SECTIONS = {
    "applications": ("Applications & REST", "/v2/web-apps", ["Name", "Namespace", "Enabled", "DispatchClass"]),
    "users": ("Users", "/v2/security/users", ["Name", "FullName", "Enabled"]),
    "roles": ("Roles", "/v2/security/roles", ["Name", "Description"]),
    "resources": ("Resources", "/v2/security/resources", ["Name", "Description"]),
    "wallet": ("Wallet collections", "/v2/wallet/collections", ["Name", "Description"]),
    "tasks": ("Tasks", "/v2/tasks", ["Id", "Name", "Namespace", "Suspended", "LastFinished", "NextScheduled"]),
    "processes": ("Processes", "/v2/processes", ["Pid", "Username", "Nspace", "State", "Routine", "ElapsedTime", "CPUTime"]),
    "locks": ("Locks", "/v2/locks", ["Reference", "Pid", "ModeCount", "RoutineInfo", "Directory"]),
    "databases": ("Databases", "/v2/databases", ["Name", "Directory", "Status"]),
    "namespaces": ("Namespace topology", "/v2/namespaces", ["Name", "Globals", "Routines", "TempGlobals"]),
    "task-history": ("Task history", "/v2/task/history", ["Name", "LastStart", "Completed", "Status", "Result", "Pid"]),
}

NAV = {
    "MANAGE": [("applications", "Applications & REST"), ("users", "Permissions"),
               ("wallet", "Security & Secrets"), ("tasks", "Tasks"), ("system", "System"), ("logs", "Logs")],
    "INVESTIGATE": [("processes", "Processes"), ("locks", "Locks")],
    "STORAGE": [("databases", "Databases"), ("namespaces", "Namespace topology")],
}
