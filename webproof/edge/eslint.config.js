import js from '@eslint/js';
import tseslint from 'typescript-eslint';
export default tseslint.config(
  { ignores: ['node_modules/**', 'coverage/**', '.wrangler/**'] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  { languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } }, rules: { '@typescript-eslint/no-confusing-void-expression': 'off', '@typescript-eslint/unbound-method': 'off', '@typescript-eslint/require-await': 'off', '@typescript-eslint/no-this-alias': 'off', '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }], '@typescript-eslint/no-unnecessary-type-assertion': 'off', '@typescript-eslint/restrict-template-expressions': 'off' } }
);
