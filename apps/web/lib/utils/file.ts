export function validateFile(file: File): { valid: boolean; error?: string } {
  const allowedTypes = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ];

  const maxSize = 50 * 1024 * 1024; // 50MB limit

  if (file.type && !allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: "Định dạng file không hỗ trợ. Vui lòng chọn PDF, PNG, JPG, WEBP hoặc DOCX.",
    };
  }

  if (file.size > maxSize) {
    return {
      valid: false,
      error: "Dung lượng file vượt quá giới hạn 50MB.",
    };
  }

  return { valid: true };
}

/**
 * Validates PDF Magic Bytes (%PDF- signature 0x25 0x50 0x44 0x46)
 * Prevents malicious file renaming attacks (e.g. .exe renamed to .pdf)
 */
export async function validateFileMagicBytes(file: File): Promise<{ valid: boolean; error?: string }> {
  if (file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf") {
    try {
      // Đọc toàn bộ file rồi lấy 4 byte đầu — an toàn hơn file.slice(0,4).arrayBuffer()
      // vì jsdom / một số môi trường không có sẵn Blob.slice().arrayBuffer().
      const buffer = await file.arrayBuffer();
      const bytes = new Uint8Array(buffer.slice(0, 4));
      const header = new TextDecoder("ascii").decode(bytes);
      if (header !== "%PDF") {
        return {
          valid: false,
          error: "Tập tin PDF không hợp lệ (Không khớp chữ ký header %PDF-). Vui lòng không đổi đuôi tập tin thực thi.",
        };
      }
    } catch {
      return { valid: false, error: "Không thể đọc cấu trúc header tập tin." };
    }
  }
  return { valid: true };
}

export async function calculateChecksum(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", new Uint8Array(buffer));
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  return `sha256_${hashHex}`;
}
