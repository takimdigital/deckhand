// design-audit — copy to <repo>/eslint.config.mjs ONLY if the repo has no eslint flat config.
// Scope: accessibility lint (eslint-plugin-jsx-a11y) — the design gate's concern.
// If your repo already has eslint.config.(js|mjs|cjs): add `jsxA11y.flatConfigs.recommended`
// to its exported array instead of using this file, and keep your existing rules.
import jsxA11y from 'eslint-plugin-jsx-a11y';

export default [jsxA11y.flatConfigs.recommended];
