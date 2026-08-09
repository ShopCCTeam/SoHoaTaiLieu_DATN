import React from "react";
import { DocumentStatus } from "@/lib/api/types";
import { getStatusLabel, getStatusBadgeVariant } from "@/lib/utils/format";
import { CheckCircle2, Clock, AlertTriangle, FileText, XCircle, RefreshCw } from "lucide-react";

interface StatusBadgeProps {
  status: DocumentStatus;
  className?: string;
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className = "",
  showIcon = true,
}) => {
  const label = getStatusLabel(status);
  const variant = getStatusBadgeVariant(status);

  const renderIcon = () => {
    if (!showIcon) return null;
    const iconClass = "w-3.5 h-3.5 mr-1.5 stroke-current flex-shrink-0";
    switch (status) {
      case "approved":
        return <CheckCircle2 className={iconClass} aria-hidden="true" />;
      case "review":
        return <Clock className={iconClass} aria-hidden="true" />;
      case "processing":
        return <RefreshCw className={`${iconClass} animate-spin`} aria-hidden="true" />;
      case "draft":
        return <FileText className={iconClass} aria-hidden="true" />;
      case "expired":
        return <AlertTriangle className={iconClass} aria-hidden="true" />;
      case "failed":
        return <XCircle className={iconClass} aria-hidden="true" />;
    }
  };

  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${variant.bgClass} ${variant.textClass} ${variant.borderClass} ${className}`}
    >
      {renderIcon()}
      <span>{label}</span>
    </span>
  );
};
