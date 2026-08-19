# SonarQube Cloud SAST PoC with GitHub Actions

[![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=PhanManhTan_poc-sonarqube-sast-cicd&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=PhanManhTan_poc-sonarqube-sast-cicd)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=PhanManhTan_poc-sonarqube-sast-cicd&metric=bugs)](https://sonarcloud.io/summary/new_code?id=PhanManhTan_poc-sonarqube-sast-cicd)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=PhanManhTan_poc-sonarqube-sast-cicd&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=PhanManhTan_poc-sonarqube-sast-cicd)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=PhanManhTan_poc-sonarqube-sast-cicd&metric=coverage)](https://sonarcloud.io/summary/new_code?id=PhanManhTan_poc-sonarqube-sast-cicd)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=PhanManhTan_poc-sonarqube-sast-cicd&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=PhanManhTan_poc-sonarqube-sast-cicd)

This proof of concept validates SonarQube Cloud (SonarCloud) as a SAST tool in a small Flask backend pipeline.

## Pipeline flow

```text
Push or pull request
        |
        v
GitHub-hosted runner (ubuntu-latest)
        |
        +-- Run pytest and create coverage.xml
        |
        +-- Run SonarQube Cloud Scan (SonarSource/sonarcloud-github-action@v3.1.0)
        |
        v
SonarQube Cloud Dashboard (Quality Gate Evaluation & PR Decoration)
```

## What the PoC measures

- Whether push and pull-request scans complete successfully.
- Whether SonarQube Cloud detects Flask, Django, and Python security issues (OWASP Top 10, CWE).
- Execution time and pipeline impact.
- Enforcement of Quality Gates (blocking PRs with High/Critical findings).

The files under `sast-fixtures/` intentionally contain insecure examples to confirm scanner detection.

## Repository contents

```text
.github/workflows/backend-sast.yml  GitHub Actions workflow running SonarQube Cloud SAST
app/                                Sample Flask backend
tests/                              Pytest tests
sast-fixtures/                      Deliberately insecure scan fixtures
sonar-project.properties            SonarQube configuration file
```

## 1. Run the application and tests locally

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run the tests and generate coverage report:

```bash
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
```

Run the sample API:

```bash
python run.py
```

The API is available at `http://127.0.0.1:5000`.

## 2. Configure SonarQube Cloud & GitHub Secrets / Variables

### Step A: Connect SonarQube Cloud
1. Sign in to [SonarQube Cloud](https://sonarcloud.io/) with your GitHub account.
2. Create a new organization or select your existing organization (`phanmanhtan`).
3. Import the repository `PhanManhTan/poc-sonarqube-sast-cicd`.
4. Turn **OFF** Automatic Analysis (under **Administration > Analysis Method**) so GitHub Actions handles the analysis.

### Step B: GitHub Secrets & Variables Setup
In your GitHub Repository, go to **Settings > Secrets and variables > Actions**:

#### 1. Repository Secrets (**Secrets** tab):
* `SONAR_TOKEN`: Generate an analysis token in SonarCloud (**My Account > Security > Generate Tokens**) and paste it here.

#### 2. Repository Variables (**Variables** tab) - Optional / Recommended:
* `SONAR_ORGANIZATION`: `phanmanhtan`
* `SONAR_PROJECT_KEY`: `PhanManhTan_poc-sonarqube-sast-cicd`

## 3. Run and verify

The workflow runs on:

- Pushes to `main`.
- Pull requests targeting `main`.
- Manual runs from **Actions > Backend CI and SonarQube Cloud SAST > Run workflow**.

Verify the following after a run:

1. `Backend tests` passes and uploads `coverage.xml`.
2. `SonarQube Cloud SAST Scan` executes and submits analysis to SonarCloud.
3. The pipeline waits for Quality Gate (`-Dsonar.qualitygate.wait=true`) and passes/fails accordingly.

## References

- [SonarQube Cloud Documentation](https://docs.sonarsource.com/sonarqube-cloud/)
- [SonarQube Cloud GitHub Action](https://github.com/SonarSource/sonarcloud-github-action)
