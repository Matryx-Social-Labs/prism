// Flat config. `next lint` is retired in Next 16, so the script calls eslint
// directly. The two hooks rules are the point: rules-of-hooks and
// exhaustive-deps were never enforced here, and every `eslint-disable` comment
// in the tree was silencing a rule that did not run.
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  { ignores: [".next/**", "out/**", "next-env.d.ts", "coverage/**"] },
];

export default config;
