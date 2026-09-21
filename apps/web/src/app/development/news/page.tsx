import type { Metadata } from "next";
import WorkbenchShell from "@/components/WorkbenchShell";
import NewsWorkspace from "@/features/news/NewsWorkspace";

export const metadata: Metadata = { title: "News & calendar · EquityEval" };

export default function NewsPage() {
  return <WorkbenchShell active="news" fictional><NewsWorkspace /></WorkbenchShell>;
}
