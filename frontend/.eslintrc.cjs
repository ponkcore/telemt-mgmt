// Legacy ESLint config (ESLint 8). ESLint 9 uses eslint.config.js (flat config).
// This file is the §5 Outputs artifact for TKT-001. The active config is
// eslint.config.js.
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: ["eslint:recommended"],
  ignorePatterns: ["dist", "node_modules"],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
};
