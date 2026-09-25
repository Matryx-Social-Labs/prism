import { Speech } from "@/components/icons";
import { ShareButton } from "@/components/ShareButton";

/**
 * The phone's thumb zone on the record (Design System v2 · StoryActionBar):
 * Ask, with the count of reports it answers from, and Share — fixed above the
 * safe area; the page keeps room beneath its last line so nothing hides here.
 */
export function StoryActionBar({ reports, onAsk, url, title }: { reports: number; onAsk: () => void; url: string; title: string }) {
  return (
    <div
      className="fixed inset-x-0 bottom-0 z-40 flex gap-2 border-t px-3 pt-2.5 lg:hidden"
      style={{ borderColor: "var(--line)", background: "color-mix(in srgb, var(--paper) 94%, transparent)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)", paddingBottom: "calc(env(safe-area-inset-bottom) + 10px)" }}
    >
      <button type="button" onClick={onAsk} className="p-btn p-btn--primary min-w-0 flex-1">
        <Speech />
        Ask ·
        <span className="font-mono text-[12px] font-normal">{reports} {reports === 1 ? "report" : "reports"}</span>
      </button>
      <div className="shrink-0">
        <ShareButton url={url} title={title} fill />
      </div>
    </div>
  );
}
