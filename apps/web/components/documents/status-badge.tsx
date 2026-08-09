import React from "react";
import { DocumentStatus } from "@/lib/api/types";
import { getStatusLabel, getStatusBadgeVariant } from "@/lib/utils/format";
import { CheckCircle2, Clock, FileText, AlertTriangle } from "lucide-react";

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
      case "APPROVED":
        return <CheckCircle2 className={iconClass} aria-hidden="true" />;
      case "UNDER_REVIEW":
        return <Clock className={iconClass} aria-hidden="true" />;
      case "DRAFT":
        return <FileText className={iconClass} aria-hidden="true" />;
      case "ARCHIVED":
        return <AlertTriangle className={iconClass} aria-hidden="true" />;
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
