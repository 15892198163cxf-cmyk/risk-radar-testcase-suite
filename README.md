# Risk Radar Testcase Suite

The four sibling folders are Codex skills. Copy them together to your Codex skills directory and reopen Codex. Use `$ziniao-landmine-map` for radar analysis or `$risk-radar-testcase-workflow` for testcase generation and review. Python runs the scripts. PyYAML and openpyxl support YAML and Excel output.

This repository includes a redacted historical defect snapshot at `ziniao-landmine-map/data/normalized_bugs.jsonl`. The original snapshot, generated indexes, benchmark data, and data fixtures are maintained separately.

To build scenario indexes locally, run these commands from the repository root:

```powershell
python ziniao-landmine-map/scripts/landmine.py build-scenarios --source ziniao-landmine-map/data/normalized_bugs.jsonl
python ziniao-landmine-map/scripts/landmine.py radar-search "设备回收站"
```
