# SonarQube SAST PoC with GitHub Actions

This proof of concept runs SonarQube Community Build in Docker, analyzes a small
Python/Flask service, and executes the scan from GitHub Actions.

The SonarQube project token is stored as the GitHub repository secret
`SONAR_TOKEN`. Container-image scanning is outside this PoC; use a separate
Trivy workflow for that purpose.

## What this PoC validates

| Area | Validation |
| --- | --- |
| Application tests | The Flask API returns the expected health, quote, and validation responses |
| SAST detection | SonarQube reports deliberately seeded Flask and Django security problems |
| CI integration | Tests and source analysis run automatically in GitHub Actions |
| Quality Gate | The workflow records or enforces the SonarQube Quality Gate |
| Performance | Scan and gate durations are measured from the GitHub Actions run |

The directories have different purposes:

- `tests/` contains normal pytest functional tests.
- `sast-fixtures/` contains deliberately vulnerable examples that SonarQube
  must analyze. Do not import or deploy these files.

## Pipeline flow

```text
Pull request
  -> pytest

Push or merge to main / manual workflow
  -> pytest and coverage.xml
  -> read SONAR_TOKEN from GitHub Secrets
  -> submit source analysis to SonarQube
  -> check the Quality Gate
```

## Repository structure

| Path | Purpose |
| --- | --- |
| `app/`, `run.py` | Sample Flask API |
| `tests/` | Functional tests |
| `sast-fixtures/` | Deliberately vulnerable Flask and Django code |
| `compose.yaml` | Local SonarQube container |
| `sonar-project.properties` | Project key, scan scope, tests, and coverage settings |
| `.github/workflows/backend-sast.yml` | Test, SonarQube scan, and Quality Gate workflow |
| `requirements.txt` | Python dependencies |

## 1. Install prerequisites

Install Python tools:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
```

Install Docker Engine and the Docker Compose plugin using the
[official Docker installation guide](https://docs.docker.com/engine/install/),
then verify them:

```bash
python3 --version
docker --version
docker compose version
```

SonarQube uses Elasticsearch. Configure the host limits before starting it:

```bash
sudo sysctl -w vm.max_map_count=524288
sudo sysctl -w fs.file-max=131072
```

These two settings do not survive a reboot. For a persistent host, add them to
`/etc/sysctl.d/99-sonarqube.conf`. The Compose file already sets
`nofile=131072` and `nproc=8192` for the container.

## 2. Run the sample application and tests

Create the environment, install dependencies, and run pytest:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
```

Expected result:

```text
8 passed
Required test coverage of 90.0% reached
```

Start the Flask API:

```bash
python run.py
```

In another terminal, test the endpoints:

```bash
curl --fail http://127.0.0.1:5000/health
curl --fail http://127.0.0.1:5000/api/v1/quotes/AAPL
```

## 3. Start and verify SonarQube

Start the container:

```bash
docker compose up -d
docker compose ps
docker compose logs -f sonarqube
```

Wait until SonarQube is operational. Press `Ctrl+C` to stop following the
logs; the container continues running.

Verify the service through its API:

```bash
curl --fail --silent http://localhost:9000/api/system/status |
  python3 -m json.tool
```

The response must contain:

```json
{
  "status": "UP"
}
```

Open `http://localhost:9000` in a browser.

### Administrator credentials

A new SonarQube installation creates this account automatically:

| Field | Initial value |
| --- | --- |
| Username | `admin` |
| Password | `admin` |

Sign in with `admin/admin`. SonarQube then requires a new password. The new
password is selected by the installer and cannot be recovered from Docker or
`compose.yaml`.

If `admin/admin` does not work, the persistent volume probably contains a
password changed during an earlier run. Use that password. If this is disposable
PoC data and the password is lost, reset the instance:

```bash
docker compose down -v
docker compose up -d
```

> `docker compose down -v` permanently removes all local SonarQube projects,
> tokens, settings, and scan history.

The embedded H2 database is appropriate only for this local evaluation. Use a
supported external database, backups, TLS, and monitoring for production.

## 4. Minimal SonarQube project setup

Use this setup when the goal is simply to prove that GitHub Actions can submit
an analysis.

### Create the project

1. Sign in to SonarQube.
2. Select **Projects -> Create Project -> Local Project**.
3. Set the display name to `poc-sonarqube-sast-cicd`.
4. Set the project key to `poc-sonarqube-sast-cicd`.
5. Set the main branch to `main` if requested.
6. Select **Set Up** or **Create Project**.

The project key must match `sonar-project.properties`:

```properties
sonar.projectKey=poc-sonarqube-sast-cicd
```

If a different project key is selected in SonarQube, update the property file
to match it.

### Create a Project Analysis Token

1. Open the avatar menu in SonarQube.
2. Select **My Account -> Security**.
3. Under **Generate Tokens**, enter `poc-sonarqube-sast-cicd`.
4. Select **Project Analysis Token**.
5. Select `poc-sonarqube-sast-cicd`.
6. Choose an expiration date, such as 30 days for the PoC.
7. Select **Generate** and copy the value immediately.

Do not use the administrator password or a global administrator token in CI. If
the token is lost, revoke it and generate a replacement.

### Validate the token

Run this on the host before configuring GitHub:

```bash
export SONAR_HOST_URL=http://localhost:9000
read -rsp "SONAR_TOKEN: " SONAR_TOKEN
echo
curl --fail --silent   --user "$SONAR_TOKEN:"   "$SONAR_HOST_URL/api/authentication/validate"
unset SONAR_TOKEN
```

Expected response:

```json
{"valid":true}
```

A `valid:false` response means the token is incorrect, expired, or revoked.

## 5. Configure GitHub Actions

The repository must exist on GitHub. If it has not been created and GitHub CLI
is authenticated:

```bash
gh auth login
gh repo create poc-sonarqube-sast-cicd --private --source=. --remote=origin --push
```

Open the repository and go to
**Settings -> Secrets and variables -> Actions**.

### Add the repository secret

Under **Secrets**, select **New repository secret**:

| Name | Value |
| --- | --- |
| `SONAR_TOKEN` | The SonarQube Project Analysis Token |

### Add repository variables

Under **Variables**, select **New repository variable** for each value:

| Name | Value |
| --- | --- |
| `SONAR_HOST_URL` | A SonarQube URL reachable from the SAST runner |
| `SONAR_ENFORCE_GATE` | `false` for initial tuning, then `true` |
| `SAST_RUNNER` | `self-hosted` when SonarQube is available only on the local network |

When SonarQube and the runner are on the same machine:

```text
SONAR_HOST_URL=http://localhost:9000
SAST_RUNNER=self-hosted
SONAR_ENFORCE_GATE=false
```

A GitHub-hosted runner cannot reach `localhost:9000` on a personal machine.
Either use a self-hosted runner on the same network or provide a secured,
reachable SonarQube URL. If `SAST_RUNNER` is not set, the workflow uses the
actual GitHub runner label `ubuntu-latest`.

### Add a self-hosted runner when SonarQube is local

1. Open **Settings -> Actions -> Runners** in the repository.
2. Select **New self-hosted runner**.
3. Select **Linux** and the host architecture, normally **x64**.
4. Run the download and configuration commands displayed by GitHub.
5. Start it with `./run.sh` or install it as a service.
6. Confirm that the runner is **Idle/Online**.
7. Set the repository variable `SAST_RUNNER=self-hosted`.

Never commit the runner registration token.

### Workflow behavior

The existing `.github/workflows/backend-sast.yml`:

1. Runs pytest and creates `coverage.xml`.
2. Checks out the full Git history for the SAST job.
3. Reads `secrets.SONAR_TOKEN` and `vars.SONAR_HOST_URL`.
4. Runs `SonarSource/sonarqube-scan-action`.
5. Polls the SonarQube Quality Gate.
6. Treats a red gate as advisory while `SONAR_ENFORCE_GATE=false`.
7. Fails the job on a red gate when `SONAR_ENFORCE_GATE=true`.

## 6. Optional GitHub App integration

A GitHub App is not required for the scanner workflow above. Configure one only
when SonarQube must import GitHub repositories or users must sign in to
SonarQube through GitHub.

The GitHub App does not replace `SONAR_TOKEN`; the workflow still needs a
Project Analysis Token.

Use a stable SonarQube Base URL for this integration. A real shared deployment
should use HTTPS, for example `https://sonarqube.example.com`.

### Set the SonarQube Base URL

1. Open **Administration -> Configuration -> General Settings**.
2. Open **General -> General**.
3. Set **Server base URL** to the URL used to access SonarQube.
4. Save the configuration.

### Create the GitHub App

1. Open GitHub **Settings -> Developer settings -> GitHub Apps**.
2. Select **New GitHub App**.
3. Enter a unique name such as `sonarqube-poc-<github-user>`.
4. Set **Homepage URL** to the SonarQube Base URL.
5. Set **Callback URL** to the SonarQube Base URL.
6. Clear **Webhook Active**, Webhook URL, and Webhook secret.
7. Configure these permissions.

Repository permissions:

| Permission | Access |
| --- | --- |
| Checks | Read and write |
| Contents | Read-only |
| Metadata | Read-only; GitHub enables it automatically |

Organization permissions:

| Permission | Access |
| --- | --- |
| Members | Read-only |
| Projects | Read-only |

Only when GitHub sign-in or automatic provisioning is required:

| Permission | Access |
| --- | --- |
| Account -> Email addresses | Read-only |
| Repository -> Administration | Read-only when required for provisioning |
| Organization -> Administration | Read-only when required for provisioning |

After creating the App:

1. Record the **App ID** and **Client ID**.
2. Generate and securely retain a **Client Secret**.
3. Generate and download a private key in PEM format.
4. Never commit the Client Secret or PEM file.

### Install the App

1. Open the GitHub App.
2. Select **Install App**.
3. Choose the account or organization containing the repository.
4. Select **Only select repositories**.
5. Select `poc-sonarqube-sast-cicd`.
6. Confirm the installation.

### Register the App in SonarQube

Sign in to SonarQube as an administrator:

1. Open **Administration -> Configuration -> General Settings**.
2. Open **DevOps Platform Integrations -> GitHub**.
3. Select **Create configuration**.
4. Enter:

| Field | Value |
| --- | --- |
| Configuration name | `github-poc` |
| GitHub API URL | `https://api.github.com/` |
| GitHub App ID | The App ID |
| Client ID | The Client ID |
| Client Secret | The generated Client Secret |
| Private Key | The complete PEM file contents |

5. Save the configuration.
6. Run **Test configuration** if the option is available.

### Import the repository

1. Open **Projects -> Create Project -> From GitHub**.
2. Select `github-poc`.
3. Select `poc-sonarqube-sast-cicd`.
4. Import the repository.
5. Note the project key created by SonarQube.
6. Update `sonar.projectKey` when the imported key differs from
   `poc-sonarqube-sast-cicd`.
7. Generate a Project Analysis Token for the imported project.

## 7. Webhook configuration

Three different mechanisms are commonly confused.

### GitHub Actions events

Do not create a webhook manually. GitHub automatically triggers the workflow
from the `push`, `pull_request`, and `workflow_dispatch` definitions in the
workflow file.

### GitHub App webhook

Keep the GitHub App webhook disabled for the repository-import and sign-in
configuration described above. It is not required to start the scanner.

Only enable it when the installed SonarQube edition and GitHub plan support
GitHub Code Scanning alert synchronization. That optional configuration uses:

```text
https://<sonarqube-host>/api/alm_integrations/webhook_github
```

It also requires:

- A strong webhook secret.
- **Code scanning alerts: Read and write** repository permission.
- Subscription to the **Code scanning alert** event.
- The same webhook secret in the SonarQube GitHub configuration.
- A public HTTPS SonarQube endpoint reachable by GitHub.

Enabling this webhook alone does not execute a scan or add unsupported pull
request features.

### SonarQube outgoing project webhook

This webhook notifies another system after an analysis completes. The current
GitHub Actions Quality Gate step polls SonarQube, so it does not need this
webhook.

To test an outgoing callback to an endpoint you control:

1. Open the SonarQube project.
2. Select **Project Settings -> Webhooks -> Create**.
3. Name it `poc-analysis-complete`.
4. Enter an HTTPS endpoint that accepts POST JSON.
5. Enter a random secret for HMAC verification.
6. Run an analysis.
7. Return to **Webhooks** and inspect the latest delivery.

Do not enter the GitHub repository URL here; a repository page is not a webhook
receiver.

## 8. Configure the Quality Profile and Quality Gate

### Quality Profile

1. Open **Quality Profiles -> Python**.
2. Use `Sonar way` for the first scan.
3. If tuning is required, copy it to `PoC Python SAST`.
4. Assign the profile to the project.
5. Review Python security rules and rules relevant to Flask and Django.
6. Focus triage on:
   - Blocker and High issues in MQR mode.
   - Blocker and Critical issues in Standard Experience mode.

### Quality Gate

1. Open **Quality Gates -> Create**.
2. Name it `PoC SAST Gate`.
3. Add new-code conditions, at minimum:
   - Security Rating must be A.
   - Security Hotspots Reviewed must be 100%.
4. Assign the gate to the PoC project.

The seeded vulnerable files may make the first gate red. Keep
`SONAR_ENFORCE_GATE=false` while validating and tuning the rules. Change it to
`true` after the baseline is accepted.

## 9. Run and verify the workflow

The included workflow runs on:

- A push to `main`.
- A pull request targeting `main`; the current PoC runs pytest only.
- A manual **Run workflow** request.

Verification sequence:

1. Open **Actions -> Backend CI and SonarQube SAST**.
2. Confirm that **Backend tests** passes.
3. On a push to `main`, confirm that **SonarQube SAST** starts.
4. Confirm that **Submit SonarQube analysis** succeeds.
5. Inspect **Check SonarQube quality gate**.
6. Open the SonarQube project and inspect **Activity** for the new analysis.
7. Open **Issues** and filter by the selected gate severities.

Expected seeded cases:

| File | Deliberate issue |
| --- | --- |
| `flask_insecure.py` | SQL injection |
| `flask_insecure.py` | Command injection through `shell=True` |
| `flask_insecure.py` | Path traversal |
| `flask_insecure.py` | Hard-coded secret and debug mode |
| `django_insecure.py` | SQL injection |
| `django_insecure.py` | CSRF exemption and unsafe HTML |

Rule keys and severities may vary with the analyzer version and active profile.

## 10. Record the PoC results

Run at least five representative scans:

| Metric | Proposed acceptance criterion |
| --- | --- |
| Successful scans | Five consecutive runs |
| Warm scan median | No more than three minutes |
| Critical injection seeds | No missed applicable cases |
| False positives | Less than 20% of reviewed severe findings |
| Quality Gate enforcement | Unsafe code fails when enforcement is enabled |

Precision is calculated as:

```text
true positives / (true positives + false positives)
```

## 11. Troubleshooting

### The initial administrator credentials do not work

The volume contains a changed password. Use the updated password or reset the
disposable PoC with `docker compose down -v`.

### SonarQube does not become UP

```bash
docker compose ps
docker compose logs --tail=200 sonarqube
sysctl vm.max_map_count
sysctl fs.file-max
```

### Token validation returns valid:false

Generate a new Project Analysis Token and confirm that it belongs to the correct
project and has not expired.

### GitHub Actions cannot reach localhost

Use a self-hosted runner on the same host/network, or provide a secured
SonarQube URL reachable by the GitHub-hosted runner.

### The scanner reports missing blame information

The SAST checkout must use `fetch-depth: 0`. The included workflow already
configures it.

### The first Quality Gate is red

This is expected because `sast-fixtures/` contains deliberate vulnerabilities.
Keep `SONAR_ENFORCE_GATE=false` during the detection test.

## 12. Stop or reset SonarQube

Stop the container while preserving data:

```bash
docker compose down
```

Delete all local PoC data:

```bash
docker compose down -v
```

## Official references

- [Run SonarQube Community Build with Docker](https://docs.sonarsource.com/sonarqube-community-build/server-installation/from-docker-image/set-up-and-start-container)
- [Host requirements](https://docs.sonarsource.com/sonarqube-community-build/server-installation/pre-installation/linux)
- [Default administrator account](https://docs.sonarsource.com/sonarqube-community-build/instance-administration/user-management/introduction)
- [Manage analysis tokens](https://docs.sonarsource.com/sonarqube-community-build/user-guide/managing-tokens)
- [Configure a GitHub App](https://docs.sonarsource.com/sonarqube-community-build/devops-platform-integration/github-integration/setting-up-at-global-level/setting-up-github-app)
- [Add analysis to GitHub Actions](https://docs.sonarsource.com/sonarqube-community-build/devops-platform-integration/github-integration/adding-analysis-to-github-actions-workflow)
- [Configure SonarQube webhooks](https://docs.sonarsource.com/sonarqube-community-build/project-administration/webhooks)
