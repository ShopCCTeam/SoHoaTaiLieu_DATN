import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import React from "react";
import { StatusBadge } from "@/components/documents/status-badge";

describe("StatusBadge Component", () => {
  it("renders correctly for APPROVED status", () => {
    render(<StatusBadge status="APPROVED" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Đã Ban Hành");
  });

  it("renders correctly for UNDER_REVIEW status", () => {
    render(<StatusBadge status="UNDER_REVIEW" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Chờ Hiệu Chỉnh");
  });

  it("renders correctly for DRAFT status", () => {
    render(<StatusBadge status="DRAFT" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Bản Nháp");
  });
});