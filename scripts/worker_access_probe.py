"""Run with the worker identity using irispython, never with deployment grants."""

import iris

assert iris.execute("return $username") == "AgenticWorker"
assert (
    int(
        next(
            iter(
                iris.sql.exec(
                    "SELECT COUNT(*) FROM Agentic.AI_SCHEMA_MIGRATION WHERE Outcome = ?",
                    "SUCCEEDED",
                )
            )
        )[0]
    )
    >= 1
)
try:
    list(iris.sql.exec("SELECT TOP 1 ID FROM Agentic.AI_AGENT"))
except Exception as error:
    assert getattr(error, "sqlcode", None) in (-99, -98), type(error).__name__
else:
    raise AssertionError("Worker has unexpected access to agent definitions")
print("WORKER_ACCESS_OK native identity, bound SQL, unrelated table denied")
