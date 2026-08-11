# Báo Cáo Phân Tích & Thiết Kế Kiến Trúc RAG Chatbot (Phase E)

**Dự án**: Hệ thống Số hoá & Quản lý Tài liệu Công tác Sinh viên  
**Tác giả**: Explorer Phase E 2 (RAG Chatbot Specialist)  
**Ngày thực hiện**: 11/08/2026  
**Thư mục làm việc**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_2`  

---

## 1. Tổng Quan Mục Tiêu & Phạm Vi Phân Tích

Phase E bổ sung tính năng **RAG Chatbot kèm Trích dẫn (Citations)** và **Quản lý Lịch sử Trò chuyện** vào Backend FastAPI của hệ thống. Phân tích này tập trung vào 5 trụ cột cốt lõi:

1. **LLM Provider Adapter Pattern**: Thiết kế interface `AbstractLLMProvider` cho phép hoán đổi giữa `OllamaLLMProvider` (Qwen2.5 / Llama-3.1 local) và `MockLLMProvider` (dùng cho CI / Unit Test không cần chạy daemon Ollama).
2. **LangChain & Search Module Pipeline**: Tích hợp module tìm kiếm RRF Hybrid sẵn có (`app/modules/search/service.py`) với pipeline LangChain, phân quyền RBAC theo scope tài liệu (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
3. **SSE (Server-Sent Events) Streaming Response**: Định dạng sự kiện trực tiếp qua FastAPI `StreamingResponse(..., media_type="text/event-stream")` trả về từng token và citation real-time (`event: token`, `event: citation`, `event: done`, `event: error`).
4. **Citation Tracking & Spec Compliance**: Đảm bảo cấu trúc trích dẫn tuân thủ tuyệt đối quy định trong `docs/domain/citation-spec.md` (bao gồm `document_id`, `document_version_id`, `title`, `page_number`, `chunk_id`, `quote`, `score`, `bbox`).
5. **Database Schema & CRUD Chat API**: Mô hình ORM (`ChatSession`, `ChatMessage`), kế hoạch migration Alembic (`0006_chat_sessions_and_messages.py`), và hệ thống API CRUD lịch sử hội thoại.

---

## 2. Kiến Trúc LLM Provider Adapter Pattern

### 2.1 Mẫu Thiết Kế (Adapter / Strategy Pattern)

Nhằm đảm bảo nguyên tắc SOLID (Single Responsibility, Dependency Inversion, Open/Closed), dịch vụ LLM không phụ thuộc trực tiếp vào SDK Ollama hay bất kỳ thư viện bên ngoài nào, mà thông qua một Abstract Base Class.

```
                    ┌─────────────────────────┐
                    │   AbstractLLMProvider   │ (app/services/llm/base.py)
                    └────────────▲────────────┘
                                 │
            ┌────────────────────┴────────────────────┐
            │                                         │
┌───────────────────────┐                 ┌───────────────────────┐
│   OllamaLLMProvider   │                 │    MockLLMProvider    │
│(app/services/llm/     │                 │(app/services/llm/     │
│   ollama.py)          │                 │   mock.py)            │
└───────────────────────┘                 └───────────────────────┘
```

### 2.2 Chi Tiết Interface `AbstractLLMProvider`

```python
# app/services/llm/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator

class AbstractLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        """Sinh văn bản phản hồi đồng bộ (full response)."""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Sinh văn bản phản hồi dạng stream (từng token delta)."""
        pass
```

### 2.3 `OllamaLLMProvider` Implementation

Sử dụng `httpx.AsyncClient` hoặc LangChain `ChatOllama` kết nối đến endpoint Ollama local (`http://localhost:11434/api/chat` hoặc `/api/generate`).

```python
# app/services/llm/ollama.py
from typing import AsyncGenerator
import httpx
from structlog import get_logger
from app.services.llm.base import AbstractLLMProvider

_logger = get_logger(__name__)

class OllamaLLMProvider(AbstractLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "qwen2.5:7b", timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                *([{"role": "system", "content": system_prompt}] if system_prompt else []),
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
            return data.get("message", {}).get("content", "")

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model_name,
            "messages": [
                *([{"role": "system", "content": system_prompt}] if system_prompt else []),
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    import json
                    chunk = json.loads(line)
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        yield delta
```

### 2.4 `MockLLMProvider` (Cho Testing / Continuous Integration)

```python
# app/services/llm/mock.py
import asyncio
from typing import AsyncGenerator
from app.services.llm.base import AbstractLLMProvider

class MockLLMProvider(AbstractLLMProvider):
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        return f"Theo quy định hiện hành đối với câu hỏi '{prompt}': Sinh viên cần tuân thủ đúng các bước hướng dẫn."

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        response_text = f"Theo quy định hiện hành đối với câu hỏi '{prompt}': Sinh viên cần tuân thủ đúng các bước hướng dẫn."
        tokens = response_text.split(" ")
        for i, token in enumerate(tokens):
            await asyncio.sleep(0.01)
            yield token + (" " if i < len(tokens) - 1 else "")
```

### 2.5 Dynamic LLM Factory & Config Updates

Cần cập nhật `app/core/config.py` để bổ sung các cấu hình LLM:

```python
# Sửa app/core/config.py
class Settings(BaseSettings):
    ...
    # ---- LLM & RAG Chatbot ----
    llm_provider: Literal["ollama", "mock"] = "mock"
    llm_ollama_base_url: str = "http://localhost:11434"
    llm_ollama_model_name: str = "qwen2.5:7b"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = 60.0
```

Dịch vụ khởi tạo provider qua factory:

```python
# app/services/llm/factory.py
from app.core.config import get_settings
from app.services.llm.base import AbstractLLMProvider
from app.services.llm.ollama import OllamaLLMProvider
from app.services.llm.mock import MockLLMProvider

def get_llm_provider() -> AbstractLLMProvider:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return OllamaLLMProvider(
            base_url=settings.llm_ollama_base_url,
            model_name=settings.llm_ollama_model_name,
            timeout=settings.llm_timeout_seconds,
        )
    return MockLLMProvider()
```

---

## 3. Luồng Xử Lý LangChain RAG & Tích Hợp Search Module

### 3.1 Sơ Đồ Tuần Tự (Sequence Diagram)

```
User (Client)            FastAPI Router             Search Service          LLM Provider
     │                         │                          │                      │
     │── POST /chat/stream ───►│                          │                      │
     │                         │── 1. Check RBAC Scopes ─►│                      │
     │                         │── 2. search_documents() ─►│                      │
     │                         │◄─ 3. Top-k Chunks + Meta─│                      │
     │                         │                          │                      │
     │                         │── 4. Build Prompt Template ────────────────────►│
     │◄── SSE event: citation ─│   (Trích xuất Citations) │                      │
     │◄── SSE event: token ────│◄── 5. Stream Tokens ─────────────────────────────│
     │◄── SSE event: token ────│◄── Stream...             │                      │
     │                         │                          │                      │
     │◄── SSE event: done ─────│── 6. Save DB History ────│                      │
```

### 3.2 Tích Hợp Search Service (`app/modules/search/service.py`)

Hàm `search_documents()` sẵn có trong `app/modules/search/service.py` trả về `SearchResponse` với danh sách `SearchResultItem`.

Trong RAG Chatbot Service:
1. Xác định `allowed_scopes` dựa vào `current_user.role`:
   - `ADMIN` & `STAFF`: `["PUBLIC", "STUDENT_AFFAIRS", "INTERNAL"]`
   - `STUDENT`: `["PUBLIC", "STUDENT_AFFAIRS"]`
2. Gọi `search_documents(session=db, query=user_message, allowed_scopes=allowed_scopes, top_k=5, alpha=0.6)`.
3. Kiểm tra độ tương đồng tốt nhất:
   - Nếu `not search_res.items` hoặc điểm `search_res.items[0].score < MIN_RAG_SCORE_THRESHOLD` (ví dụ 0.25): Set `has_sufficient_evidence = False`.
   - Nếu đủ bằng chứng: Set `has_sufficient_evidence = True`.

### 3.3 Prompt Template & Grounding

```python
SYSTEM_PROMPT = """Bạn là Trợ lý AI thông minh về Công tác Sinh viên của Trường Đại học.
Nhiệm vụ của bạn là giải đáp các thắc mắc của sinh viên và cán bộ dựa trên các văn bản quy định được cung cấp.

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng thông tin trong phần CONTEXT dưới đây để trả lời.
2. Nếu thông tin KHÔNG có trong CONTEXT, hãy trả lời rõ ràng: "Tôi không tìm thấy thông tin phù hợp trong các văn bản quy định hiện hành." Không tự suy đoán hay bịa đặt.
3. Trả lời mạch lạc, chính xác, lịch sự và dễ hiểu. Có thể dùng danh sách dạng gạch đầu dòng để làm rõ nội dung."""

def build_rag_prompt(user_query: str, search_items: list[SearchResultItem], history_messages: list[dict] = None) -> str:
    context_str = ""
    for idx, item in enumerate(search_items, 1):
        context_str += f"\n--- Nguồn [{idx}]: {item.document_title} (Trang {item.page_number}) ---\n{item.text}\n"

    history_str = ""
    if history_messages:
        for msg in history_messages[-6:]: # Lấy 3 lượt hội thoại gần nhất
            role_label = "Sinh viên" if msg["role"] == "user" else "Trợ lý AI"
            history_str += f"{role_label}: {msg['content']}\n"

    prompt = f"HỒ SƠ TÀI LIỆU KHAM KHẢO (CONTEXT):{context_str}\n\n"
    if history_str:
        prompt += f"LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY:\n{history_str}\n\n"
    prompt += f"CÂU HỎI MỚI CỦA USER: {user_query}\nTRẢ LỜI:"
    return prompt
```

---

## 4. Định Dạng Chuẩn Streaming SSE (Server-Sent Events)

FastAPI hỗ trợ trả về `StreamingResponse` với MIME type `text/event-stream`.

### 4.1 Đóng Gói SSE Event Format

Định dạng chuẩn W3C SSE:
```
event: <event_name>
data: <json_string>

```

### 4.2 Chi Tiết Các Event Type

1. **`event: citation`**: Trả về ngay ở đầu stream (trước khi gen token) để UI hiển thị các chip trích dẫn ngay lập tức.
   ```http
   event: citation
   data: {"document_id": "018f2d5e-...", "document_version_id": "018f2d5e-...", "title": "Quy chế Đánh giá Kết quả Rèn luyện", "page_number": 1, "chunk_id": "018f2d5e-...", "quote": "Sinh viên hoàn thành chương trình...", "score": 0.94, "bbox": [10.0, 20.0, 500.0, 150.0]}
   ```
2. **`event: token`**: Phát ra khi LLM trả về mỗi token mới.
   ```http
   event: token
   data: {"delta": "Theo "}
   ```
3. **`event: done`**: Phát ra khi kết thúc luồng generation, kèm thông tin session & message ID và cờ bằng chứng.
   ```http
   event: done
   data: {"session_id": "018f2d5e-...", "message_id": "018f2d5e-...", "has_sufficient_evidence": true}
   ```
4. **`event: error`**: Trả về nếu xảy ra lỗi trong quá trình sinh phản hồi.
   ```http
   event: error
   data: {"code": "LLM_GENERATION_FAILED", "message": "Không thể kết nối tới mô hình AI."}
   ```

---

## 5. Quy Chuẩn Trích Dẫn (Citation Tracking & Specification)

Tuân thủ tuyệt đối quy định trong `docs/domain/citation-spec.md`:

### 5.1 Structure Schema (`Citation`)

```python
class CitationSchema(BaseModel):
    document_id: str = Field(..., description="UUID tài liệu gốc")
    document_version_id: str = Field(..., description="UUID phiên bản tài liệu")
    title: str = Field(..., description="Tiêu đề tài liệu hiện tại (resolved at query time)")
    page_number: int = Field(..., description="Trang PDF gốc (1-based)")
    chunk_id: str = Field(..., description="UUID chunk embedding")
    quote: str = Field(..., description="Trích nguyên văn (tối đa 300 ký tự)")
    score: float = Field(..., description="Điểm tương đồng (0.0..1.0)")
    bbox: list[float] | None = Field(None, description="[x0, y0, x1, y1] PDF coordinate")
```

### 5.2 Các Quy Tắc Bắt Buộc Khi Tạo Citation

1. **Title Resolution**: Lấy tiêu đề tài liệu trực tiếp từ kết quả `SearchResultItem.document_title`.
2. **Quote Truncation**: Trích nguyên văn đoạn text của chunk, cắt tối đa **300 ký tự** tại ranh giới từ (word boundary), bổ sung `"..."` nếu bị cắt.
3. **Score Normalization**: Làm tròn điểm 2 chữ số thập phân (`round(item.score, 2)`).
4. **Bbox Handling**: Giữ lại mảng 4 phần tử `[x0, y0, x1, y1]` nếu từ OCR block, hoặc `None` nếu PDF text.
5. **Sufficiency Check**: Khi `has_sufficient_evidence == False`, mảng `citations` trả về là mảng rỗng `[]`.

---

## 6. Thiết Kế Cơ Sở Dữ Liệu & Migrations Alembic

### 6.1 Bảng `chat_sessions` (ORM: `ChatSession`)

Lưu trữ các phiên trò chuyện của người dùng.

```python
# app/models/chat_session.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.user import User

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, comment="Chat Session ID (UUID v4)"
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID người sở hữu phiên chat",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Cuộc trò chuyện mới",
        comment="Tiêu đề phiên trò chuyện",
    )
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="qwen2.5:7b",
        comment="Mô hình LLM được sử dụng",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Thời điểm xóa mềm (soft delete)",
    )

    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )
```

### 6.2 Bảng `chat_messages` (ORM: `ChatMessage`)

Lưu trữ thông điệp từng lượt (user và assistant).

```python
# app/models/chat_message.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, comment="Message ID (UUID v4)"
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID phiên trò chuyện chứa message này",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Vai trò người gửi (user | assistant | system)",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Nội dung văn bản tin nhắn",
    )
    citations: Mapped[Any | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="Danh sách các trích dẫn (chỉ có ở role=assistant)",
    )
    has_sufficient_evidence: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        default=True,
        comment="Cờ đánh giá đủ bằng chứng từ tài liệu tham khảo",
    )
    tokens_used: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Số token ước tính sử dụng",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[ChatSession] = relationship("ChatSession", back_populates="messages")
```

### 6.3 Alembic Migration Plan (`0006_chat_sessions_and_messages.py`)

Thứ tự thực hiện migration:
1. Tạo bảng `chat_sessions` kèm các khoá ngoại `users.id` (CASCADE) và index `ix_chat_sessions_user_updated`.
2. Tạo bảng `chat_messages` kèm khoá ngoại `chat_sessions.id` (CASCADE) và index `ix_chat_messages_session_created`.

---

## 7. Thiết Kế Hệ Thống Endpoints API & Schemas (`app/modules/chat/`)

### 7.1 Danh Sách Endpoints RESTful

| Method | Endpoint | Mô Tả | Phân Quyền (RBAC) |
|---|---|---|---|
| `POST` | `/api/v1/chat/sessions` | Tạo một phiên trò chuyện mới | Authenticated Users |
| `GET` | `/api/v1/chat/sessions` | Danh sách phiên trò chuyện của user hiện tại | Authenticated Users |
| `GET` | `/api/v1/chat/sessions/{id}` | Lấy chi tiết phiên trò chuyện | Owner Only |
| `DELETE` | `/api/v1/chat/sessions/{id}` | Xóa mềm (soft delete) phiên trò chuyện | Owner Only |
| `GET` | `/api/v1/chat/sessions/{id}/messages` | Lấy lịch sử tin nhắn của phiên | Owner Only |
| `POST` | `/api/v1/chat/sessions/{id}/messages` | Gửi tin nhắn & sinh câu trả lời đồng bộ (JSON) | Owner Only |
| `POST` | `/api/v1/chat/sessions/{id}/messages/stream` | Gửi tin nhắn & stream câu trả lời (SSE) | Owner Only |
| `POST` | `/api/v1/chat/query` | Stateless query (tương thích mock cũ) | Authenticated Users |

### 7.2 API Schemas (`app/modules/chat/schemas.py`)

```python
class CreateSessionRequest(BaseModel):
    title: str | None = Field(None, max_length=255, description="Tiêu đề phiên (tùy chọn)")

class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    model_name: str
    created_at: datetime
    updated_at: datetime

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: list[CitationSchema] = []
    has_sufficient_evidence: bool = True
    created_at: datetime

class SendMessageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="Nội dung câu hỏi của người dùng")

class ChatQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)

class ChatQueryResponse(BaseModel):
    answer: str
    citations: list[CitationSchema]
    has_sufficient_evidence: bool
```

---

## 8. Kế Hoạch Triển Khai Step-by-Step (Cho Implementer)

### Bước 1: Mở Rộng Config & LLM Service Layer
1. Cập nhật `app/core/config.py` bổ sung các trường cấu hình `llm_*`.
2. Tạo module `app/services/llm/` gồm:
   - `base.py` (`AbstractLLMProvider`)
   - `ollama.py` (`OllamaLLMProvider`)
   - `mock.py` (`MockLLMProvider`)
   - `factory.py` (`get_llm_provider()`)
3. Đăng ký test unit cho LLM providers trong `tests/test_llm_provider.py`.

### Bước 2: Tạo Models ORM & Migration Alembic
1. Tạo `app/models/chat_session.py` & `app/models/chat_message.py`.
2. Khai báo re-export trong `app/models/__init__.py`.
3. Tạo file migration Alembic `alembic/versions/0006_chat_sessions_and_messages.py`.
4. Viết test khởi tạo bảng trong `tests/test_chat_models.py`.

### Bước 3: Triển Khai Core Chat RAG Service & Router
1. Tạo `app/modules/chat/` gồm:
   - `schemas.py`
   - `service.py` (`execute_rag_chat()`, `stream_rag_chat()`)
   - `dependencies.py` (Validate owner session)
   - `router.py`
2. Tích hợp `router` vào `app/main.py`.

### Bước 4: Viết Test Integration & E2E Verification
1. Viết suite pytest `tests/test_chat_router.py` bao phủ:
   - CRUD sessions
   - SSE streaming responses (`test_chat_stream_sse`)
   - Citation matching `docs/domain/citation-spec.md`
   - Phân quyền RBAC khi chat (Student không được cite tài liệu scope `INTERNAL`).

---

## 9. Đánh Giá Rủi Ro & Biện Pháp Giảm Thường (Risk Assessment)

1. **Rủi ro Ollama local offline trên dev machine**:
   - *Giảm thiểu*: Thiết lập `llm_provider="mock"` mặc định ở dev/test. Khi chạy test pytest hoặc CI, `MockLLMProvider` phản hồi tức thì không cần Ollama service.
2. **Rủi ro SSE Stream bị gián đoạn kết nối**:
   - *Giảm thiểu*: Đóng gói khối `try...except` toàn cục trong generator, gửi event `event: error` trước khi kết thúc response stream.
3. **Rủi ro rò rỉ dữ liệu nhạy cảm (RBAC Leak)**:
   - *Giảm thiểu*: Truyền trực tiếp `allowed_scopes` vào `search_documents()` trước khi retrieval, chặn từ gốc dữ liệu không có quyền xem.

---
