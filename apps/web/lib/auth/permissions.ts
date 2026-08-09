import { UserRole } from "../api/types";

export interface RolePermissions {
  canViewAllDocuments: boolean;
  canUploadDocuments: boolean;
  canEditOCR: boolean;
  canApproveDocument: boolean;
  canAccessAdminPanel: boolean;
  canChatRAG: boolean;
  scopedOnly: boolean;
}

export const ROLE_PERMISSIONS_MATRIX: Record<UserRole, RolePermissions> = {
  admin: {
    canViewAllDocuments: true,
    canUploadDocuments: true,
    canEditOCR: true,
    canApproveDocument: true,
    canAccessAdminPanel: true,
    canChatRAG: true,
    scopedOnly: false,
  },
  staff: {
    canViewAllDocuments: true,
    canUploadDocuments: true,
    canEditOCR: true,
    canApproveDocument: true,
    canAccessAdminPanel: false,
    canChatRAG: true,
    scopedOnly: false,
  },
  student: {
    canViewAllDocuments: false,
    canUploadDocuments: false,
    canEditOCR: false,
    canApproveDocument: false,
    canAccessAdminPanel: false,
    canChatRAG: true,
    scopedOnly: true,
  },
};

export function hasPermission(
  role: UserRole | undefined,
  permission: keyof RolePermissions
): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS_MATRIX[role]?.[permission] ?? false;
}
