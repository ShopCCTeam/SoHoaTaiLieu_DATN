"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuthStore, DEMO_USERS } from "@/lib/auth/session";
import { UserRole } from "@/lib/api/types";
import { BookOpen, Shield, UserCheck, GraduationCap, ArrowRight, Lock, Mail, Sparkles } from "lucide-react";

const loginSchema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(6, "Mật khẩu tối thiểu 6 ký tự"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [selectedRole, setSelectedRole] = useState<UserRole>("admin");
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: DEMO_USERS.admin.email,
      password: "password123",
    },
  });

  const handleSelectDemoRole = (role: UserRole) => {
    setSelectedRole(role);
    setValue("email", DEMO_USERS[role].email);
  };

  const onSubmit = (data: LoginFormValues) => {
    setLoading(true);
    setTimeout(() => {
      login(data.email, selectedRole);
      setLoading(false);
      router.push("/dashboard");
    }, 500);
  };

  return (
    <div className="w-full max-w-md">
      <div className="glass-panel p-8 rounded-3xl border border-primary-200/90 shadow-rose-glow backdrop-blur-xl relative overflow-hidden">
        {/* Glow Ambient Top Accent */}
        <div className="absolute -top-16 -right-16 w-32 h-32 bg-primary-300 rounded-full blur-3xl opacity-60" />
        
        {/* Header */}
        <div className="text-center space-y-3 mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-300 via-primary-400 to-rose-400 text-slate-900 shadow-rose-subtle mb-1">
            <BookOpen className="w-7 h-7 stroke-current" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
              Số hóa Tài liệu CTSV
            </h1>
            <p className="text-xs text-muted-foreground mt-1">
              Ứng dụng OCR, RAG & LangChain — Đồ án Tốt nghiệp
            </p>
          </div>
        </div>

        {/* Demo Account Quick Switchers */}
        <div className="mb-6 space-y-2">
          <label className="text-[11px] font-bold tracking-wider text-muted-foreground uppercase flex items-center gap-1">
            <Sparkles className="w-3 h-3 stroke-current text-primary-600" />
            <span>Chọn nhanh tài khoản Demo (Role):</span>
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[
              { role: "admin" as UserRole, label: "Admin", icon: Shield },
              { role: "staff" as UserRole, label: "Staff", icon: UserCheck },
              { role: "student" as UserRole, label: "Student", icon: GraduationCap },
            ].map((item) => {
              const Icon = item.icon;
              const isSelected = selectedRole === item.role;
              return (
                <button
                  key={item.role}
                  type="button"
                  onClick={() => handleSelectDemoRole(item.role)}
                  className={`flex flex-col items-center justify-center p-2.5 rounded-xl border text-xs font-semibold transition-all ${
                    isSelected
                      ? "border-primary-400 bg-primary-200/80 text-slate-950 shadow-sm"
                      : "border-primary-100 bg-white/50 text-slate-600 hover:bg-primary-50"
                  }`}
                >
                  <Icon className="w-4 h-4 stroke-current mb-1" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Email trường / tài khoản:
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 stroke-current text-slate-400" />
              <input
                {...register("email")}
                type="email"
                className="w-full h-11 pl-10 pr-4 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 transition-all"
                placeholder="name@phenikaa-uni.edu.vn"
              />
            </div>
            {errors.email && (
              <p className="text-[11px] text-rose-600 mt-1">{errors.email.message}</p>
            )}
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Mật khẩu:
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 stroke-current text-slate-400" />
              <input
                {...register("password")}
                type="password"
                className="w-full h-11 pl-10 pr-4 rounded-xl border border-primary-200 bg-white/80 dark:bg-slate-900/80 text-xs focus:outline-none focus:ring-2 focus:ring-primary-400 transition-all"
              />
            </div>
            {errors.password && (
              <p className="text-[11px] text-rose-600 mt-1">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 mt-2 rounded-xl bg-gradient-to-r from-primary-400 via-primary-500 to-rose-400 text-slate-950 font-bold text-xs shadow-rose-subtle hover:shadow-rose-glow transition-all flex items-center justify-center gap-2 active:scale-[0.98] disabled:opacity-50"
          >
            {loading ? (
              <span>Đang đăng nhập...</span>
            ) : (
              <>
                <span>Vào Hệ Thống</span>
                <ArrowRight className="w-4 h-4 stroke-current" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
