import { describe, it, expect } from "vitest";
import { hasPermission, ROLE_PERMISSIONS_MATRIX } from "@/lib/auth/permissions";

describe("RBAC Permission Matrix", () => {
  describe("Admin role", () => {
    it("có toàn quyền", () => {
      expect(hasPermission("admin", "canViewAllDocuments")).toBe(true);
      expect(hasPermission("admin", "canUploadDocuments")).toBe(true);
      expect(hasPermission("admin", "canEditOCR")).toBe(true);
      expect(hasPermission("admin", "canApproveDocument")).toBe(true);
      expect(hasPermission("admin", "canAccessAdminPanel")).toBe(true);
      expect(hasPermission("admin", "canChatRAG")).toBe(true);
      expect(hasPermission("admin", "scopedOnly")).toBe(false);
    });
  });

  describe("Staff role", () => {
    it("có quyền xem/upload/edit/approve", () => {
      expect(hasPermission("staff", "canViewAllDocuments")).toBe(true);
      expect(hasPermission("staff", "canUploadDocuments")).toBe(true);
      expect(hasPermission("staff", "canEditOCR")).toBe(true);
      expect(hasPermission("staff", "canApproveDocument")).toBe(true);
      expect(hasPermission("staff", "canChatRAG")).toBe(true);
    });

    it("KHÔNG có quyền admin panel", () => {
      expect(hasPermission("staff", "canAccessAdminPanel")).toBe(false);
    });
  });

  describe("Student role", () => {
    it("KHÔNG có quyền upload/edit/approve/admin", () => {
      expect(hasPermission("student", "canViewAllDocuments")).toBe(false);
      expect(hasPermission("student", "canUploadDocuments")).toBe(false);
      expect(hasPermission("student", "canEditOCR")).toBe(false);
      expect(hasPermission("student", "canApproveDocument")).toBe(false);
      expect(hasPermission("student", "canAccessAdminPanel")).toBe(false);
    });

    it("CÓ quyền chat RAG (chỉ trên scope được phép)", () => {
      expect(hasPermission("student", "canChatRAG")).toBe(true);
      expect(hasPermission("student", "scopedOnly")).toBe(true);
    });
  });

  describe("Edge cases", () => {
    it("trả về false khi role undefined", () => {
      expect(hasPermission(undefined, "canViewAllDocuments")).toBe(false);
      expect(hasPermission(undefined, "canUploadDocuments")).toBe(false);
    });

    it("ma trận phải đủ 3 role", () => {
      expect(Object.keys(ROLE_PERMISSIONS_MATRIX)).toEqual(
        expect.arrayContaining(["admin", "staff", "student"])
      );
    });
  });
});
