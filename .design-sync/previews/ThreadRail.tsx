import { ThreadRail } from "prism-web";

const upstream = [
  {
    event_id: "a1",
    title: "Ukraine strikes 17 Russian oil tankers in Black Sea drone attack",
    sector: "politics",
    occurred_at: "2026-07-12T06:00:00Z",
    relation: "leads_to",
    rationale: "The tanker strikes triggered the shipping suspension covered here.",
    confidence: 0.85,
    image_url: null,
  },
];
const downstream = [
  {
    event_id: "b2",
    title: "Oil prices surge 8% as Black Sea shipping halts",
    sector: "finance",
    occurred_at: "2026-07-13T09:30:00Z",
    relation: "leads_to",
    rationale: "Brent jumped after operators suspended Black Sea routes over strike risk.",
    confidence: 0.8,
    image_url: null,
  },
  {
    event_id: "c3",
    title: "Insurers triple war-risk premiums for Black Sea routes",
    sector: "business",
    occurred_at: "2026-07-14T11:00:00Z",
    relation: "related",
    rationale: "Marine insurers repriced war risk after the same attacks on commercial shipping.",
    confidence: 0.7,
    image_url: null,
  },
];

// The story thread: what led here → this story → what followed.
export const FullThread = () => (
  <ThreadRail
    thread={{ upstream, downstream }}
    currentTitle="Tanker operators suspend Black Sea routes citing drone-strike risk"
  />
);

export const UpstreamOnly = () => (
  <ThreadRail
    thread={{ upstream, downstream: [] }}
    currentTitle="Oil prices surge 8% as Black Sea shipping halts"
  />
);
