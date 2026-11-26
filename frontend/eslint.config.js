import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  {
    // Scope legacy pre-R1 component rule exceptions to avoid cross-branch merge conflicts
    files: [
      'src/components/chat/ChatInput.tsx',
      'src/components/lineage/LineageGraph.tsx',
      'src/components/modals/DatasetRelationModal.tsx',
      'src/components/modals/LLMSettingsModal.tsx',
      'src/components/sidebar/FileItem.tsx',
      'src/components/upload/UploadModal.tsx',
      'src/components/workspace/ScriptMetadataView.tsx',
      'src/components/workspace/ScriptView.tsx',
    ],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
      'react-hooks/exhaustive-deps': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/set-state-in-effect': 'off',
      'react-hooks/static-components': 'off',
    },
  },
])
