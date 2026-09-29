"use client";

import { useState } from "react";
import { Alert, SelectField, TextField } from "@/components/ui";
import { GRIEVANCE_KINDS, fileGrievance, isKind, type FiledGrievance } from "@/lib/grievance";
import { GRIEVANCE_OFFICER } from "@/lib/legal";

const BODY_MIN = 10;
const BODY_MAX = 5000;

const istDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "long", year: "numeric" });

/**
 * The complaint form on /grievance (api/routes/grievances.py). Prefilled from
 * ?kind= and ?record= when a record's "Something wrong?" link opened it. On
 * success the form gives way to the reference and what happens next, in words
 * that depend on whether the acknowledgement email actually went out.
 */
export function GrievanceForm({ initialKind = "", initialRecord = "" }: { initialKind?: string; initialRecord?: string }) {
  const [category, setCategory] = useState(isKind(initialKind) ? initialKind : "");
  const [page, setPage] = useState(initialRecord);
  const [body, setBody] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [website, setWebsite] = useState(""); // the honeypot: people never see it
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [filed, setFiled] = useState<(FiledGrievance & { email: string }) | null>(null);

  if (filed) {
    return (
      <Alert title={<>Received · <span className="p-mono">{filed.ref}</span></>}>
        <p>
          {filed.acknowledged
            ? `The acknowledgement, with a copy of your complaint, is on its way to ${filed.email}.`
            : `Your complaint is saved, but the acknowledgement could not be emailed to ${filed.email}. Keep this reference.`}{" "}
          {GRIEVANCE_OFFICER.name} will decide it by {istDate(filed.decide_by)} and write to you with the outcome. Quote {filed.ref} if you write to{" "}
          <a href={`mailto:${GRIEVANCE_OFFICER.email}`} className="p-link">{GRIEVANCE_OFFICER.email}</a>.
        </p>
      </Alert>
    );
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isKind(category)) return setError("Choose what the complaint is about.");
    if (body.trim().length < BODY_MIN) return setError(`Say what is wrong in at least ${BODY_MIN} characters.`);
    setBusy(true);
    setError("");
    try {
      const done = await fileGrievance({ category, body, email, name, subject_url: page, website });
      setFiled({ ...done, email: email.trim() });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Your complaint could not be sent.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid max-w-[560px] gap-4" aria-label="Make a complaint">
      <SelectField label="What is it about?" placeholder="Choose one" value={category} onChange={setCategory} options={GRIEVANCE_KINDS} />
      <TextField
        label="Which page (optional)"
        hint="A Prism address, such as /story/…, or the full link. Leave it empty if the complaint is not about one page."
        value={page}
        onChange={setPage}
        name="subject_url"
        maxLength={500}
      />
      <TextField
        label="What is wrong"
        hint="What you saw, where, and what it should say. For a payment, the payment reference from your receipt."
        multiline
        rows={6}
        value={body}
        onChange={setBody}
        name="body"
        required
        maxLength={BODY_MAX}
      />
      <TextField label="Your email" hint="The acknowledgement and the decision are sent here." type="email" autoComplete="email" required value={email} onChange={setEmail} name="email" maxLength={254} />
      <TextField label="Your name (optional)" autoComplete="name" value={name} onChange={setName} name="name" maxLength={120} />
      <div className="p-sr" aria-hidden="true">
        <TextField label="Leave this empty" value={website} onChange={setWebsite} name="website" tabIndex={-1} autoComplete="off" />
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      <div>
        <button type="submit" className="p-btn p-btn--primary" disabled={busy}>
          {busy ? "Sending…" : "Send the complaint"}
        </button>
      </div>
    </form>
  );
}
