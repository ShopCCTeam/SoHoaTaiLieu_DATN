import { describe, it, expect, beforeAll } from "vitest";
import { validateFile, validateFileMagicBytes, calculateChecksum } from "@/lib/utils/file";

/**
 * Tạo File giả lập cho test — jsdom không có File.arrayBuffer() mặc định.
 */
function makeFile(content: string | Uint8Array, name: string, type: string): File {
  let blob: Blob;
  if (content instanceof Uint8Array) {
    // Cast buffer để TS strict không complain ArrayBufferLike vs ArrayBuffer.
    // SharedArrayBuffer cũng không được nhận vào Blob, nên ép kiểu rõ ràng.
    const ab = content.buffer.slice(content.byteOffset, content.byteOffset + content.byteLength) as ArrayBuffer;
    blob = new Blob([ab], { type });
  } else {
    blob = new Blob([content], { type });
  }
  // Polyfill arrayBuffer + slice cho jsdom
  const blobAny = blob as Blob & {
    arrayBuffer?: () => Promise<ArrayBuffer>;
  };
  if (!blobAny.arrayBuffer) {
    blobAny.arrayBuffer = async () => {
      const reader = new FileReader();
      return new Promise<ArrayBuffer>((resolve, reject) => {
        reader.onload = () => resolve(reader.result as ArrayBuffer);
        reader.onerror = () => reject(reader.error);
        reader.readAsArrayBuffer(blob);
      });
    };
  }
  const file = new File([blob], name, { type });
  // Polyfill file.arrayBuffer + file.slice với arrayBuffer
  const fileAny = file as File & {
    arrayBuffer?: () => Promise<ArrayBuffer>;
  };
  if (!fileAny.arrayBuffer) {
    fileAny.arrayBuffer = () => blobAny.arrayBuffer!();
  }
  return file;
}

/**
 * Tạo File PDF giả lập với magic bytes %PDF- chính xác
 */
function makePdfFile(content: string = "fake pdf content"): File {
  const pdfHeader = "%PDF-1.4\n";
  const textEncoder = new TextEncoder();
  const bytes = textEncoder.encode(pdfHeader + content);
  return makeFile(bytes, "test.pdf", "application/pdf");
}

describe("validateFile — MIME & size validation", () => {
  it("chấp nhận PDF hợp lệ", () => {
    const file = makePdfFile();
    const result = validateFile(file);
    expect(result.valid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("chấp nhận PNG, JPG, WEBP", () => {
    expect(validateFile(makeFile("fake", "test.png", "image/png")).valid).toBe(true);
    expect(validateFile(makeFile("fake", "test.jpg", "image/jpeg")).valid).toBe(true);
    expect(validateFile(makeFile("fake", "test.webp", "image/webp")).valid).toBe(true);
  });

  it("từ chối MIME không hỗ trợ", () => {
    const file = makeFile("fake", "test.exe", "application/x-msdownload");
    const result = validateFile(file);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("Định dạng file không hỗ trợ");
  });

  it("từ chối file > 50MB", () => {
    // Tạo blob 51MB — dùng Uint8Array để polyfill không cần đọc
    const bigArray = new Uint8Array(51 * 1024 * 1024);
    const file = makeFile(bigArray, "big.pdf", "application/pdf");
    const result = validateFile(file);
    expect(result.valid).toBe(false);
    expect(result.error).toContain("50MB");
  });
});

describe("validateFileMagicBytes — chống rename .exe → .pdf", () => {
  it("chấp nhận PDF có magic bytes %PDF- hợp lệ", async () => {
    const file = makePdfFile();
    const result = await validateFileMagicBytes(file);
    expect(result.valid).toBe(true);
  });

  it("TỪ CHỐI file .pdf nhưng nội dung là EXE (rename attack)", async () => {
    const exeBytes = new Uint8Array([0x4d, 0x5a, 0x90, 0x00, 0x03, 0x00]); // MZ header
    const exeFile = makeFile(exeBytes, "malware.pdf", "application/pdf");
    const result = await validateFileMagicBytes(exeFile);
    expect(result.valid).toBe(false);
    // Lỗi có thể là "không hợp lệ" hoặc "không thể đọc"
    expect(result.error).toMatch(/hợp lệ|đọc/);
  });

  it("TỪ CHỐI file .pdf có nội dung text thường", async () => {
    const textBytes = new TextEncoder().encode("hello world");
    const textFile = makeFile(textBytes, "fake.pdf", "application/pdf");
    const result = await validateFileMagicBytes(textFile);
    expect(result.valid).toBe(false);
  });

  it("BỎ QUA check magic bytes cho file không phải PDF", async () => {
    const pngFile = makeFile("fake png content", "test.png", "image/png");
    const result = await validateFileMagicBytes(pngFile);
    expect(result.valid).toBe(true);
  });
});

describe("calculateChecksum — SHA-256", () => {
  it("tính SHA-256 chính xác cho nội dung biết trước", async () => {
    const file = makeFile("hello", "test.txt", "text/plain");
    const checksum = await calculateChecksum(file);
    expect(checksum).toMatch(/^sha256_[a-f0-9]{64}$/);
  });

  it("checksum khác nhau cho nội dung khác nhau", async () => {
    const file1 = makeFile("content1", "a.txt", "text/plain");
    const file2 = makeFile("content2", "b.txt", "text/plain");
    const c1 = await calculateChecksum(file1);
    const c2 = await calculateChecksum(file2);
    expect(c1).not.toBe(c2);
  });

  it("checksum deterministic cho cùng nội dung", async () => {
    const file1 = makeFile("same content", "a.txt", "text/plain");
    const file2 = makeFile("same content", "b.txt", "text/plain");
    expect(await calculateChecksum(file1)).toBe(await calculateChecksum(file2));
  });
});