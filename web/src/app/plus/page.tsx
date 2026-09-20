import type { Metadata } from "next";
import { PlusPage } from "@/components/PlusPage";

export const metadata: Metadata = {
  title: "Plus",
  description: "The record stays free. Plus is for the reader who asks more of it: 100 questions a day, the stronger model, answers from the whole story.",
};

export default function Page() {
  return <PlusPage />;
}
