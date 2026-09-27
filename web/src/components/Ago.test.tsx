import { afterEach, describe, expect, it, vi } from "vitest";
import { act } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { render, screen } from "@testing-library/react";
import { Ago } from "@/components/Ago";

const NOW = new Date("2026-09-27T04:30:00Z"); // 10:00 IST
const TWELVE_MIN_AGO = new Date(NOW.getTime() - 12 * 60_000).toISOString();

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("Ago", () => {
  it("prints the time itself on the server, so a cached page never goes stale in place", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
    expect(renderToString(<Ago iso={TWELVE_MIN_AGO} />)).toContain(">27 Sept 09:48</time>");
  });

  it("hydrates that time without a mismatch, then shows the reader the age", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
    const host = document.createElement("div");
    host.innerHTML = renderToString(<Ago iso={TWELVE_MIN_AGO} />);
    document.body.appendChild(host);
    const errors = vi.spyOn(console, "error").mockImplementation(() => {});
    await act(async () => {
      hydrateRoot(host, <Ago iso={TWELVE_MIN_AGO} />, { onRecoverableError: (e) => console.error(e) });
    });
    expect(errors).not.toHaveBeenCalled();
    expect(host.textContent).toBe("12m ago");
  });

  it("shows the age straight away on a client-side render", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
    render(<Ago iso={TWELVE_MIN_AGO} />);
    expect(screen.getByText("12m ago").tagName).toBe("TIME");
  });
});
