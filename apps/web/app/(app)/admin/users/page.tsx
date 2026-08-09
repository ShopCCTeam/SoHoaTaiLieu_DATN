"use client";

import React from "react";
import { useAdminUsers } from "@/lib/api/queries";
import { Users, Shield, Plus, Lock } from "lucide-react";
import { useAuthStore } from "@/lib/auth/session";

export default function AdminUsersPage() {
  const { user } = useAuthStore();
  const { data: users = [], isLoading, error } = useAdminUsers();

  if (user?.role !== "admin") {
    return (
      <div className="max-w-xl mx-auto my-12 glass-panel p-8 rounded-3xl border border-rose-200 text-center space-y-4 shadow-rose-subtle">
        <div className="w-14 h-14 rounded-2xl bg-rose-100 dark:bg-rose-950 flex items-center justify-center text-rose-600 mx-auto">
          <Lock className="w-7 h-7 stroke-current" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          403 - Giới Hạn Quyền Quản Trị Viên
        </h2>
        <p className="text-xs text-muted-foreground">
          Chức năng Quản lý User & Phân quyền Role chỉ dành cho tài khoản Admin.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-rose-100 text-rose-800 text-[11px] font-bold">
            <Shield className="w-3.5 h-3.5 stroke-current text-rose-600" />
            <span>Hệ Thống Phân Quyền RBAC (Phase F6 Active)</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">
            Quản lý Người dùng & Phân quyền Role
          </h1>
        </div>

        <button
          aria-label="Thêm tài khoản người dùng mới"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:bg-primary-500 transition-all"
        >
          <Plus className="w-4 h-4 stroke-current" />
          <span>Thêm User Mới</span>
        </button>
      </div>

      {/* Users Table */}
      <div className="glass-panel rounded-3xl border border-primary-200/80 overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-8 h-8 border-4 border-primary-300 border-t-primary-600 rounded-full animate-spin mx-auto" />
            <p className="text-xs text-muted-foreground">Đang lấy danh sách người dùng...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-primary-100 dark:border-slate-800 bg-primary-50/50 dark:bg-slate-900/80 text-slate-600 dark:text-slate-300 uppercase text-[10px] tracking-wider font-bold">
                  <th className="py-3 px-4">Họ và tên / Email</th>
                  <th className="py-3 px-4">Đơn vị / Khoa</th>
                  <th className="py-3 px-4">Quyền hạn (Role)</th>
                  <th className="py-3 px-4">Trạng thái</th>
                  <th className="py-3 px-4 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-primary-100/60 dark:divide-slate-800/60">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-primary-50/40 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900 dark:text-white">{u.fullName}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">{u.email}</div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300 font-medium">
                      {u.department}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2.5 py-1 rounded-lg bg-primary-100 text-slate-900 font-bold uppercase text-[10px]">
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-semibold">
                        {u.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button aria-label="Sửa thông tin user" className="px-3 py-1 rounded-lg bg-white dark:bg-slate-800 border border-primary-200 text-slate-900 dark:text-white font-bold text-xs hover:bg-primary-100 transition-all">
                        Chỉnh sửa
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
