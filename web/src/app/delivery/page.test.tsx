import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import DeliveryPage, { metadata } from "@/app/delivery/page";

describe("/delivery — Razorpay's delivery page", () => {
  it("says access is digital and immediate, nothing is shipped, and links the refund policy and terms", () => {
    render(<DeliveryPage />);
    expect(screen.getByRole("heading", { level: 1, name: "Delivery" })).toBeInTheDocument();
    expect(screen.getByText(/Access starts the moment your payment is confirmed/)).toBeInTheDocument();
    expect(screen.getByText(/Nothing is shipped/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Refund policy" })).toHaveAttribute("href", "/refunds");
    expect(screen.getByRole("link", { name: "Terms of service" })).toHaveAttribute("href", "/terms");
    expect(metadata.alternates?.canonical).toBe("/delivery");
    expect(metadata.openGraph?.url).toBe("/delivery");
  });
});
