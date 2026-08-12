# PoC SonarQube SAST trên Ubuntu với GitHub Actions

PoC này chạy SonarQube Community Build bằng Docker, scan source code Python và
chạy tự động từ GitHub Actions.

- Không scan container image; nếu cần hãy tạo workflow Trivy riêng.
- SonarQube Community Build chỉ scan nhánh `main`; pull request vẫn chạy pytest.
- Có hai cách kết nối GitHub:
  - **Cách A — tối giản:** project local + token + GitHub Actions.
  - **Cách B — đầy đủ:** GitHub App + import repository + GitHub Actions.

## 1. PoC kiểm tra gì?

| Phần | Mục đích |
| --- | --- |
| Pytest | Xác nhận Flask API hoạt động đúng |
| SonarQube SAST | Phát hiện code không an toàn trong `sast-fixtures/` |
| GitHub Actions | Xác nhận test và scan tự động chạy trong CI |
| Quality Gate | Xác nhận pipeline cảnh báo hoặc fail khi không đạt chuẩn |
| Thời gian | Đo mức ảnh hưởng của SAST tới pipeline |

`tests/` là test chức năng. `sast-fixtures/` là code cố ý có lỗ hổng, chỉ để
SonarQube scan; không được import hoặc chạy.

## 2. Chuẩn bị Ubuntu

Cài Python:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
```

Cài Docker Engine và Compose plugin theo
[hướng dẫn Docker cho Ubuntu](https://docs.docker.com/engine/install/ubuntu/),
sau đó kiểm tra:

```bash
python3 --version
docker --version
docker compose version
```

SonarQube dùng Elasticsearch. Cấu hình Ubuntu host:

```bash
sudo sysctl -w vm.max_map_count=524288
sudo sysctl -w fs.file-max=131072
```

Hai giá trị trên mất sau khi reboot. Với host dùng lâu dài, lưu chúng trong
`/etc/sysctl.d/99-sonarqube.conf`. `compose.yaml` đã cấu hình
`nofile=131072` và `nproc=8192` cho container.

## 3. Chạy test Flask trên Ubuntu

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
```

Kết quả mong đợi:

```text
8 passed
Required test coverage of 90.0% reached
```

Chạy API:

```bash
python run.py
```

Mở terminal khác:

```bash
curl --fail http://127.0.0.1:5000/health
curl --fail http://127.0.0.1:5000/api/v1/quotes/AAPL
```

## 4. Khởi động và kiểm tra SonarQube

```bash
docker compose up -d
docker compose ps
docker compose logs -f sonarqube
```

Đợi log báo SonarQube hoạt động. Nhấn `Ctrl+C` để thoát phần xem log; container
vẫn tiếp tục chạy.

Kiểm tra trạng thái bằng API:

```bash
curl --fail --silent http://localhost:9000/api/system/status |
  python3 -m json.tool
```

Kết quả phải chứa:

```json
{
  "status": "UP"
}
```

Mở trình duyệt tại `http://localhost:9000`.

## 5. Tài khoản admin và mật khẩu

SonarQube tự tạo tài khoản quản trị trên lần khởi động đầu tiên:

| Trường | Giá trị |
| --- | --- |
| Username | `admin` |
| Password lần đầu | `admin` |

Đăng nhập bằng `admin/admin`, sau đó SonarQube bắt buộc đặt mật khẩu mới.
Mật khẩu mới do người cài đặt tự chọn; không thể đọc lại từ Docker hoặc
`compose.yaml`.

Nếu `admin/admin` không dùng được, volume đang chứa dữ liệu từ lần chạy trước.
Hãy dùng mật khẩu đã đổi. Nếu quên mật khẩu và toàn bộ dữ liệu chỉ là PoC có thể
xóa, reset hoàn toàn:

```bash
docker compose down -v
docker compose up -d
```

> Cảnh báo: `docker compose down -v` xóa toàn bộ project, token, cấu hình và
> lịch sử scan trong volume. Sau khi tạo lại, tài khoản trở về `admin/admin`.

## 6. Cách A — cấu hình tối giản

Dùng cách này khi chỉ cần chứng minh GitHub Actions scan được code.

### 6.1 Tạo project

1. Đăng nhập SonarQube.
2. Chọn **Projects -> Create Project -> Local Project**.
3. Display name: `PoC SAST Flask Backend`.
4. Project key: `poc-sast-flask-backend`.
5. Main branch: `main`, nếu giao diện yêu cầu.
6. Chọn **Set Up/Create Project**.

Project key phải giống trong `sonar-project.properties`:

```properties
sonar.projectKey=poc-sast-flask-backend
```

### 6.2 Tạo token scan

1. Chọn avatar ở góc trên bên phải.
2. Vào **My Account -> Security**.
3. Tại **Generate Tokens**, nhập tên `github-actions-poc`.
4. Type: **Project Analysis Token**.
5. Project: `PoC SAST Flask Backend`.
6. Chọn thời hạn phù hợp, ví dụ 30 ngày cho PoC.
7. Chọn **Generate** và sao chép token ngay.

Nếu mất token, revoke token cũ và tạo token mới. Không dùng mật khẩu admin làm
token CI.

### 6.3 Kiểm tra URL và token trước khi cấu hình GitHub

Trên Ubuntu host:

```bash
export SONAR_HOST_URL=http://localhost:9000
read -rsp "SONAR_TOKEN: " SONAR_TOKEN
echo
curl --fail --silent --user "$SONAR_TOKEN:" "$SONAR_HOST_URL/api/authentication/validate"
unset SONAR_TOKEN
```

Kết quả đúng:

```json
{"valid":true}
```

Nếu nhận `{"valid":false}`, token sai, hết hạn hoặc đã bị revoke.

## 7. Cách B — cấu hình GitHub App đầy đủ

Dùng cách này nếu muốn SonarQube import repository từ GitHub hoặc cho phép người
dùng đăng nhập SonarQube bằng GitHub. GitHub App không thay thế
`SONAR_TOKEN`; workflow vẫn cần Project Analysis Token để scan.

Cấu hình đầy đủ cần một SonarQube Base URL ổn định. Với môi trường kết nối thật,
nên dùng HTTPS, ví dụ `https://sonarqube.example.com`. URL
`http://localhost:9000` chỉ phù hợp để test local.

### 7.1 Đặt Server Base URL trên SonarQube

1. Vào **Administration -> Configuration -> General Settings**.
2. Mở **General -> General**.
3. Đặt **Server base URL** thành URL SonarQube mà người dùng truy cập được.
4. Lưu cấu hình.

### 7.2 Tạo GitHub App

Trên GitHub:

1. Vào **Settings -> Developer settings -> GitHub Apps**.
2. Chọn **New GitHub App**.
3. App name: tên duy nhất, ví dụ `sonarqube-poc-<github-user>`.
4. Homepage URL: SonarQube Base URL.
5. Callback URL: SonarQube Base URL.
6. **Webhook:** bỏ chọn **Active**, xóa Webhook URL và Webhook secret.
7. Chọn các quyền sau.

Repository permissions:

| Permission | Access |
| --- | --- |
| Checks | Read and write |
| Contents | Read-only |
| Metadata | Read-only; GitHub tự bật |

Organization permissions:

| Permission | Access |
| --- | --- |
| Members | Read-only |
| Projects | Read-only |

Chỉ khi dùng GitHub login/provisioning:

| Permission | Access |
| --- | --- |
| Account -> Email addresses | Read-only |
| Repository -> Administration | Read-only nếu cần provisioning |
| Organization -> Administration | Read-only nếu cần provisioning |

Với PoC một tài khoản, giới hạn nơi cài App vào đúng account/repository. Chỉ cho
phép **Any account** nếu thực sự cần dùng App cho nhiều organization.

Sau khi tạo App:

1. Ghi lại **App ID** và **Client ID**.
2. Chọn **Generate a new client secret** và lưu Client Secret.
3. Chọn **Generate a private key** và tải file PEM.
4. Không commit Client Secret hoặc file PEM vào repository.

### 7.3 Cài GitHub App vào repository

1. Mở GitHub App vừa tạo.
2. Chọn **Install App**.
3. Chọn account/organization chứa repository.
4. Chọn **Only select repositories**.
5. Chọn repository `poc-sonarqube-sast-cicd`.
6. Xác nhận cài đặt.

### 7.4 Khai báo GitHub App trong SonarQube

Đăng nhập SonarQube bằng admin:

1. Vào **Administration -> Configuration -> General Settings**.
2. Mở **DevOps Platform Integrations -> GitHub**.
3. Chọn **Create configuration**.
4. Nhập:

| Field | Giá trị |
| --- | --- |
| Configuration name | `github-poc` |
| GitHub API URL | `https://api.github.com/` |
| GitHub App ID | App ID vừa tạo |
| Client ID | Client ID vừa tạo |
| Client Secret | Client Secret vừa tạo |
| Private Key | Toàn bộ nội dung file PEM |

5. Lưu cấu hình.
6. Nếu giao diện có **Test configuration**, chạy test và xác nhận thành công.

### 7.5 Import repository vào SonarQube

1. Vào **Projects -> Create Project -> From GitHub**.
2. Chọn configuration `github-poc`.
3. Chọn repository `poc-sonarqube-sast-cicd`.
4. Import project.
5. Sao chép project key mà SonarQube tạo.
6. Nếu key khác `poc-sast-flask-backend`, cập nhật
   `sonar.projectKey` trong `sonar-project.properties`.
7. Tạo Project Analysis Token cho project đã import.

## 8. Webhook: khi nào cần và cấu hình thế nào?

Có ba khái niệm dễ nhầm:

### 8.1 GitHub push/PR webhook

Không cần tạo thủ công. GitHub Actions tự nhận event `push`,
`pull_request` và `workflow_dispatch` từ file workflow.

### 8.2 GitHub App webhook

Với Community Build và PoC này, để **tắt**. SonarSource khuyến nghị bỏ chọn
Webhook Active và để trống URL/secret khi tạo GitHub App.

Webhook GitHub App chỉ nên bật cho tính năng đồng bộ GitHub Code Scanning
Alerts trên edition hỗ trợ. Khi đó cấu hình là:

```text
https://<sonarqube-host>/api/alm_integrations/webhook_github
```

và cần:

- Webhook secret đủ mạnh.
- Repository permission **Code scanning alerts: Read and write**.
- Subscribe event **Code scanning alert**.
- Nhập cùng webhook secret vào GitHub configuration trên SonarQube.
- GitHub phải truy cập được URL SonarQube qua HTTPS.

Không bật cấu hình này trên Community Build chỉ để chạy GitHub Actions; nó không
làm scanner chạy và không bổ sung PR decoration.

### 8.3 SonarQube project webhook

Đây là webhook từ SonarQube tới một hệ thống nhận callback sau khi analysis hoàn
thành. GitHub Actions workflow hiện tại polling Quality Gate nên không cần
webhook này.

Nếu cần thử callback tới một endpoint do bạn quản lý:

1. Vào project **Project Settings -> Webhooks**.
2. Chọn **Create**.
3. Name: `poc-analysis-complete`.
4. URL: endpoint HTTPS nhận POST JSON.
5. Secret: chuỗi ngẫu nhiên dùng kiểm tra HMAC.
6. Chạy một scan.
7. Quay lại Webhooks để xem trạng thái lần gửi gần nhất.

Không nhập URL repository GitHub vào đây; repository không phải webhook
receiver.

## 9. Cấu hình GitHub Actions

Repository phải tồn tại trên GitHub. Nếu chưa có và GitHub CLI đã đăng nhập:

```bash
gh auth login
gh repo create poc-sonarqube-sast-cicd --private --source=. --remote=origin --push
```

Trong GitHub repository, vào
**Settings -> Secrets and variables -> Actions**.

### 9.1 Repository Secret

Tab **Secrets -> New repository secret**:

| Name | Value |
| --- | --- |
| `SONAR_TOKEN` | Project Analysis Token từ SonarQube |

### 9.2 Repository Variables

Tab **Variables -> New repository variable**:

| Name | Value |
| --- | --- |
| `SONAR_HOST_URL` | URL SonarQube mà runner truy cập được |
| `SONAR_ENFORCE_GATE` | `false` cho lần test đầu |
| `SAST_RUNNER` | `self-hosted` nếu SonarQube chạy local |

Khi SonarQube và runner chạy trên cùng Ubuntu host:

```text
SONAR_HOST_URL=http://localhost:9000
SAST_RUNNER=self-hosted
SONAR_ENFORCE_GATE=false
```

GitHub-hosted runner `ubuntu-latest` không truy cập được
`localhost:9000` trên máy cá nhân. Nếu muốn dùng `ubuntu-latest`,
SonarQube phải có URL HTTPS mà runner trên Internet truy cập được.

### 9.3 Cài self-hosted runner trên Ubuntu

1. Vào repository **Settings -> Actions -> Runners**.
2. Chọn **New self-hosted runner**.
3. Chọn **Linux** và **x64**.
4. Chạy đúng các lệnh tải/configure do GitHub hiển thị.
5. Khởi động bằng `./run.sh` hoặc cài thành service.
6. Xác nhận runner có trạng thái **Idle/Online**.
7. Đặt variable `SAST_RUNNER=self-hosted`.

Không commit registration token của runner.

## 10. Cấu hình Quality Profile và Quality Gate

### Quality Profile

1. Vào **Quality Profiles -> Python**.
2. Dùng `Sonar way` cho lần scan đầu.
3. Nếu cần tuning, copy thành `PoC Python SAST`.
4. Gán profile cho project.
5. Trong Issues, tập trung:
   - MQR mode: Blocker và High.
   - Standard Experience: Blocker và Critical.
6. Kiểm tra rule liên quan Flask và Django.

### Quality Gate

1. Vào **Quality Gates -> Create**.
2. Name: `PoC SAST Gate`.
3. Thêm điều kiện trên new code, tối thiểu:
   - Security Rating không tệ hơn A.
   - Security Hotspots Reviewed bằng 100%.
4. Gán gate cho project.

`sast-fixtures/` cố ý chứa lỗi nên lần đầu gate có thể đỏ. Giữ
`SONAR_ENFORCE_GATE=false` khi tuning. Sau khi xác nhận findings và baseline,
đổi variable thành `true` để gate đỏ làm job thất bại.

## 11. Chạy và kiểm tra pipeline

Workflow chạy khi:

- Push vào `main`.
- Pull request vào `main`: chạy pytest; Community Build không chạy SAST PR.
- Chọn **Actions -> Backend CI and SonarQube SAST -> Run workflow**.

Thứ tự kiểm tra:

1. GitHub job **Backend tests** phải xanh.
2. Job **SonarQube SAST** phải kết nối được tới SonarQube.
3. Step **Submit SonarQube analysis** phải thành công.
4. Step **Check SonarQube quality gate** hiển thị trạng thái gate.
5. Trong SonarQube, mở project **Activity** để thấy analysis mới.
6. Mở **Issues** và lọc Blocker/High hoặc Blocker/Critical.

Các finding cố ý mong đợi:

| File | Trường hợp |
| --- | --- |
| `flask_insecure.py` | SQL injection |
| `flask_insecure.py` | Command injection với `shell=True` |
| `flask_insecure.py` | Path traversal |
| `flask_insecure.py` | Hard-coded secret và debug mode |
| `django_insecure.py` | SQL injection |
| `django_insecure.py` | CSRF exemption và unsafe HTML |

## 12. Đánh giá PoC

Chạy ít nhất năm lần và ghi lại:

| Chỉ số | Tiêu chí đề xuất |
| --- | --- |
| Scan thành công | 5 lần liên tiếp |
| Warm scan median | Không quá 3 phút |
| Injection nghiêm trọng | Không bỏ sót |
| False positive | Dưới 20% findings đã review |
| Quality Gate | Code lỗi bị chặn khi enforcement bật |

## 13. Troubleshooting

### Không đăng nhập được bằng admin/admin

Volume đã lưu mật khẩu mới. Dùng mật khẩu đã đổi hoặc reset PoC bằng
`docker compose down -v`.

### API status không trả về UP

```bash
docker compose ps
docker compose logs --tail=200 sonarqube
sysctl vm.max_map_count
sysctl fs.file-max
```

### Token trả về valid:false

Tạo Project Analysis Token mới, kiểm tra token thuộc đúng project và chưa hết
hạn.

### GitHub Actions không kết nối được localhost

Dùng self-hosted runner trên cùng Ubuntu host, hoặc cung cấp URL SonarQube HTTPS
mà GitHub-hosted runner truy cập được.

### Scanner báo thiếu blame information

Workflow phải checkout với `fetch-depth: 0`. File workflow hiện tại đã cấu
hình giá trị này cho job SAST.

### Quality Gate đỏ ngay lần đầu

Đây là kết quả mong đợi vì `sast-fixtures/` chứa lỗi cố ý. Giữ
`SONAR_ENFORCE_GATE=false` trong giai đoạn kiểm chứng.

## 14. Dừng SonarQube

Giữ lại dữ liệu:

```bash
docker compose down
```

Xóa toàn bộ dữ liệu PoC:

```bash
docker compose down -v
```

## Tài liệu chính thức

- [SonarQube Community Build bằng Docker](https://docs.sonarsource.com/sonarqube-community-build/server-installation/from-docker-image/set-up-and-start-container)
- [Yêu cầu Linux host](https://docs.sonarsource.com/sonarqube-community-build/server-installation/pre-installation/linux)
- [Tài khoản mặc định](https://docs.sonarsource.com/sonarqube-community-build/instance-administration/user-management/introduction)
- [Quản lý token](https://docs.sonarsource.com/sonarqube-community-build/user-guide/managing-tokens)
- [Tạo GitHub App cho SonarQube](https://docs.sonarsource.com/sonarqube-community-build/devops-platform-integration/github-integration/setting-up-at-global-level/setting-up-github-app)
- [Thêm analysis vào GitHub Actions](https://docs.sonarsource.com/sonarqube-community-build/devops-platform-integration/github-integration/adding-analysis-to-github-actions-workflow)
- [SonarQube webhooks](https://docs.sonarsource.com/sonarqube-community-build/project-administration/webhooks)
