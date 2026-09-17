# PROJECT: Academic Citation Graph Visualizer

## 1. Mục tiêu dự án
Xây dựng ứng dụng web cho phép:
- Nhập DOI hoặc tiêu đề của bài báo khoa học.
- Trích xuất danh sách tài liệu tham khảo (references) và bài báo trích dẫn (citations).
- Đánh giá trọng số bài báo (dựa trên citation count, độ ảnh hưởng, thuật toán đồ thị).
- Mở rộng (expand) đồ thị tương tác nhiều tầng.
- Mở trực tiếp toàn văn PDF (qua Open Access / Unpaywall) hoặc fallback qua DOI resolver.

---

## 2. Kiến trúc & Công nghệ (Tech Stack)

### Backend (Python 3.11+)
- **Framework:** FastAPI (RESTful API, bất đồng bộ hoàn toàn với `async`/`await`).
- **HTTP Client:** `httpx` (asynchronous calls cho third-party APIs).
- **Validation / Schemas:** Pydantic v2.
- **Graph & Math Processing:** `networkx` (hoặc `igraph`) để tính toán PageRank / Degree Centrality khi cần.
- **Third-Party APIs sử dụng:**
  - Semantic Scholar Academic Graph API (metadata, references, `isInfluential`).
  - OpenAlex API (tra cứu cây trích dẫn thay thế/dự phòng).
  - Unpaywall API (tra cứu URL PDF Open Access miễn phí hợp pháp qua DOI).

### Frontend (TypeScript)
- **Framework:** React / Next.js (App Router) + Vite / Turbopack.
- **Styling:** Tailwind CSS + Lucide React (icons).
- **Graph Visualization:** `Cytoscape.js` (với layout `cola` hoặc `cose`) hoặc `Sigma.js` / `Cosmograph`.
- **State Management:** TanStack Query (React Query) + Zustand.

---

## 3. Cấu trúc thư mục chuẩn (Folder Structure)

```text
root/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (endpoints)
│   │   ├── core/         # Config, logging, settings
│   │   ├── models/       # Pydantic models & DTOs
│   │   ├── services/     # Tích hợp external APIs (Semantic Scholar, OpenAlex, Unpaywall)
│   │   └── utils/        # Graph processing algorithms (PageRank, node filters)
│   ├── tests/
│   ├── requirements.txt
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/   # GraphView, PaperDetailsModal, SearchBar, PDFViewer
│   │   ├── hooks/        # useCitationGraph, usePaperDetails
│   │   ├── services/     # Axios / Fetch client gọi sang backend
│   │   ├── types/        # TypeScript interfaces matching backend models
│   │   └── App.tsx
│   └── package.json
└── README.md