import { readFile } from "node:fs/promises";
import path from "node:path";
import { gunzip } from "node:zlib";
import { promisify } from "node:util";
import SectorExplorer from "@/features/sectors/SectorExplorer";
import type { SectorBundle } from "@/features/sectors/types";

export default async function DevelopmentSectorsPage() {
  // An offline, checked artifact; no provider fetch or public financial API.
  const file = path.join(process.cwd(), "src/features/sectors/fixture.json.gz");
  const bytes = await promisify(gunzip)(await readFile(file));
  const bundle = JSON.parse(bytes.toString("utf8")) as SectorBundle;
  if (bundle.fictional !== true) throw new Error("The development explorer requires an explicitly fictional fixture.");
  return <SectorExplorer bundle={bundle} />;
}
