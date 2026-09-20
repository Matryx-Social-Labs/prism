import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ClipOut } from "@/lib/api";
import { Clips, HeardOn, clipShift } from "@/components/Clips";

const show = { slug: "et", name: "The Morning Brief", publisher: "The Economic Times", art_url: null, site_url: null };
const clip = (over: Partial<ClipOut> = {}): ClipOut => ({
  show,
  episode_title: "Ep",
  episode_url: "https://et.example/ep",
  audio_url: "https://cdn.example/ep.mp3",
  audio_duration_s: 900,
  published_at: new Date().toISOString(),
  start_s: 120,
  end_s: 180,
  text: "the rupee fell sharply on Monday",
  words: [["the", 120, 120.2], ["rupee", 120.2, 120.6], ["fell", 120.6, 121], ["sharply", 121, 121.5], ["on", 121.5, 121.7], ["Monday", 121.7, 122]],
  score: 0.9,
  ...over,
});

// jsdom has no media pipeline: play()/pause() are stubbed and the element's
// duration/currentTime are set by hand, then the events are fired.
beforeEach(() => {
  Object.defineProperty(HTMLMediaElement.prototype, "play", { configurable: true, value: vi.fn().mockResolvedValue(undefined) });
  Object.defineProperty(HTMLMediaElement.prototype, "pause", { configurable: true, value: vi.fn() });
  Object.defineProperty(HTMLMediaElement.prototype, "load", { configurable: true, value: vi.fn() });
  Object.defineProperty(HTMLMediaElement.prototype, "duration", { configurable: true, writable: true, value: 900 });
});
afterEach(() => vi.useRealTimers());

const audioEl = () => document.querySelector("audio") as HTMLAudioElement;

describe("the clip shift", () => {
  it("is the difference in duration once it is more than noise", () => {
    expect(clipShift(900, 900)).toBe(0);
    expect(clipShift(900.8, 900)).toBe(0);
    expect(clipShift(931, 900)).toBe(31); // a 31 s pre-roll the host stitched in for this reader
    expect(clipShift(NaN, 900)).toBe(0);
    expect(clipShift(900, null)).toBe(0);
  });
});

describe("Clips — one player, the publisher's file", () => {
  it("plays from the clip's start, not from the top of the episode", async () => {
    render(<Clips clips={[clip()]} />);
    await userEvent.click(screen.getByRole("button", { name: /Play the clip/ }));
    const el = audioEl();
    expect(el.src).toBe("https://cdn.example/ep.mp3");
    act(() => { fireEvent.loadedMetadata(el); });
    expect(el.currentTime).toBe(120);
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
  });

  it("adds the ad shift when the loaded file is longer than the one we transcribed", async () => {
    render(<Clips clips={[clip()]} />);
    await userEvent.click(screen.getByRole("button", { name: /Play the clip/ }));
    const el = audioEl();
    Object.defineProperty(el, "duration", { configurable: true, value: 930 });
    act(() => { fireEvent.loadedMetadata(el); });
    expect(el.currentTime).toBe(150);
  });

  it("advances to the next clip at the end of this one, and stops after the last", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const second = clip({ audio_url: "https://cdn.example/other.mp3", start_s: 40, end_s: 70, episode_title: "Other" });
    render(<Clips clips={[clip(), second]} />);
    await userEvent.click(screen.getAllByRole("button", { name: /Play the clip/ })[0]);
    const el = audioEl();
    act(() => { fireEvent.loadedMetadata(el); fireEvent.play(el); });
    el.currentTime = 181; // past end_s
    act(() => { fireEvent.timeUpdate(el); });
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(el.src).toBe("https://cdn.example/other.mp3");
  });

  it("keeps listening past the clip when the reader asks", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<Clips clips={[clip(), clip({ start_s: 300, end_s: 330 })]} />);
    await userEvent.click(screen.getAllByRole("button", { name: /Play the clip/ })[0]);
    const el = audioEl();
    act(() => { fireEvent.loadedMetadata(el); fireEvent.play(el); });
    await userEvent.click(screen.getAllByRole("button", { name: "Keep listening" })[0]);
    (HTMLMediaElement.prototype.pause as ReturnType<typeof vi.fn>).mockClear();
    el.currentTime = 181;
    act(() => { fireEvent.timeUpdate(el); });
    expect(HTMLMediaElement.prototype.pause).not.toHaveBeenCalled();
    expect(el.currentTime).toBe(181);
  });

  it("inks the words as they are spoken", async () => {
    render(<Clips clips={[clip()]} />);
    await userEvent.click(screen.getByRole("button", { name: /Play the clip/ }));
    const el = audioEl();
    act(() => { fireEvent.loadedMetadata(el); fireEvent.play(el); });
    el.currentTime = 120.7;
    act(() => { fireEvent.timeUpdate(el); });
    expect(screen.getByText("fell").className).toBe("clip-word-said");
    expect(screen.getByText("Monday").className).toBe("clip-word");
  });

  it("names the show, the publisher and the whole episode — on the card and again on the transcript window", () => {
    render(<Clips clips={[clip()]} />);
    expect(screen.getAllByText("The Morning Brief").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/The Economic Times/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Full episode/ })).toHaveAttribute("href", "https://et.example/ep");
    expect(screen.getByText(/Transcript 2:00–3:00/)).toBeInTheDocument();
  });

  it("renders nothing at all with no clips", () => {
    const { container } = render(<Clips clips={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("HeardOn", () => {
  it("counts the shows and is absent when there are none", () => {
    const { rerender } = render(<HeardOn shows={["et", "hindu"]} />);
    expect(screen.getByText("Heard on 2 shows")).toBeInTheDocument();
    rerender(<HeardOn shows={[]} />);
    expect(screen.queryByText(/Heard on/)).toBeNull();
  });
});
