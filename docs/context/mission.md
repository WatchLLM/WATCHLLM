# Mission

WatchLLM exists to prevent unsafe code from reaching disk during the write path,
especially when code is produced at machine speed by autonomous agents or
under rapid human iteration.

Without deterministic pre-write governance, unsafe patterns such as hardcoded
credentials, boundary violations, and missing auth checks can be introduced
faster than teams can review or remediate. This creates a high-leverage failure
mode where one bad save can propagate quickly through build and deployment paths.

The core product thesis is local write-path governance: a deterministic kernel
that evaluates code structure before save completion and returns a clear allow or
block decision. Post-hoc scanning alone is not enough for this threat profile.

AST-based enforcement is required because code safety is contextual. The same
text fragment can be harmless in one location and dangerous in another.
Structural analysis enables deterministic distinction between safe retrieval and
unsafe assignment, between allowed module boundaries and direct internal access.
