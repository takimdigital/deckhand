# EDGE_CASE_REGISTRY: acquisition

| category | exists(Y/N) | screen(s) | dead_ends(Y/N) | finding_tag |
|---|---|---|---|---|
| empty | N | booking-form starts empty by design | N | - |
| error | Y | booking-form send failure | N | - |
| loading_latency | Y | booking-form send spinner | N | - |
| permission_role | N | not_applicable: no accounts at lean depth | N | - |
| boundary | N | not_applicable: no quotas or limits | N | - |
| interruption | Y | booking-form back button keeps values | N | - |
| state_conflict | N | not_applicable: no accounts or sessions | N | - |
| device_context | Y | mobile-first layouts per brief | N | - |
| unhappy_path | N | not_applicable: no payments or refunds yet | N | - |
| lifecycle | N | not_applicable: no returning-user state | N | - |
| ai_agent | N | not_applicable: local service, no agent traffic expected | N | - |
