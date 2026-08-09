"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
  ColumnDef,
} from "@tanstack/react-table";
import { Document, DocumentStatus, DocumentType } from "@/lib/api/types";
import { StatusBadge } from "./status-badge";
import { formatDate, formatFileSize } from "@/lib/utils/format";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  Edit3,
  RotateCcw,
} from "lucide-react";

interface DocumentTableProps {
  initialDocuments: Document[];
}

export const DocumentTable: React.FC<DocumentTableProps> = ({
  initialDocuments,
}) => {
  const [data, setData] = useState<Document[]>(initialDocuments);
  const [globalFilter, setGlobalFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [typeFilter, setTypeFilter] = useState<string>("ALL");

  const filteredData = useMemo(() => {
    return data.filter((doc) => {
      const matchesGlobal =
        !globalFilter ||
        doc.title.toLowerCase().includes(globalFilter.toLowerCase()) ||
        doc.codeNumber?.toLowerCase().includes(globalFilter.toLowerCase()) ||
        doc.issuingBody?.toLowerCase().includes(globalFilter.toLowerCase()) ||
        doc.tags.some((t) => t.toLowerCase().includes(globalFilter.toLowerCase()));

      const matchesStatus = statusFilter === "ALL" || doc.status === statusFilter;
      const matchesType = typeFilter === "ALL" || doc.type === typeFilter;

      return matchesGlobal && matchesStatus && matchesType;
    });
  }, [data, globalFilter, statusFilter, typeFilter]);

  const columns = useMemo<ColumnDef<Document>[]>(
    () => [
      {
        accessorKey: "title",
        header: "Tên văn bản / Số hiệu",
        cell: ({ row }) => {
          const doc = row.original;
          return (
            <div className="space-y-1 py-1">
              <Link
                href={`/documents/${doc.id}`}
                className="font-bold text-slate-900 dark:text-white hover:text-primary-700 dark:hover:text-primary-300 transition-colors line-clamp-2"
              >
                {doc.title}
              </Link>
              <div className="flex items-center gap-2 text-[10px]">
                <span className="font-mono bg-primary-100/70 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-800 dark:text-slate-200 border border-primary-200 dark:border-slate-700">
                  {doc.codeNumber || doc.id}
                </span>
                <span className="text-slate-500 dark:text-slate-400 font-medium">• Scope: {doc.scope}</span>
              </div>
            </div>
          );
        },
      },
      {
        accessorKey: "type",
        header: "Loại văn bản",
        cell: ({ row }) => (
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 font-semibold text-[11px] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-700">
            {row.original.type}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Trạng thái",
        cell: ({ row }) => <StatusBadge status={row.original.status} />,
      },
      {
        accessorKey: "issuingBody",
        header: "Đơn vị ban hành",
        cell: ({ row }) => (
          <span className="text-slate-800 dark:text-slate-200 font-medium">
            {row.original.issuingBody || "—"}
          </span>
        ),
      },
      {
        accessorKey: "effectiveFrom",
        header: "Ngày ban hành",
        cell: ({ row }) => (
          <span className="text-slate-600 dark:text-slate-400 font-mono text-[11px]">
            {formatDate(row.original.effectiveFrom || row.original.createdAt)}
          </span>
        ),
      },
      {
        id: "actions",
        header: () => <div className="text-right">Thao tác</div>,
        cell: ({ row }) => {
          const doc = row.original;
          return (
            <div className="flex items-center justify-end gap-1.5">
              {doc.status === "review" ? (
                <Link
                  href={`/documents/${doc.id}/review`}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-amber-500 text-white font-bold text-xs hover:bg-amber-600 transition-all shadow-sm"
                >
                  <Edit3 className="w-3.5 h-3.5 stroke-current" />
                  <span>Sửa OCR</span>
                </Link>
              ) : (
                <Link
                  href={`/documents/${doc.id}`}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-800 border border-primary-200 dark:border-slate-700 hover:bg-primary-100 dark:hover:bg-slate-700 text-slate-900 dark:text-white font-bold text-xs transition-all shadow-sm"
                >
                  <Eye className="w-3.5 h-3.5 stroke-current text-slate-600 dark:text-slate-400" />
                  <span>Chi tiết</span>
                </Link>
              )}
            </div>
          );
        },
      },
    ],
    []
  );

  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    initialState: {
      pagination: {
        pageSize: 6,
      },
    },
  });

  return (
    <div className="space-y-4">
      {/* Filter & Controls Panel */}
      <div className="glass-panel p-4 rounded-2xl border border-primary-200/80 dark:border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 shadow-sm">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 stroke-current text-slate-400" />
          <input
            type="text"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Lọc theo tên tài liệu, số hiệu, từ khóa..."
            className="w-full h-10 pl-10 pr-4 rounded-xl border border-primary-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary-400 transition-all"
          />
        </div>

        {/* Status Dropdown */}
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 px-3 rounded-xl border border-primary-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-400"
          >
            <option value="ALL">Tất cả trạng thái (Status)</option>
            <option value="approved">Đã Ban Hành (Approved)</option>
            <option value="review">Chờ Hiệu Chỉnh (Review)</option>
            <option value="processing">Đang Xử Lý (Processing)</option>
            <option value="draft">Bản Nháp (Draft)</option>
            <option value="expired">Hết Hiệu Lực (Expired)</option>
            <option value="failed">Lỗi Xử Lý (Failed)</option>
          </select>

          {/* Type Dropdown */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-10 px-3 rounded-xl border border-primary-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary-400"
          >
            <option value="ALL">Tất cả loại văn bản (Type)</option>
            <option value="QUY_CHE">Quy chế</option>
            <option value="QUY_DINH">Quy định</option>
            <option value="THONG_BAO">Thông báo</option>
            <option value="QUYET_DINH">Quyết định</option>
            <option value="HUONG_DAN">Hướng dẫn</option>
            <option value="MAU_DON">Mẫu đơn</option>
          </select>

          {(statusFilter !== "ALL" || typeFilter !== "ALL" || globalFilter) && (
            <button
              onClick={() => {
                setGlobalFilter("");
                setStatusFilter("ALL");
                setTypeFilter("ALL");
              }}
              aria-label="Đặt lại bộ lọc tìm kiếm"
              className="h-10 px-3 rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 text-xs font-semibold hover:bg-rose-100 transition-all flex items-center gap-1"
              title="Đặt lại bộ lọc"
            >
              <RotateCcw className="w-3.5 h-3.5 stroke-current" />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* TanStack Table Container */}
      <div className="glass-panel rounded-2xl border border-primary-200/80 dark:border-slate-800 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr
                  key={headerGroup.id}
                  className="border-b border-primary-100 dark:border-slate-800 bg-primary-50/50 dark:bg-slate-900/80 text-slate-600 dark:text-slate-300 uppercase text-[10px] tracking-wider font-bold"
                >
                  {headerGroup.headers.map((header) => (
                    <th key={header.id} className="py-3 px-4">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y divide-primary-100/60 dark:divide-slate-800/60">
              {table.getRowModel().rows.length > 0 ? (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="hover:bg-primary-50/40 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="py-3.5 px-4">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="py-12 text-center text-slate-500 dark:text-slate-400 font-medium"
                  >
                    Không tìm thấy văn bản phù hợp với bộ lọc.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-4 py-3 border-t border-primary-100 dark:border-slate-800 flex items-center justify-between gap-4">
          <div className="text-xs text-slate-600 dark:text-slate-400">
            Hiển thị{" "}
            <span className="font-bold text-slate-900 dark:text-white">
              {table.getRowModel().rows.length}
            </span>{" "}
            trên tổng số{" "}
            <span className="font-bold text-slate-900 dark:text-white">
              {filteredData.length}
            </span>{" "}
            tài liệu
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              aria-label="Chuyển sang trang trước"
              className="p-1.5 rounded-lg border border-primary-200 dark:border-slate-700 hover:bg-primary-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none transition-colors"
            >
              <ChevronLeft className="w-4 h-4 stroke-current text-slate-700 dark:text-slate-300" />
            </button>
            <span className="text-xs font-semibold px-2 text-slate-800 dark:text-slate-200">
              Trang {table.getState().pagination.pageIndex + 1} /{" "}
              {table.getPageCount() || 1}
            </span>
            <button
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              aria-label="Chuyển sang trang kế tiếp"
              className="p-1.5 rounded-lg border border-primary-200 dark:border-slate-700 hover:bg-primary-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none transition-colors"
            >
              <ChevronRight className="w-4 h-4 stroke-current text-slate-700 dark:text-slate-300" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
