import { Suspense } from "react";
import AskPage from "@/components/AskPage";

export default function Page() {
  return <Suspense fallback={null}><AskPage /></Suspense>;
}
