# PoC SonarQube SAST với GitHub Actions

**Trạng thái:** đã chuẩn bị xong cấu hình; chưa chạy scan thực tế trên SonarQube.

PoC này dùng một ứng dụng Flask nhỏ để kiểm tra việc tích hợp SonarQube vào GitHub Actions. SonarQube chỉ scan source code, không scan Docker image. Nếu cần scan image thì dùng Trivy trong một workflow riêng.

Repository chỉ dùng một file `requirements.txt`.

## PoC này kiểm tra những gì?

| Phần kiểm tra | Mục đích | Kết quả mong đợi |
| --- | --- | --- |
| Pytest | Kiểm tra ứng dụng Flask mẫu chạy đúng | API health, quote hợp lệ và dữ liệu không hợp lệ trả đúng kết quả |
| SonarQube SAST | Kiểm tra SonarQube có phát hiện code không an toàn | Phát hiện SQL injection, command injection, path traversal, XSS và cấu hình Flask/Django không an toàn |
| GitHub Actions | Kiểm tra scan có chạy tự động trong CI | Push hoặc pull request kích hoạt test và SonarQube scan |
| Quality Gate | Kiểm tra pipeline có thể cảnh báo hoặc chặn code lỗi | Gate đỏ khi có lỗi nghiêm trọng và xanh sau khi sửa |
| Thời gian scan | Kiểm tra SonarQube có làm pipeline chậm quá nhiều không | Thời gian scan ổn định và chấp nhận được |

Hai loại file có mục đích khác nhau:

- `tests/` là pytest thông thường, dùng để kiểm tra chức năng của Flask API.
- `sast-fixtures/` là code cố ý có lỗ hổng để kiểm tra khả năng phát hiện của SonarQube. Các file này không được import hoặc chạy.

## Luồng CI/CD

```text
Push hoặc Pull Request
  -> chạy pytest và tạo coverage.xml
  -> lấy SONAR_TOKEN từ GitHub Secret
  -> gửi source code tới SonarQube
  -> kiểm tra Quality Gate
```

Workflow dùng GitHub Secret `SONAR_TOKEN` và không có bước scan container image.

## Cấu trúc chính

| Đường dẫn | Nội dung |
| --- | --- |
| `app/`, `run.py` | Flask API mẫu |
| `tests/` | Kiểm tra API và service |
| `sast-fixtures/` | Code Flask/Django cố ý không an toàn |
| `compose.yaml` | Chạy một container SonarQube |
| `sonar-project.properties` | Cấu hình source, test và coverage |
| `.github/workflows/backend-sast.yml` | GitHub Actions workflow |
| `requirements.txt` | Toàn bộ Python dependencies |

## 1. Chạy ứng dụng và pytest

Trong PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
python run.py
```

Kiểm tra API:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/health
Invoke-RestMethod http://127.0.0.1:5000/api/v1/quotes/AAPL
```

Hiện tại bộ pytest có 8 test và coverage là 97.62%.

## 2. Chạy SonarQube

Yêu cầu Docker Desktop hoặc Docker Engine có Compose v2.

```powershell
docker compose up -d
docker compose ps
docker compose logs -f sonarqube
```

Mở `http://localhost:9000` và đăng nhập lần đầu bằng `admin/admin`.

Sau đó:

1. Tạo project có key `poc-sast-flask-backend`.
2. Tạo một **Project Analysis Token**.
3. Lưu token vào GitHub Secret `SONAR_TOKEN`.

Dừng SonarQube:

```powershell
docker compose down
```

Compose chỉ chạy SonarQube với H2 tích hợp, không có PostgreSQL. H2 phù hợp cho PoC local, không dùng cho production. Volume `sonarqube_data` giữ dữ liệu khi container được tạo lại.

## 3. Cấu hình rule và Quality Gate

Trong SonarQube:

1. Copy Python profile `Sonar way` thành `PoC Python SAST`.
2. Bật các security rule cho Python, Flask và Django.
3. Gán profile này cho project `poc-sast-flask-backend`.
4. Tạo Quality Gate trên new code:
   - không có Blocker;
   - không có High trong MQR mode, hoặc Critical trong Standard Experience mode;
   - Security Hotspots đã được review.

Các lỗi cố ý tạo trong `sast-fixtures/`:

| File | Lỗi cần SonarQube phát hiện |
| --- | --- |
| `flask_insecure.py` | SQL injection |
| `flask_insecure.py` | Command injection qua `shell=True` |
| `flask_insecure.py` | Path traversal |
| `flask_insecure.py` | Hard-coded secret và Flask debug mode |
| `django_insecure.py` | SQL injection |
| `django_insecure.py` | Tắt CSRF và đưa input chưa tin cậy vào HTML |

Rule key và severity có thể thay đổi theo phiên bản analyzer. Mục tiêu là kiểm tra SonarQube có đưa ra cảnh báo hữu ích, không yêu cầu tên rule phải cố định.

## 4. Cấu hình GitHub

Trong **Settings -> Secrets and variables -> Actions**:

### Secret

| Tên | Giá trị |
| --- | --- |
| `SONAR_TOKEN` | Project Analysis Token tạo từ SonarQube |

### Variable

| Tên | Ví dụ | Bắt buộc |
| --- | --- | --- |
| `SONAR_HOST_URL` | `https://sonarqube.example.com` | Có |
| `SAST_RUNNER` | `self-hosted` hoặc runner label riêng | Khi SonarQube chạy trong mạng nội bộ |
| `SONAR_ENFORCE_GATE` | `false` lúc tuning, sau đó `true` | Khuyến nghị |

Nếu SonarQube chạy tại `localhost:9000`, GitHub-hosted runner không thể truy cập máy local. Khi đó cần self-hosted runner cùng mạng với SonarQube.

Pull request từ fork bên ngoài sẽ bỏ qua job SAST vì GitHub không cấp repository secret cho fork.

## 5. Cách chạy PoC

1. Khởi động SonarQube và tạo project/token.
2. Thêm `SONAR_TOKEN` và `SONAR_HOST_URL` vào GitHub.
3. Để `SONAR_ENFORCE_GATE=false` trong lần chạy đầu.
4. Push code hoặc mở pull request vào `main`.
5. Kiểm tra pytest, SonarQube scan và Quality Gate trong GitHub Actions.
6. Mở SonarQube, đối chiếu kết quả với các lỗi cố ý trong `sast-fixtures/`.
7. Sau khi chỉnh rule phù hợp, đặt `SONAR_ENFORCE_GATE=true` và xác nhận gate đỏ làm job thất bại.

## 6. Ghi nhận kết quả

| Chỉ số | Cách kiểm tra | Tiêu chí đề xuất |
| --- | --- | --- |
| Scan thành công | GitHub Actions và SonarQube history | 5 lần liên tiếp thành công |
| Thời gian scan | Thời gian step scan và Quality Gate trong GitHub Actions | Median không quá 3 phút |
| Khả năng phát hiện | So sánh findings với `sast-fixtures/` | Không bỏ sót injection nghiêm trọng |
| False positive | Review từng finding nghiêm trọng | Ít hơn 20% findings đã review |
| Quality Gate | Chạy với `SONAR_ENFORCE_GATE=true` | Code lỗi bị chặn, code đã sửa được pass |

**Precision** được tính bằng:

```text
true positives / (true positives + false positives)
```

## Kết quả hiện tại

| Hạng mục | Trạng thái |
| --- | --- |
| Flask app và pytest | Hoàn thành |
| SonarQube Docker Compose | Hoàn thành |
| GitHub Actions dùng GitHub Secret | Hoàn thành |
| Live SonarQube scan | Chưa chạy |
| Đánh giá thời gian và false positive | Chưa có dữ liệu |

Chỉ kết luận SonarQube phù hợp sau khi chạy đủ sample commit/pull request và ghi lại các số liệu trên.

## Ngoài phạm vi

- Scan Docker image: dùng Trivy workflow riêng.
- Dependency/SCA scanning.
- DAST.
- SonarQube production architecture.

## Tài liệu tham khảo

- [SonarQube Community Build Docker setup](https://docs.sonarsource.com/sonarqube-community-build/server-installation/from-docker-image/set-up-and-start-container)
- [SonarQube với GitHub Actions](https://docs.sonarsource.com/sonarqube-server/devops-platform-integration/github-integration/adding-analysis-to-github-actions-workflow)
- [SonarQube Quality Gates](https://docs.sonarsource.com/sonarqube-community-build/quality-standards-administration/managing-quality-gates/introduction-to-quality-gates)
