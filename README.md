# Tiltmeter GitHub Action

Run [Tiltmeter](https://github.com/tiltmeter-dev/tiltmeter) on a schedule and fail the job
when a third-party API your code or AI agents depend on changes shape: a renamed field, a
number that became a string, a value that started arriving as `null`.

The action installs Tiltmeter, keeps the baseline in the Actions cache between runs, writes
a table of changes to the job summary and fails the step according to `fail-on`.

## Usage

Put a [`tiltmeter.yaml`](https://github.com/tiltmeter-dev/tiltmeter/blob/main/docs/configuration.md)
in your repository and add `.github/workflows/api-drift.yml`:

```yaml
name: API drift

on:
  schedule:
    - cron: "17 * * * *"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  tiltmeter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
      - uses: tiltmeter-dev/tiltmeter-action@v1
        env:
          # Every ${VAR} in tiltmeter.yaml needs a matching variable here.
          STRIPE_API_KEY: ${{ secrets.STRIPE_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }} # optional, for explanations
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }} # optional, for alerts
```

The first run records a baseline. Later runs report each change once, then fold it into
the baseline.

## Inputs

| Input | Default | Description |
|---|---|---|
| `config` | `tiltmeter.yaml` | Path to the config file, relative to the workspace. |
| `endpoints` | all | Endpoint ids to check, separated by spaces or new lines. |
| `version` | `0.3.0` | Tiltmeter version from PyPI. |
| `fail-on` | `warning` | `warning` fails on warning or breaking drift and on checks that could not run. `breaking` fails only on breaking drift. `never` only reports. A broken config always fails. |
| `explain` | `true` | Ask Claude to explain drift. Needs `ANTHROPIC_API_KEY`; without it the check runs without explanations. |
| `notify` | `true` | Send the Slack and webhook notifications declared in the config. |
| `cache` | `true` | Keep the baseline in the Actions cache. Without it nothing is ever reported. |
| `cache-key` | `tiltmeter` | Cache key prefix. Change it when one job checks several independent configs. |
| `summary` | `true` | Write the results to the job summary. |

## Outputs

| Output | Description |
|---|---|
| `exit-code` | `0` clean, `1` warning, `2` breaking, `3` a check could not run, `4` configuration error. |
| `result` | `clean`, `warning`, `breaking`, `failed` or `error`. |
| `json` | Path to the JSON results, one check result per endpoint. |

Use them to react in later steps, for example to open an issue on breaking drift:

```yaml
      - uses: tiltmeter-dev/tiltmeter-action@v1
        id: drift
        with:
          fail-on: never
      - if: steps.drift.outputs.result == 'breaking'
        run: gh issue create --title "Breaking API drift" --body "Details: $RUN_URL"
        env:
          GH_TOKEN: ${{ github.token }}
          RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

## Notes

- **Pin it.** `@v1` follows compatible releases. For a fixed version, use a full commit
  SHA, and set `version` to the Tiltmeter release you reviewed.
- **Runners.** Works on Linux, macOS and Windows runners. It uses
  [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv) and
  [`actions/cache`](https://github.com/actions/cache), both pinned by commit SHA.
- **Secrets.** Credentials are passed through `env` and expanded by Tiltmeter at request
  time. They are never written to the cache, the summary or the logs. The cache holds only
  response shapes.
- **Schedules.** GitHub runs `cron` in UTC and can delay busy hours; avoid minute `0`.

## License

[MIT](LICENSE)
