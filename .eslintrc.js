module.exports = {
  env: {
    node: true,
    browser: true,
    commonjs: true,
    es6: true,
  },
  settings: {
    "import/resolver": {
      typescript: {
        project: ["tsconfig.json"],
      },
      node: {
        extensions: [".js", ".jsx", ".ts", ".tsx"],
        paths: ["."],
      },
    },
  },
  extends: [
    "airbnb",
    "prettier",
    "plugin:@typescript-eslint/eslint-recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:jsx-a11y/recommended",
    "plugin:testing-library/react",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    project: "tsconfig.json",
    tsconfigRootDir: __dirname,
    sourceType: "module",
    createDefaultProgram: true,
  },
  plugins: ["react", "@typescript-eslint", "jsx-a11y", "testing-library"],
  rules: {
    "react/react-in-jsx-scope": 0,
    "react/function-component-definition": 0,
    "react/no-unescaped-entities": 0,
    "react/prop-types": 0,
    "react/display-name": 0,
    "react/jsx-filename-extension": 0,
    "react/jsx-props-no-spreading": 0,
    "react/jsx-one-expression-per-line": 0,
    "react/jsx-wrap-multilines": 0,
    "react/require-default-props": 0,
    "no-use-before-define": 0,
    "prefer-destructuring": 0,
    "no-shadow": 0,
    "no-else-return": 0,
    "arrow-body-style": 0,
    "no-plusplus": 0,
    "import/order": 0,
    camelcase: 0,
    "no-param-reassign": 0,
    "import/prefer-default-export": 0,
    "jsx-a11y/anchor-is-valid": 0,
    "@typescript-eslint/no-explicit-any": 0,
    "@typescript-eslint/no-empty-function": 0,
    "@typescript-eslint/no-empty-interface": 0,
    "import/no-extraneous-dependencies": 0,
    "no-restricted-syntax": 0,
    "@typescript-eslint/explicit-function-return-type": 0,
    "@typescript-eslint/explicit-module-boundary-types": 0,
    "array-callback-return": 0,
    "prefer-arrow-callback": 0,
    "func-names": 0,
    "@typescript-eslint/no-unused-vars": [
      "warn",
      {
        vars: "all",
        args: "after-used",
        ignoreRestSiblings: false,
        varsIgnorePattern: "^_",
        argsIgnorePattern: "^_",
      },
    ],
    "import/extensions": [
      "error",
      "ignorePackages",
      {
        js: "never",
        jsx: "never",
        ts: "never",
        tsx: "never",
      },
    ],
  },
  ignorePatterns: ["dist"],
};
