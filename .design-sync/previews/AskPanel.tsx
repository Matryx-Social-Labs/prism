import { AskPanel } from "prism-web";

// Grounded per-story Q&A: suggested questions as chips + a free-text ask box.
// Answers stream from the story's own sources with citations (network-bound;
// the static card shows the resting state).
export const WithSuggestions = () => (
  <div style={{ maxWidth: 620, padding: 16 }}>
    <AskPanel
      eventId="demo-event"
      sourceCount={5}
      suggestedQuestions={[
        "What led to this?",
        "Who is affected?",
        "What are the likely outcomes?",
        "How is each side framing it?",
      ]}
    />
  </div>
);

export const LensQuestions = () => (
  <div style={{ maxWidth: 620, padding: 16 }}>
    <AskPanel
      eventId="demo-event"
      sourceCount={5}
      suggestedQuestions={["Which tickers does this move?", "What is the catalyst here?"]}
    />
  </div>
);
