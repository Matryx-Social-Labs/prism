import { redirect } from "next/navigation";

// The interests editor folded into /you (the reservation form). Old links land there.
export default function InterestsPage() {
  redirect("/you");
}
