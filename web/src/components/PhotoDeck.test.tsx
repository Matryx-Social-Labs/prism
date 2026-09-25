import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PhotoDeck } from "@/components/PhotoDeck";
import type { DeckPhoto } from "@/lib/photos";

const frame = (k: string, name: string): DeckPhoto => ({ key: k, image_url: `https://img.test/${k}.jpg`, url: `https://news.test/${k}`, source_name: name });
const FRAMES = [frame("a", "The Hindu"), frame("b", "Mint"), frame("c", "TV9 Kannada")];

describe("PhotoDeck", () => {
  it("credits the photo on the stage and opens that outlet's report", () => {
    render(<PhotoDeck frames={FRAMES} />);
    expect(screen.getByRole("group", { name: "Photo 1 of 3: The Hindu" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Their report ↗" })).toHaveAttribute("href", "https://news.test/a");
  });

  it("steps with the arrow keys and the thumbnails, wrapping at the end", () => {
    render(<PhotoDeck frames={FRAMES} />);
    const stage = screen.getByRole("group", { name: /Photo 1 of 3/ });
    fireEvent.keyDown(stage, { key: "ArrowLeft" });
    expect(screen.getByRole("group", { name: "Photo 3 of 3: TV9 Kannada" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Photo 2: Mint" }));
    expect(screen.getByRole("group", { name: "Photo 2 of 3: Mint" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Photo 2: Mint" })).toHaveAttribute("aria-current", "true");
  });

  it("drops a photo that fails to load rather than showing a hole", () => {
    render(<PhotoDeck frames={FRAMES} />);
    fireEvent.error(screen.getByAltText("Photo: The Hindu"));
    expect(screen.getByRole("group", { name: "Photo 1 of 2: Mint" })).toBeInTheDocument();
    expect(screen.queryByAltText("Photo: The Hindu")).toBeNull();
  });
});
