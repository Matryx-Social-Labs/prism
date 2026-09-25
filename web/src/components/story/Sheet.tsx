"use client";

import { Close } from "@/components/icons";

/**
 * A sheet over the record (Design System v2 · Sheet): from the bottom on the
 * phone, with a grab bar; on a desk a 420px drawer from the right ("drawer")
 * or a centred dialog ("dialog"). The scrim, Escape (the owner's) and the
 * close button all close it; the reader keeps their place underneath.
 */
export function Sheet({
  variant,
  label,
  labelledBy,
  title,
  onClose,
  closeRef,
  children,
  footer,
  modal = true,
}: {
  variant: "drawer" | "dialog";
  /** The dialog's name when there is no visible title to point at. */
  label?: string;
  labelledBy?: string;
  /** The sheet's own head, beside the close button. */
  title?: React.ReactNode;
  onClose?: () => void;
  closeRef?: React.Ref<HTMLButtonElement>;
  children: React.ReactNode;
  footer?: React.ReactNode;
  modal?: boolean;
}) {
  const place =
    variant === "drawer"
      ? "ask-sheet max-h-[88vh] lg:inset-y-0 lg:left-auto lg:right-0 lg:max-h-none lg:w-[420px] lg:rounded-none"
      : "upgrade-sheet max-h-[88vh] lg:inset-auto lg:left-1/2 lg:top-1/2 lg:w-[440px] lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-[var(--r-xl)]";
  return (
    <>
      <div className="p-scrim" onClick={onClose} aria-hidden="true" />
      <section
        role="dialog"
        aria-modal={modal}
        aria-label={label}
        aria-labelledby={labelledBy}
        className={`p-sheet fixed inset-x-0 bottom-0 rounded-t-[var(--r-xl)] ${place}`}
      >
        <div className="p-sheet__grab lg:hidden" aria-hidden />
        {(title || onClose) && (
          <div className="flex items-center gap-2 pb-1.5 pl-5 pr-3 pt-2.5">
            <div className="min-w-0 flex-1">{title}</div>
            {onClose && (
              <button ref={closeRef} type="button" className="p-iconbtn" aria-label="Close" onClick={onClose}>
                <Close size={16} />
              </button>
            )}
          </div>
        )}
        {children}
        {footer && <div className="border-t px-5 pb-[calc(env(safe-area-inset-bottom)+16px)] pt-3" style={{ borderColor: "var(--line)" }}>{footer}</div>}
      </section>
    </>
  );
}
