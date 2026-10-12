# CloudNotes operations readiness lab

Repair a local production-readiness setup in 30–40 minutes after cloning. Exactly three configuration faults are planted. Application and checker code are correct; repair configuration only.

## Start

Fork https://github.com/kalviumcommunity/cloudnotes-ops-readiness-lab.git on GitHub, then clone your fork:

```bash
git clone https://github.com/<your-username>/cloudnotes-ops-readiness-lab.git
cd cloudnotes-ops-readiness-lab
git switch -c fix/cloudnotes-ops-readiness
```

Python 3 standard library only. No Docker, Prometheus, Grafana, paid cloud, credentials, or package install during the timer. GitHub access is needed only for repository setup and submission, not local checks.

## Application contract

Each checker command starts the application at `127.0.0.1:8765` and stops it when finished. Leave this port available. No separate server command is needed.

- `GET /health`: HTTP 200, JSON with `status: ok` and `service: cloudnotes-api`.
- `GET /metrics`: HTTP 200, Prometheus text with these sample lines:

  ```text
  cloudnotes_requests_total 1000
  cloudnotes_errors_total 20
  cloudnotes_request_latency_seconds 0.084
  cloudnotes_saturation_ratio 0.41
  ```

- Availability objective: `99.0` percent. Allowed errors are 1 percent of 1000 requests. Remaining budget is allowed errors minus observed errors. A negative budget is intended evidence, not another fault.
- `GET /logs`: JSON records with `timestamp`, `level`, `service`, and `msg`. Service is `cloudnotes-api`; at least one record has `level` equal to `ERROR`.
- Unknown paths return HTTP 404.
- Acknowledged notes: `n1`, `n2`, `n3`. Backup artifact: `data/notes-backup/notes.json`. `write_backup(directory)` writes `notes.json` only inside its supplied directory. Recovery checks restore the saved JSON and verify all acknowledged notes.
- Leave recovery values unchanged: `rpo_minutes: 0` and `rto_seconds: 10`. These are exercise recovery targets, not elapsed-time measurements.

## Checks and evidence

Run these commands in order, rerunning after each repair:

```bash
python3 readiness.py signals
python3 readiness.py logs
python3 readiness.py recovery
```

1. **Signals and error budget:** reads `ops/signals.yaml` key `metrics_path`, requests that path, and requires HTTP 200 plus all four signal names. On pass it prints signal samples, `requests=1000`, `errors=20`, `objective_percent=99.0`, `allowed_errors=10`, `error_budget_remaining=-10`, and `TASK1 PASS`.
2. **Structured logs:** reruns signals first. It reads `ops/logging.yaml` key `level_field`, fetches `/logs`, and requires that field to equal `ERROR` on a `cloudnotes-api` record. On pass it prints an ERROR JSON record and `TASK2 PASS`.
3. **Backup and restore:** reruns logs first. It reads `ops/recovery.yaml` key `backup_dir`; the resolved directory must match the application backup contract. It writes and restores the backup, verifies acknowledged note IDs, and prints `rpo_minutes=0`, `rto_seconds=10`, `restored_ids=n1,n2,n3`, and `TASK3 PASS`.

Later checks print `SKIP` until earlier checks print `PASS`: `TASK2 SKIP signals not ready` or `TASK3 SKIP logs not ready`. A failed or skipped check exits with status 1; tool failures exit with status 2. Tool failures go to the instructor and are not extra planted faults.

Record cause, file change, and checker output for each task in `readiness-notes.md`. For Task 1, record all five printed budget numbers, one SLI-versus-SLO sentence, and one negative-budget sentence. For Task 3, write one RPO-versus-RTO sentence using printed values. Commit repairs and notes on `fix/cloudnotes-ops-readiness` and submit your branch URL as directed by your instructor.


