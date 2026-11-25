"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Explorer from "@/components/Explorer";

function Inner() {
  const { slug } = useParams<{ slug: string }>();
  const sp = useSearchParams();
  return <Explorer key={slug} fixedDisease={slug} initialCountry={sp.get("country") ?? undefined} />;
}

export default function DiseasePage() {
  return (
    <Suspense fallback={null}>
      <Inner />
    </Suspense>
  );
}
