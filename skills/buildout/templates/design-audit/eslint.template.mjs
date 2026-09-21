// design-audit — copy to <repo>/eslint.config.mjs ONLY if the repo has no eslint flat config.
// Scope: accessibility lint (eslint-plugin-jsx-a11y) + TypeScript parsing — the design gate's concern.
// If your repo already has eslint.config.(js|mjs|cjs): add `jsxA11y.flatConfigs.recommended`
// (and the parser + ignores blocks, if it lints TS) to that config instead, and keep your rules.
import tsParser from '@typescript-eslint/parser';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    ignores: [
      '.next/**',
      'node_modules/**',
      'design-audit/artifacts/**',
      'design-audit/report/**',
      'design-audit/reports/**',
      'design-audit/ctrf/**'
    ]
  },
  {
    files: ['**/*.{js,jsx,mjs,cjs,ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaFeatures: { jsx: true }, sourceType: 'module' }
    }
  },
  jsxA11y.flatConfigs.recommended,
  {
    // react-hooks: repos commonly carry eslint-disable comments for exhaustive-deps; with the
    // rule undefined, ESLint 9 reports "Definition for rule ... was not found" as an ERROR.
    files: ['**/*.{js,jsx,mjs,cjs,ts,tsx}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn'
    }
  }
];
