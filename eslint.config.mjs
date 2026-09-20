import { FlatCompat } from "@eslint/eslintrc";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });
const config = [
  { ignores: ["**/node_modules/**", "**/.next/**", "**/next-env.d.ts"] },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  { settings: { next: { rootDir: fileURLToPath(new URL("./apps/web/", import.meta.url)) } } },
];
export default config;
