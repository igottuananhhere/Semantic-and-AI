# Semantic Layer & Cube.dev — AI Natural Language Querying Demo

> Tài liệu tổng hợp: lý thuyết seminar + hướng dẫn dựng lại demo (đã kiểm chứng thực tế, bao gồm các lỗi thường gặp và cách xử lý) + phần bảo mật/Q&A.
> Stack: PostgreSQL → Cube Core (self-host, Docker) → MCP Server → Claude Desktop, song song với Superset (SQL API) làm dashboard.

---

## MỤC LỤC

1. [Vai trò của Semantic Layer trong kỷ nguyên AI](#1)
2. [Giới thiệu Cube.dev / Cube Core](#2)
3. [Kiến trúc demo](#3)
4. [Setup môi trường (Docker)](#4)
5. [Nạp dữ liệu mẫu (Online Retail dataset)](#5)
6. [Định nghĩa Semantic Layer (Cube Data Model)](#6)
7. [Cài đặt MCP Server + kết nối Claude Desktop](#7)
8. [Kết nối Dashboard (Superset) — Single Source of Truth](#8)
9. [Bảo mật: AI có đọc được dữ liệu ngoài phạm vi không?](#9)
10. [Checklist trước khi demo live](#10)
11. [Nhật ký lỗi thường gặp & cách xử lý](#11)

---

<a id="1"></a>
## 1. Vai trò của Semantic Layer trong kỷ nguyên AI

### Vấn đề
Để AI tự viết SQL trực tiếp trên schema thô (NL2SQL cổ điển) mang lại 3 rủi ro đã ghi nhận:
- **Không nhất quán**: cùng 1 câu hỏi, LLM có thể sinh SQL khác nhau ở các lần gọi khác nhau.
- **Rò rỉ dữ liệu**: AI có full quyền SELECT trên schema thô, dễ vô tình trả về dữ liệu nhạy cảm.
- **"Confident wrong numbers"**: AI trả lời tự nhiên, thuyết phục, nhưng logic tính sai — người dùng business khó phát hiện.

### Semantic Layer là gì
Một tầng metadata + logic nằm giữa database và lớp tiêu thụ (BI tool, AI agent), gồm:
- **Measures**: công thức tính (SUM, COUNT DISTINCT, tỷ lệ...)
- **Dimensions**: trục phân tích (thời gian, khu vực, danh mục...)
- **Relationships**: join đã kiểm chứng, khai báo tường minh
- **API chuẩn hoá**: SQL API / REST API / GraphQL API — mọi công cụ phía trên dùng chung 1 logic

### 4 vai trò trong kiến trúc AI-BI hiện đại
1. **Grounding cho AI**: AI chọn đúng measure/dimension đã định nghĩa sẵn, thay vì tự đoán SQL trên schema thô.
2. **Governance & Access Control tập trung**: row-level/column-level security áp dụng 1 lần, đồng nhất cho mọi kênh truy vấn (kể cả AI).
3. **Chuẩn API cho AI Agent (MCP)**: Model Context Protocol cho phép AI "khám phá" và gọi measure như gọi 1 function.
4. **Single Source of Truth**: AI trả lời và Dashboard hiển thị cùng đọc 1 nguồn — số liệu luôn khớp tuyệt đối.

---

<a id="2"></a>
## 2. Giới thiệu Cube.dev / Cube Core

- **Cube Core**: mã nguồn mở (Apache 2.0), tự host miễn phí, chạy bằng Docker — phù hợp đội nhỏ, ngân sách thấp.
- **Cube Cloud**: bản thương mại, có UI quản trị, MCP server hosted sẵn (gói Premium/Enterprise).

**Kiến trúc**: Data model (YAML) → Cube compiler → nhiều API đầu ra cùng lúc (SQL API, REST API, GraphQL API, MCP) → Cube Store (cache/pre-aggregation).

**Case study**: Grafana Labs dùng chính Cube làm semantic layer nội bộ, tách riêng phần định nghĩa metric khỏi phần hiển thị.

**Lộ trình nâng cấp**: không cần dbt ngay từ đầu — Cube Core độc lập, khi cần có thể thêm dbt làm tầng transform hoặc nâng cấp Cube Cloud mà không đổi công nghệ.

### ⚠️ Điểm quan trọng — MCP trên Cube Core self-host

| | Cube Cloud (MCP chính chủ) | Cube Core tự host (miễn phí) |
|---|---|---|
| MCP server | Có sẵn, hosted, OAuth | **Không có** — tính năng thuộc gói Premium/Enterprise |
| Cách nhúng AI | Add connector, xác thực OAuth | Dùng **MCP server mã nguồn mở cộng đồng**, gọi qua REST API của Cube Core |

Demo này dùng **`isaacwasserman/mcp_cube_server`** (GitHub, mã nguồn mở) làm cầu nối.

---

<a id="3"></a>
## 3. Kiến trúc demo

```
PostgreSQL (online_retail_raw) → Cube Core (Docker) = SEMANTIC LAYER → 2 nhánh song song:

  Nhánh 1: MCP Server (mcp_cube_server) → Claude Desktop → người dùng hỏi tiếng Việt
  Nhánh 2: SQL API (port 15432) → Superset → Dashboard hiển thị
```

**Thông điệp cốt lõi**: cả AI và Dashboard đều đọc từ **cùng 1 data model** trong Cube Core — không phải 2 nguồn logic tách biệt. Đây là điểm khác biệt lớn nhất so với các giải pháp AI-BI rời rạc.

---

<a id="4"></a>
## 4. Setup môi trường (Docker)

### 4.1. `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16
    container_name: demo-postgres
    environment:
      POSTGRES_USER: cube
      POSTGRES_PASSWORD: cubepass
      POSTGRES_DB: demo_ecommerce
    ports:
      - "5434:5432"   # xem lưu ý cổng bên dưới
  cube:
    image: cubejs/cube:latest
    container_name: demo-cube
    ports:
      - "4000:4000"
      - "15432:15432"
    environment:
      CUBEJS_DEV_MODE: "true"
      CUBEJS_DB_TYPE: postgres
      CUBEJS_DB_HOST: postgres
      CUBEJS_DB_NAME: demo_ecommerce
      CUBEJS_DB_USER: cube
      CUBEJS_DB_PASS: cubepass
      CUBEJS_API_SECRET: "demo_secret_change_me"
    volumes:
      - ./model:/cube/conf/model
    depends_on:
      - postgres
```

> ⚠️ **Lưu ý cổng 5432**: nếu máy đã cài PostgreSQL native (Windows service), nó sẽ chiếm cổng `5432` trước Docker. Đổi cổng public của container Postgres sang `5434:5432` (chỉ ảnh hưởng cách *bạn* kết nối từ ngoài — DBeaver, script — không ảnh hưởng nội bộ Docker network, vì `cube` service vẫn gọi `postgres:5432` qua tên service).

### 4.2. Khởi động

```bash
docker compose up -d
docker ps          # xác nhận demo-postgres, demo-cube đều Up
```

---

<a id="5"></a>
## 5. Nạp dữ liệu mẫu (Online Retail dataset)

Dataset dùng: **UCI/Kaggle "Online Retail"** — 1 bảng phẳng giao dịch bán lẻ, cột: `InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country`.

### 5.1. Tạo bảng + dữ liệu mẫu rút gọn (dùng khi không có sẵn file Kaggle)

```sql
DROP TABLE IF EXISTS online_retail_raw;

CREATE TABLE online_retail_raw (
    id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(20),
    stock_code VARCHAR(20),
    description TEXT,
    quantity INT,
    invoice_date TIMESTAMP,
    unit_price NUMERIC(10,2),
    customer_id VARCHAR(20),
    country VARCHAR(50)
);

-- 37 dòng dữ liệu mẫu, trải 3 tháng (T1-T3/2026), 4 quốc gia,
-- có cả hoá đơn huỷ (invoice_no bắt đầu bằng 'C') và 1 dòng customer_id NULL (khách vãng lai)
INSERT INTO online_retail_raw (invoice_no, stock_code, description, quantity, invoice_date, unit_price, customer_id, country) VALUES
('536101','85123A','White Hanging Heart T-Light Holder',6,'2026-01-05 09:12:00',2.55,'17850','United Kingdom'),
('536101','71053','White Metal Lantern',6,'2026-01-05 09:12:00',3.39,'17850','United Kingdom'),
('536102','84406B','Cream Cupid Hearts Coat Hanger',8,'2026-01-06 10:30:00',2.75,'13047','United Kingdom'),
('536103','21730','Glass Star Frosted T-Light Holder',6,'2026-01-07 11:45:00',4.25,'17850','United Kingdom'),
('536104','22752','Set 7 Babushka Nesting Boxes',2,'2026-01-08 13:20:00',7.65,'12583','France'),
('536105','21212','Pack Of 72 Retro Spot Cake Cases',24,'2026-01-09 14:05:00',0.55,'12583','France'),
('536106','22633','Hand Warmer Union Jack',12,'2026-01-10 08:55:00',1.85,'13748','Germany'),
('536107','22632','Hand Warmer Red Polka Dot',12,'2026-01-11 09:40:00',1.85,'14606','United Kingdom'),
('C536108','85123A','White Hanging Heart T-Light Holder',-3,'2026-01-12 10:10:00',2.55,'17850','United Kingdom'),
('536109','84879','Assorted Colour Bird Ornament',32,'2026-01-13 12:00:00',1.69,'15311','United Kingdom'),
('536110','22961','Jam Making Set Printed',24,'2026-01-14 15:30:00',1.45,'12583','France'),
('536111','21754','Home Building Block Word',3,'2026-01-15 16:15:00',5.95,'13089','United Kingdom'),
('536112','22745','Poppys Playhouse Bedroom',6,'2026-01-16 09:05:00',2.10,'14911','Germany'),
('536113','21777','Recipe Box With Metal Heart',4,'2026-01-17 10:50:00',7.95,'17850','United Kingdom'),
('C536114','22752','Set 7 Babushka Nesting Boxes',-2,'2026-01-18 11:25:00',7.65,'12583','France'),
('536201','85123A','White Hanging Heart T-Light Holder',10,'2026-02-02 09:00:00',2.55,'16029','Spain'),
('536202','22423','Regency Cakestand 3 Tier',4,'2026-02-03 10:15:00',12.75,'13047','United Kingdom'),
('536203','21232','Strawberry Ceramic Trinket Box',12,'2026-02-04 11:00:00',1.25,'14606','United Kingdom'),
('536204','22961','Jam Making Set Printed',18,'2026-02-05 12:30:00',1.45,'12583','France'),
('536205','21212','Pack Of 72 Retro Spot Cake Cases',48,'2026-02-06 13:45:00',0.55,'15311','United Kingdom'),
('536206','22633','Hand Warmer Union Jack',24,'2026-02-07 09:20:00',1.85,'13748','Germany'),
('536207','84406B','Cream Cupid Hearts Coat Hanger',6,'2026-02-08 10:05:00',2.75,'17850','United Kingdom'),
('C536208','22423','Regency Cakestand 3 Tier',-4,'2026-02-09 11:40:00',12.75,'13047','United Kingdom'),
('536209','21754','Home Building Block Word',5,'2026-02-10 14:15:00',5.95,NULL,'United Kingdom'),
('536210','21777','Recipe Box With Metal Heart',3,'2026-02-11 15:00:00',7.95,'14911','Germany'),
('536211','22745','Poppys Playhouse Bedroom',8,'2026-02-12 16:30:00',2.10,'16029','Spain'),
('536212','71053','White Metal Lantern',10,'2026-02-13 09:45:00',3.39,'17850','United Kingdom'),
('536301','85123A','White Hanging Heart T-Light Holder',15,'2026-03-01 09:10:00',2.55,'13047','United Kingdom'),
('536302','22423','Regency Cakestand 3 Tier',6,'2026-03-02 10:25:00',12.75,'12583','France'),
('536303','22961','Jam Making Set Printed',30,'2026-03-03 11:50:00',1.45,'14606','United Kingdom'),
('536304','21232','Strawberry Ceramic Trinket Box',20,'2026-03-04 13:10:00',1.25,'15311','United Kingdom'),
('536305','22633','Hand Warmer Union Jack',16,'2026-03-05 14:40:00',1.85,'13748','Germany'),
('C536306','85123A','White Hanging Heart T-Light Holder',-6,'2026-03-06 15:20:00',2.55,'13047','United Kingdom'),
('536307','21754','Home Building Block Word',4,'2026-03-07 09:00:00',5.95,'17850','United Kingdom'),
('536308','84406B','Cream Cupid Hearts Coat Hanger',10,'2026-03-08 10:35:00',2.75,'16029','Spain'),
('536309','22745','Poppys Playhouse Bedroom',5,'2026-03-09 11:15:00',2.10,'14911','Germany'),
('536310','21777','Recipe Box With Metal Heart',6,'2026-03-10 12:45:00',7.95,'12583','France');
```

Kiểm tra: `SELECT COUNT(*) FROM online_retail_raw;` → phải ra **37**.

### 5.2. Nếu dùng file Kaggle thật (CSV/Excel)

```python
import polars as pl
from sqlalchemy import create_engine

df = pl.read_csv(r"D:\đường_dẫn\OnlineRetail.csv", encoding="windows-1252", infer_schema_length=10000)
df = df.rename({
    "InvoiceNo": "invoice_no", "StockCode": "stock_code", "Description": "description",
    "Quantity": "quantity", "InvoiceDate": "invoice_date", "UnitPrice": "unit_price",
    "CustomerID": "customer_id", "Country": "country",
})
engine = create_engine("postgresql://cube:cubepass@localhost:5434/demo_ecommerce")
df.write_database("online_retail_raw", engine, if_table_exists="replace")
```
Sau đó thêm khoá chính: `ALTER TABLE online_retail_raw ADD COLUMN id SERIAL PRIMARY KEY;`

---

<a id="6"></a>
## 6. Định nghĩa Semantic Layer (Cube Data Model)

File `model/online_retail.yml`:

```yaml
cubes:
  - name: online_retail
    sql: >
      SELECT
        id, invoice_no, stock_code, description, quantity,
        invoice_date, unit_price, customer_id, country,
        (invoice_no LIKE 'C%') AS is_cancelled
      FROM online_retail_raw

    measures:
      - name: total_revenue
        sql: "quantity * unit_price"
        type: sum
        filters:
          - sql: "{CUBE}.is_cancelled = false"
        description: "Doanh thu, loại trừ hoá đơn huỷ (InvoiceNo bắt đầu bằng 'C')"

      - name: order_count
        sql: invoice_no
        type: count_distinct
        filters:
          - sql: "{CUBE}.is_cancelled = false"
        description: "Số hoá đơn hợp lệ"

      - name: cancelled_rate
        sql: "COUNT(DISTINCT CASE WHEN {CUBE}.is_cancelled THEN {CUBE}.invoice_no END)::float / NULLIF(COUNT(DISTINCT {CUBE}.invoice_no), 0)"
        type: number
        description: "Tỷ lệ hoá đơn bị huỷ"

      - name: total_quantity
        sql: quantity
        type: sum
        filters:
          - sql: "{CUBE}.is_cancelled = false"
        description: "Tổng số lượng sản phẩm bán ra"

    dimensions:
      - name: id
        sql: id
        type: number
        primary_key: true
      - name: invoice_no
        sql: invoice_no
        type: string
      - name: description
        sql: description
        type: string
      - name: customer_id
        sql: customer_id
        type: string
      - name: country
        sql: country
        type: string
      - name: invoice_date
        sql: invoice_date
        type: time
```

Cube dev mode tự hot-reload khi lưu file. Kiểm tra tại `http://localhost:4000` → tab **Schema** → cube `online_retail` phải xuất hiện đầy đủ measures/dimensions.

**Kiểm chứng số liệu tham khảo** (từ bộ dữ liệu mẫu 37 dòng):

| Quốc gia | total_revenue | order_count | total_quantity |
|---|---|---|---|
| United Kingdom | 512.17 | 17 | 231 |
| France | 213.6 | 6 | 80 |
| Germany | 143.15 | 6 | 66 |
| Spain | 69.8 | 3 | 28 |
| **Tổng** | **938.72** | | |

`cancelled_rate` toàn bộ ≈ **0.1111**.

---

<a id="7"></a>
## 7. Cài đặt MCP Server + kết nối Claude Desktop

### 7.1. Lấy API Token

Token JWT ký bằng `CUBEJS_API_SECRET`. Tự tạo bằng script:
```python
import jwt
token = jwt.encode({}, "demo_secret_change_me", algorithm="HS256")
print(token)
```
(`pip install pyjwt` nếu chưa có). Payload rỗng `{}` → token không có hạn dùng (`exp`), phù hợp demo.

Kiểm tra token hoạt động:
```powershell
curl.exe -H "Authorization: <token>" http://localhost:4000/cubejs-api/v1/meta
```
(Trên PowerShell dùng `curl.exe`, không dùng alias `curl` mặc định — alias đó trỏ tới `Invoke-WebRequest`, cú pháp `-H` khác.)

### 7.2. Cài MCP server

```powershell
git clone https://github.com/isaacwasserman/mcp_cube_server.git
cd mcp_cube_server
pip install -e .
```

> ⚠️ **Lỗi thường gặp**: `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` — do package `mcp` cài từ PyPI có thể là bản không tương thích (VD `mcp==2.0.0` tái cấu trúc module). Xem mục [Nhật ký lỗi](#11) để xử lý.

### 7.3. Cấu hình Claude Desktop

Trong Claude Desktop: **Settings → Developer → "Local MCP servers" → Edit Config**. App sẽ tự mở đúng file cấu hình thật (đường dẫn có thể khác `%APPDATA%\Claude` tuỳ cách đóng gói — dùng nút Edit Config thay vì tự dò đường dẫn).

```json
{
  "mcpServers": {
    "cube-semantic-layer": {
      "command": "C:\\đường_dẫn\\Scripts\\mcp_cube_server.exe",
      "args": [
        "--endpoint", "http://localhost:4000/cubejs-api/v1",
        "--api_secret", "<token>"
      ]
    }
  }
}
```

> ⚠️ Package `mcp_cube_server` nhận cấu hình qua **tham số dòng lệnh** (`--endpoint`, `--api_secret`), không qua biến môi trường `env`.

Lưu file → thoát hẳn Claude Desktop (Task Manager → End Task nếu cần) → mở lại → **Settings → Developer** → `cube-semantic-layer` phải chuyển sang trạng thái **"running"**.

### 7.4. Câu hỏi demo mẫu

```
Cho tôi biết những số liệu nào đang có sẵn về đơn hàng?
Tổng doanh thu tháng 1/2026 là bao nhiêu?
So sánh doanh thu giữa các quốc gia
Tỷ lệ huỷ đơn hiện tại là bao nhiêu?
Bạn lấy số liệu này từ measure nào?
```

---

<a id="8"></a>
## 8. Kết nối Dashboard (Superset) — Single Source of Truth

### 8.1. Thêm database connection trỏ vào Cube SQL API

**Settings → Database Connections → + Database → PostgreSQL**

| Trường | Giá trị |
|---|---|
| Host | `host.docker.internal` (nếu Superset chạy trong Docker riêng — `localhost` sẽ trỏ vào chính container Superset, không phải máy host) |
| Port | `15432` |
| Database name | `db` |
| Username | `cube` (giá trị bất kỳ, Cube không kiểm tra) |
| Password | token JWT |

### 8.2. Tạo Dataset + Chart

Dataset trỏ vào **cube** `online_retail` (không phải bảng `online_retail_raw` gốc). Tạo 4 chart:

| Chart | Loại | Metric | Dimension | Aggregate trong Superset |
|---|---|---|---|---|
| Tổng doanh thu | Big Number with Trendline | `total_revenue` | `invoice_date` (Time Grain: Month) | **SUM** |
| Doanh thu theo quốc gia | Bar Chart | `total_revenue` | `country` | **SUM** |
| Tỷ lệ huỷ đơn | Big Number | `cancelled_rate` | — | **SUM** |
| Xu hướng theo tháng | Line Chart | `total_revenue` | `invoice_date` (Time Grain: Month) | **SUM** |

> ⚠️ **Luôn chọn Aggregate = SUM** cho mọi measure lấy từ Cube trong Superset — vì Cube đã tính đúng sẵn theo breakdown dimension, Superset chỉ "truyền qua". Chọn AVG/COUNT sẽ tính sai vì áp nhầm phép toán lên 1 số đã tổng hợp sẵn.

### 8.3. Bố cục Dashboard (nguyên tắc F/Z-pattern)

```
┌──────────────┬──────────────┬───────────────┐
│ Tổng doanh   │  Tỷ lệ huỷ   │  [Filter: tháng,│  ← KPI chính, trên-trái
│ thu (Big #)  │  đơn (Big #) │   quốc gia]    │
├──────────────┴──────────────┼───────────────┤
│   Xu hướng theo tháng        │                │  ← Xu hướng, giữa
│   (Line Chart)                │                │
├───────────────────────────────┴───────────────┤
│      Doanh thu theo quốc gia (Bar Chart)       │  ← Chi tiết, dưới cùng
└─────────────────────────────────────────────────┘
```
- Filter (Time range trên `invoice_date`, Value dropdown trên `country`) đặt ở sidebar trái (mặc định của Superset Native Filters) — Scoping = "Apply to all panels" cho cả 4 chart.
- Giữ khoảng trắng đều, không nhồi quá 2-3 chart/hàng.

> **Ghi chú thực tế**: cross-filter (bấm trực tiếp vào cột bar chart để lọc chéo) có thể không hoạt động ổn định tuỳ phiên bản Superset. Nếu gặp vấn đề này, dùng **Filter sidebar (dropdown)** làm phương án chính — vẫn đảm bảo đúng thông điệp "chọn 1 quốc gia → mọi chart tự cập nhật khớp với AI".

### 8.4. Kịch bản demo đối chiếu

1. Hỏi AI: *"Tổng doanh thu tháng 1/2026 là bao nhiêu?"* → AI trả lời **307.17**
2. Bấm filter Time = January 2026 trên dashboard → Big Number cũng ra **307.17**
3. Hỏi AI: *"Doanh thu ở France là bao nhiêu?"* → AI trả lời
4. Bấm filter Country = France → dashboard khớp ngay

---

<a id="9"></a>
## 9. Bảo mật: AI có đọc được dữ liệu ngoài phạm vi không?

### Câu hỏi thường gặp nhất trong Q&A
*"Nếu Postgres có bảng dữ liệu nhạy cảm (lương, PII...) mà không đưa vào semantic layer, AI có 'chọc' ra được không?"*

### Trả lời: Không, với điều kiện đúng kiến trúc

`mcp_cube_server` **không hề cầm thông tin đăng nhập Postgres**. Nó chỉ có 1 endpoint (Cube API) + 1 token. Chuỗi kết nối thật:
```
Claude → MCP server → Cube REST API (chỉ hiểu measures/dimensions đã khai báo trong .yml) → Postgres
```
Một bảng chưa có cube nào trỏ tới → Cube API còn không biết nó tồn tại để trả lời, không phải "AI tử tế không hỏi".

### Demo trực tiếp minh chứng (dùng trong Q&A)

Tạo 1 bảng giả lập:
```sql
CREATE TABLE employees_confidential (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100), department VARCHAR(50), salary NUMERIC(12,2),
    national_id VARCHAR(20), bank_account VARCHAR(30)
);
INSERT INTO employees_confidential (full_name, department, salary, national_id, bank_account) VALUES
('Nguyễn Văn A','Sales',25000000,'001099012345','1903-xxxx-001'),
('Trần Thị B','Marketing',22000000,'001099012346','1903-xxxx-002');
```
**Không** tạo file `.yml` nào cho bảng này. Sau đó hỏi Claude Desktop:
```
Bạn có thấy thông tin gì về lương, nhân viên, hoặc bảng employees_confidential không?
```
→ AI báo không thấy. Đối chiếu bằng DBeaver `SELECT * FROM employees_confidential;` → dữ liệu tồn tại thật, chỉ là AI không có đường vào.

### 2 điều kiện bắt buộc để đảm bảo an toàn thật sự

1. **Không cấp thêm MCP server nào khác** trỏ thẳng vào cùng Postgres (tránh "cửa sau").
2. **User Postgres phía sau Cube chỉ nên có quyền tối thiểu** — không dùng cấu hình demo (`Superuser, Create role, Create DB, Bypass RLS`) cho môi trường thật.

### Checklist "least privilege" cho user DB production

```sql
CREATE ROLE cube_reader WITH LOGIN PASSWORD '...';
REVOKE CONNECT ON DATABASE demo_ecommerce FROM PUBLIC;
GRANT CONNECT ON DATABASE demo_ecommerce TO cube_reader;
GRANT USAGE ON SCHEMA public TO cube_reader;
GRANT SELECT ON online_retail_raw TO cube_reader;   -- chỉ đúng bảng cần, KHÔNG dùng ALL TABLES
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM cube_reader;
REVOKE CREATE ON SCHEMA public FROM cube_reader;
ALTER ROLE cube_reader CONNECTION LIMIT 20;
```
Với bảng có cả cột public lẫn nhạy cảm: tạo **view** chỉ lộ cột được phép, cấp quyền trên view thay vì bảng gốc. Nếu cần phân quyền theo nhóm người dùng: dùng **Cube Security Context** để áp filter bắt buộc cho mọi truy vấn, kể cả từ AI.

### Câu trả lời chốt cho khán giả
> *"AI không có thông tin đăng nhập database, chỉ có 1 địa chỉ API và 1 token của Cube. Cube API chỉ biết trả lời đúng những gì được định nghĩa sẵn trong file YAML — không có cơ chế nào để AI 'chọc' xuống tận Postgres, trừ khi có người cố tình cấu hình thêm đường khác."*

---

<a id="10"></a>
## 10. Checklist trước khi demo live

- [ ] `docker compose up -d` chạy ổn định trên máy sạch (test lại từ đầu, không chỉ máy đã setup)
- [ ] Token Cube không hết hạn (dùng payload `{}` — không có `exp`, an toàn cho demo)
- [ ] Test trước toàn bộ câu hỏi demo mẫu, xác nhận Claude Desktop trả lời ổn định
- [ ] `cube-semantic-layer` ở trạng thái **"running"** trong Settings → Developer
- [ ] Dashboard Superset đã Publish (không còn "Draft")
- [ ] Chuẩn bị phương án dự phòng: video/screenshot kết quả demo thành công, phòng sự cố mạng/Docker khi trình bày trực tiếp
- [ ] Không demo trên dữ liệu thật/nhạy cảm — chỉ dùng dataset mẫu
- [ ] Đã test bảng `employees_confidential` cho phần Q&A bảo mật

---

<a id="11"></a>
## 11. Nhật ký lỗi thường gặp & cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `password authentication failed for user "cube"` | Postgres container init với password cũ (từ `docker-compose.yml` từng bị sửa sai) trước khi sửa lại đúng | `docker compose down -v` (xoá volume) rồi `up -d` lại — sửa file *trước*, không sửa container đang chạy |
| `role "cube" does not exist` khi dùng DBeaver dù container đúng | Có Postgres khác (native trên Windows, hoặc container khác) cùng chiếm cổng `5432` | `netstat -ano \| findstr :5432` xem có > 1 PID; nếu có, đổi cổng public của container Postgres (VD `5434:5432`) |
| `no configuration file provided: not found` khi `docker compose up` | Chưa tạo file `docker-compose.yml` đúng thư mục, hoặc file bị lưu nhầm đuôi `.txt` | Dùng VS Code tạo file (tránh Notepad tự thêm `.txt`); xác nhận bằng `dir` |
| `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | Package `mcp` cài từ PyPI là bản không tương thích với `mcp_cube_server` (VD `mcp==2.0.0` đổi cấu trúc module) | `pip install "mcp==1.9.4"` (hạ về bản tương thích), hoặc cân nhắc tự viết MCP server tối giản dùng SDK mới nếu dự án cộng đồng không cập nhật kịp |
| MCP server "failed" — `Server disconnected` trong Claude Desktop | Thiếu tham số bắt buộc (`--endpoint`, `--api_secret`) — package này không đọc `env`, cần truyền qua `args` | Sửa `claude_desktop_config.json`, dùng `args` thay vì `env` |
| Không tìm thấy `%APPDATA%\Claude` | Bản Claude Desktop cài kiểu packaged/sandboxed (Microsoft Store) — path bị ảo hoá vào `AppData\Local\Packages\...` | Dùng **Settings → Developer → Edit Config** trong chính app để nó tự mở đúng file, không tự dò đường dẫn |
| Superset báo "The port is closed" khi nối tới Cube SQL API | Superset chạy trong Docker riêng, `localhost` từ góc nhìn container đó không phải máy host | Đổi Host thành `host.docker.internal`, hoặc nối 2 container vào chung Docker network |
| Cross-filter (bấm vào bar chart) không hoạt động | Tuỳ phiên bản Superset / trạng thái Draft chưa Publish | Dùng Filter sidebar (dropdown) làm phương án chính, không phụ thuộc cross-filter |
| Đếm số dòng dữ liệu ra khác kỳ vọng (VD 37 thay vì "36") | Nhầm lẫn khi đếm thủ công bộ dữ liệu mẫu | Luôn đối chiếu bằng `SUM()` trực tiếp trên dữ liệu thô so với con số Cube/AI trả lời, thay vì chỉ tin vào số dòng |

