import { Suspense } from "react";
import Explorer from "@/components/Explorer";

export default function ExplorePage() {
  return (
    <Suspense fallback={null}>
      <Explorer />
    </Suspense>
  );
}
