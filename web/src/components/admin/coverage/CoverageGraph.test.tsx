import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import * as THREE from "three";

import CoverageGraph from "./CoverageGraph";

afterEach(() => vi.restoreAllMocks());

describe("the 3D coverage view", () => {
  it("says so in words when the browser cannot draw WebGL, instead of an empty box", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    render(<CoverageGraph outlets={[{ id: "a", name: "The Hindu", language: "en", stories: 4, color: "var(--viz-1)" }]} links={[]} label="1 outlet" />);
    expect(await screen.findByText(/This browser can't draw the 3D network/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "1 outlet" })).toBeInTheDocument();
  });

  it("frees the buffers it built when it goes away", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    const dispose = vi.spyOn(THREE.BufferGeometry.prototype, "dispose");
    const outlets = [
      { id: "a", name: "A", language: "en", stories: 4, color: "var(--viz-1)" },
      { id: "b", name: "B", language: "en", stories: 2, color: "var(--viz-1)" },
    ];
    const { unmount } = render(<CoverageGraph outlets={outlets} links={[{ a: "a", b: "b", shared: 2 }]} label="2 outlets" />);
    await screen.findByText(/This browser can't draw the 3D network/);
    unmount();
    expect(dispose).toHaveBeenCalled();
  });
});
