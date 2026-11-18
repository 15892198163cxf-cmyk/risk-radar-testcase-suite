# OpenViking Historical Bug Dataset

## Contract

`viking://resources/ziniao-online-bugs-governed` is the shared distribution source for normalized Ziniao online-Bug history. The radar does not search it as a second independent Bug corpus. It downloads the governed JSONL into `data/normalized_bugs.jsonl`, validates it, rebuilds the existing derived indexes, and then uses the unchanged local recall and ranking implementation.

This preserves deterministic aliases, scenario routing, cluster recall, age weighting, and regression fixtures while allowing every tester to receive the same Bug archive.

## Three Layers Without Duplication

Each Bug is stored once in `normalized/normalized_bugs.jsonl`.

- `view_memberships` contains `current_182d` when the Bug is in Feishu view `Khmxw2UDR`.
- `view_memberships` contains `historical_view` when the Bug is in Feishu view `ZZdtquUvR`.
- Every JSONL row belongs to the long-term archive even when `view_memberships` is empty.
- `source_view_ids` records the matching view IDs.
- `window_status` remains for backward compatibility and is derived from `current_182d`.

View membership does not replace age ranking. `created_at` remains the freshness authority, and older direct evidence remains eligible.

## Consumer Preflight

Run before the first radar recall in a task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/refresh_openviking_bug_cache.ps1
```

The script:

1. Reads `manifest.json` and the canonical JSONL.
2. Performs a hash no-op when the local mirror is current.
3. Validates schema, record count, unique IDs, membership values, and all three layer counts.
4. Backs up the local mirror and generated scenario/cluster files.
5. Rebuilds scenarios and current-window clusters with the existing code.
6. Runs the existing recall regression suite.
7. Restores the previous cache if rebuilding or regression validation fails.

Remote unavailability, missing credentials, invalid manifests, and invalid datasets produce `local_fallback`; they do not delete or partially update the local cache. Use `-RequireRemote` only for administration or CI where failure must be fatal.

## Publisher

After both Feishu views and details have been refreshed, normalized, rebuilt, and locally validated:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sync_openviking_bugs.ps1
powershell -ExecutionPolicy Bypass -File scripts/verify_openviking_bugs.ps1
```

The publisher writes:

- `manifest.json`: schema, source hash, timestamps, canonical file path, and three-layer counts.
- `normalized/normalized_bugs.jsonl`: exact canonical archive.
- `semantic/normalized/ziniao-online-bugs/`: searchable summaries that retain Bug IDs, memberships, triggers, failures, expected results, fix clues, and evidence.

The verifier must pass exact JSONL bytes, IDs, field values, semantic evidence, snapshot memberships, and manifest counts before synchronization is reported successful.

## Evidence Boundary

- The remote archive and local mirror are the same historical Bug source and count once.
- Accepted business rules and historical testcase atoms remain separate optional OpenViking evidence.
- A Bug proves that a failure happened; it does not by itself define current expected behavior.
- Never write credentials into the skill, dataset, manifest, logs, or radar output.
