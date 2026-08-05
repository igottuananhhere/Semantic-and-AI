# QUY TRÌNH TÓM TẮT — Semantic Layer (Cube.dev) + AI + Dashboard

> Bản tóm tắt nhanh, xem chi tiết đầy đủ tại `README_Semantic_Layer_CubeDev_AI_Demo.md`

---

## SƠ ĐỒ TỔNG QUAN

```
┌──────────────┐     ┌───────────────────┐     ┌─────────────┐     ┌────────────────┐
│  PostgreSQL   │ ──► │   Cube Core        │ ──► │  MCP Server  │ ──► │ Claude Desktop  │
│ (dữ liệu thô) │     │ (Docker, self-host)│     │ (mcp_cube_   │     │ (hỏi tiếng Việt)│
└──────────────┘     │  = SEMANTIC LAYER  │     │  server)     │     └────────────────┘
                      └─────────┬─────────┘     └─────────────┘
                                │ SQL API (port 15432)
                                ▼
                      ┌───────────────────┐
                      │     Superset        │  ← Dashboard, đọc CÙNG semantic layer
                      └───────────────────┘
```

---

## FLOW 1 — Dựng hạ tầng (làm 1 lần)

```
1. Tạo docker-compose.yml (postgres + cube)
        ↓
2. docker compose up -d  →  docker ps (xác nhận Up)
        ↓
3. Nạp dữ liệu vào Postgres (SQL script hoặc Python/Polars)
        ↓
4. Viết model/*.yml (measures, dimensions)  →  Cube tự hot-reload
        ↓
5. Kiểm tra tại localhost:4000 (Cube Playground) → Run Query → đối chiếu SQL thô
```

## FLOW 2 — Nối AI (MCP)

```
1. Tạo token JWT (ký bằng CUBEJS_API_SECRET)
        ↓
2. Cài mcp_cube_server (pip install -e . từ GitHub)
        ↓
3. Claude Desktop → Settings → Developer → Edit Config
        ↓
4. Thêm mcpServers: { command, args: [--endpoint, --api_secret] }
        ↓
5. Thoát hẳn Claude Desktop → mở lại → Developer → status "running"
        ↓
6. Hỏi thử: "Tổng doanh thu tháng X là bao nhiêu?"
```

## FLOW 3 — Nối Dashboard (Superset)

```
1. Settings → Database Connections → + Database → PostgreSQL
        ↓
2. Host: host.docker.internal | Port: 15432 | DB: db | User: cube | Pass: token
        ↓
3. Tạo Dataset trỏ vào cube "online_retail"
        ↓
4. Tạo Chart (luôn chọn Aggregate = SUM)
        ↓
5. Ghép Dashboard theo F/Z-pattern + thêm Filter sidebar (Time, Country)
        ↓
6. Đối chiếu: hỏi AI → bấm filter dashboard → so số
```

## FLOW 4 — Kiểm chứng bảo mật (Q&A)

```
1. Tạo bảng "nhạy cảm" giả lập (employees_confidential)
        ↓
2. KHÔNG tạo file .yml cho bảng này
        ↓
3. Hỏi AI về bảng đó → AI không thấy
        ↓
4. Đối chiếu bằng DBeaver → dữ liệu có thật, chỉ AI không có đường vào
```

---

## BẢNG THAM SỐ KẾT NỐI (dùng lại nhiều lần)

| Thành phần | Giá trị |
|---|---|
| Postgres host/port | `localhost:5434` (từ ngoài) / `postgres:5432` (nội bộ Docker) |
| Postgres DB / user / pass | `demo_ecommerce` / `cube` / `cubepass` |
| Cube API | `http://localhost:4000/cubejs-api/v1` |
| Cube SQL API (cho Superset) | `host.docker.internal:15432`, database `db` |
| Cube Playground | `http://localhost:4000` |

---

## LỆNH HAY DÙNG (tra cứu nhanh)

```bash
# Khởi động / dừng hạ tầng
docker compose up -d
docker compose down -v      # xoá cả volume — dùng khi cần reset sạch

# Kiểm tra trạng thái
docker ps
docker exec demo-postgres env | findstr POSTGRES
docker exec demo-cube env | findstr CUBEJS_DB

# Kiểm tra dữ liệu
docker exec -it demo-postgres psql -U cube -d demo_ecommerce -c "\du"
```

```sql
-- Đối chiếu doanh thu 1 tháng, khớp đúng logic measure total_revenue
SELECT SUM(quantity * unit_price) AS total_revenue
FROM online_retail_raw
WHERE invoice_date >= DATE '2026-01-01'
  AND invoice_date < DATE '2026-02-01'
  AND invoice_no NOT LIKE 'C%';
```

---

## FILE CẦN CÓ TRONG REPO GIT

```
cube-ai-demo/
├── docker-compose.yml
├── model/
│   └── online_retail.yml
├── seed/
│   └── init.sql              # script tạo bảng + insert dữ liệu mẫu
├── load_data.py               # (tuỳ chọn) script nạp CSV/Excel thật
├── generate_token.py
├── README_Semantic_Layer_CubeDev_AI_Demo.md
├── QUY_TRINH_TOM_TAT.md       # chính file này
└── .gitignore
```

> ⚠️ **Không đưa lên Git**: token thật, file `claude_desktop_config.json` (chứa token/đường dẫn máy cá nhân), file dữ liệu Kaggle gốc nếu có bản quyền giới hạn phân phối lại.

