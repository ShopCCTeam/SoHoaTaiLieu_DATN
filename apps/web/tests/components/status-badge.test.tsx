import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import React from "react";
import { StatusBadge } from "@/components/documents/status-badge";

describe("StatusBadge Component", () => {
  it("renders correctly for approved status", () => {
    render(<StatusBadge status="approved" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Đã Ban Hành");
  });

  it("renders correctly for review status", () => {
    render(<StatusBadge status="review" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Chờ Hiệu Chỉnh");
  });

  it("renders correctly for processing status", () => {
    render(<StatusBadge status="processing" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Đang Xử Lý OCR");
  });
});
