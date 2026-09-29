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

  // REGRESSION: the 64/104px size sat on the inner word, so the clip box's em padding resolved
  // against 16px (1-2px) and Devanagari, Bengali, Gujarati and Telugu marks above the letters
  // were cut off by up to 19px. The box carries the word's size, so em padding scales with it.
  // REGRESSION (iPhone): the room then sat on the clip box, but the opacity/blur transition runs
  // on the word, and iOS Safari paints a transitioning element on a layer only as big as its own
  // box — the marks above a 1.08 line were cut flat through every un-blur, then popped back
  // (phone recording, 2026-09-29). The room belongs on the word that animates.
  it("gives the animated word room above and below in its own em", () => {
    render(<IndicName languages={["en", "hi"]} />);
    const box = screen.getByRole("img", { name: "Prism, in the scripts it reads" }).firstElementChild as HTMLElement;
    const word = box.firstElementChild as HTMLElement;
    expect(box.className).toMatch(/text-\[64px\]/);
    expect(word.className).not.toMatch(/text-\[/);
    expect(word.style.transition).toMatch(/filter/);
    expect(box.style.padding).toBe("");
    const [top, , bottom] = word.style.padding.split(" ");
    expect(top).toMatch(/em$/);
    expect(parseFloat(top)).toBeGreaterThanOrEqual(0.2);
    expect(parseFloat(bottom)).toBeGreaterThanOrEqual(0.05);
  });
});
