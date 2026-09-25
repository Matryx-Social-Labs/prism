import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { IndicName } from "@/components/landing/IndicName";

describe("IndicName — the name in each script Prism reads", () => {
  it("offers only the scripts the monitored set reads, labelled as transliterations", () => {
    const { container } = render(<IndicName languages={["en", "hi", "ta", "ml"]} />);
    // English, Hindi and Tamil have a set name; Malayalam is read but has none yet, so it is not invented.
    expect(container.querySelectorAll("i")).toHaveLength(3);
    expect(screen.getByRole("img", { name: "Prism, in the scripts it reads" })).toHaveTextContent("Prism");
  });

  it("is the English name, still, when the monitored languages are unknown", () => {
    const { container } = render(<IndicName languages={null} />);
    expect(container.querySelectorAll("i")).toHaveLength(0);
    expect(container.textContent).toBe("Prism");
  });
});
