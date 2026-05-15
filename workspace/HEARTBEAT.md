# HEARTBEAT

**Autonomous Control Loop**

WarungFlow uses a while-loop orchestrator that continuously evaluates the state of its task until completion, failure, or until `max_steps` is reached.

The loop sequence follows:
1. Observe current state.
2. Decide next required action.
3. Call the correct tool.
4. Update state.
5. Log the tool call in the execution trace.
6. Validate progress.
7. Continue until task is complete.

We enforce a `max_steps = 20` threshold to prevent infinite loops. The heartbeat stops when all reports are exported or critical data is missing.
