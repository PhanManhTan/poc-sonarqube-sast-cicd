# SonarQube Cloud SAST PoC with GitHub Actions

This proof of concept validates SonarQube Cloud as a SAST tool in a small Flask backend pipeline.

## Pipeline flow

```text
Push or pull request
        |
        v
GitHub-hosted runner (ubuntu-latest)
        |
        +-- Run pytest and create coverage.xml
        |
        +-- Run the SonarQube scanner
        |
        v
SonarQube Cloud analyzes the uploaded report
        |
        v
Quality Gate is shown in SonarQube Cloud and controls the workflow result
```

SonarQube Cloud is hosted by SonarSource. This setup does not need Docker, a database, a self-hosted runner, `SONAR_HOST_URL`, Vault, or a manually configured webhook.

## What the PoC measures

- Whether push and pull-request scans complete successfully.
- Whether the scanner finds actionable Flask, Django, and Python security issues.
- False positives found while reviewing the results.
- Test, scan, and total workflow duration.
- Whether developers can understand the issue location, explanation, remediation, and Quality Gate result.

The files under `sast-fixtures/` intentionally contain insecure examples. They are included only to confirm that the scanner detects known problems and may cause the Quality Gate to fail.

## Repository contents

```text
.github/workflows/backend-sast.yml  GitHub Actions workflow
app/                                Sample Flask backend
tests/                              Pytest tests
sast-fixtures/                      Deliberately insecure scan fixtures
sonar-project.properties            Analysis scope and coverage settings
```

## 1. Run the application and tests locally

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run the tests and generate the same coverage report used by CI:

```bash
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
```

Run the sample API:

```bash
python run.py
```

The API is available at `http://127.0.0.1:5000`.

## 2. Create the SonarQube Cloud project

1. Sign in to [SonarQube Cloud](https://sonarcloud.io/) with GitHub.
2. Import `PhanManhTan/poc-sonarqube-sast-cicd` from the GitHub organization or account.
3. Select CI-based analysis with GitHub Actions.
4. Open **Administration > Analysis Method** and disable **Automatic Analysis**. This repository sends its analysis and coverage from GitHub Actions, so both methods must not run together.
5. Copy the organization key and project key shown by SonarQube Cloud.

Importing the repository binds the SonarQube Cloud project to GitHub. GitHub Actions supplies the trigger, and SonarQube Cloud handles analysis results and pull-request decoration. No custom webhook is required.

## 3. Create the analysis token

In SonarQube Cloud, open **My Account > Security**, generate a token for analysis, and copy it immediately.

In GitHub, open **Settings > Secrets and variables > Actions > Secrets** and add:

| Secret | Value |
| --- | --- |
| `SONAR_TOKEN` | The token generated in SonarQube Cloud |

Do not commit the token to this repository.

## 4. Add the project variables

In GitHub, open **Settings > Secrets and variables > Actions > Variables** and add:

| Variable | Value |
| --- | --- |
| `SONAR_ORGANIZATION` | The exact SonarQube Cloud organization key |
| `SONAR_PROJECT_KEY` | The exact SonarQube Cloud project key |

Remove old local-server variables if they exist:

- `SONAR_HOST_URL`
- `SAST_RUNNER`
- `SONAR_ENFORCE_GATE`

The workflow always uses a GitHub-hosted `ubuntu-latest` runner and the SonarQube Cloud endpoint.

## 5. Configure rules and the Quality Gate

Start with the built-in Python profile. For PoC-specific tuning:

1. Copy the built-in Python Quality Profile so it can be edited.
2. Review security rules with Flask and Django tags or search terms.
3. Activate the relevant high-severity rules and assign the profile to this project.
4. Use the default Quality Gate first, then copy it only if the PoC needs different thresholds.

The workflow sets `sonar.qualitygate.wait=true`, so it waits up to five minutes for the result. A failed Quality Gate makes the SAST job fail while the detailed findings remain available in SonarQube Cloud.

## 6. Run and verify

The workflow runs on:

- Pushes to `main`.
- Pull requests targeting `main`.
- Manual runs from **Actions > Backend CI and SonarQube Cloud SAST > Run workflow**.

Verify the following after a run:

1. `Backend tests` passes and uploads `coverage.xml`.
2. `SonarQube Cloud SAST` uploads the analysis.
3. The SonarQube Cloud project shows the branch or pull request, findings, coverage, and Quality Gate.
4. The GitHub job passes or fails with the same Quality Gate result.

For pull requests from forks, GitHub does not expose `SONAR_TOKEN`; the workflow therefore runs the tests but skips the SAST job.

## 7. Record the results

Use several representative commits and pull requests, then record:

| Run | Trigger | Tests | Scan time | Total time | Findings | False positives | Quality Gate |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Push |  |  |  |  |  |  |
| 2 | Pull request |  |  |  |  |  |  |
| 3 | Tuned rules |  |  |  |  |  |  |

The PoC is successful when scans run reliably, results are actionable, false positives are manageable, and the pipeline duration remains acceptable.

## Troubleshooting

### The scanner tries to connect to `localhost:9000`

Delete the GitHub variable `SONAR_HOST_URL`. SonarQube Cloud does not run on the GitHub runner.

### The job waits for a self-hosted runner

Delete `SAST_RUNNER` and use the workflow from this repository, which explicitly uses `ubuntu-latest`.

### The scanner reports an invalid project or organization

Copy `SONAR_PROJECT_KEY` and `SONAR_ORGANIZATION` exactly from the SonarQube Cloud project. They are keys, not display names.

### The token is rejected

Generate a new SonarQube Cloud token and replace the `SONAR_TOKEN` GitHub secret. Do not add quotes or whitespace.

### The Quality Gate fails on the first run

Review the issues under `sast-fixtures/`. The repository deliberately contains insecure examples, so a red gate can be an expected PoC result.

## References

- [SonarQube Cloud: GitHub onboarding](https://docs.sonarsource.com/sonarqube-cloud/getting-started/github)
- [SonarQube Cloud: GitHub Actions analysis](https://docs.sonarsource.com/sonarqube-cloud/advanced-setup/ci-based-analysis/github-actions-for-sonarcloud)
- [SonarQube Cloud: Quality Gates](https://docs.sonarsource.com/sonarqube-cloud/standards/quality-gates)
