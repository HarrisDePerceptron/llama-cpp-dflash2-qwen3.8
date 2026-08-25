---
name: jinja-template-authoring
description: Author, review, debug, and refactor Jinja templates. Use for Jinja syntax, inheritance, includes and imports, macros, variables, expressions, control flow, filters, tests, whitespace, escaping, and template-scope problems. Do not use for Python-side Environment or loader configuration, custom extension implementation, or framework integration unless the task also requires template work.
---

# Jinja Template Authoring

Produce clear, maintainable templates that match the host application's actual Jinja configuration and context contract.

## Workflow

1. Inspect the relevant templates and nearby project conventions before editing. Identify parent templates, included or imported files, naming patterns, whitespace conventions, and any template-specific tests or render commands.
2. Determine the context contract from call sites, fixtures, documentation, or neighboring templates. Do not invent variables, filters, tests, globals, or extensions merely because standard Jinja could support them.
3. Confirm project-specific behavior when it matters: Jinja version, delimiters, undefined type, autoescape policy, enabled extensions, and whether imports receive context.
4. Make the smallest coherent template change. Keep application logic in application code when practical; use template logic for presentation, composition, and simple transformations.
5. Validate with the project's existing template tests, linter, or representative render path. If none exists, review block structure, variable availability, escaping, whitespace, empty collections, missing optional values, and inheritance behavior explicitly.

## Correctness and Safety

- Treat autoescaping as environment-dependent. Do not assume that a file extension alone guarantees escaping.
- Use `|safe` only when the value is already trusted or sanitized under the application's security contract. Never use it merely to make rendered markup look correct.
- Preserve the distinction between undefined, `none`, false, zero, and empty values. Use `is defined`, `is none`, or an explicit fallback according to the intended semantics.
- Account for Jinja scope rules. Assignments inside loops do not provide general outer-scope mutation; use a namespace only when state must intentionally cross the loop boundary.
- Prefer inheritance and macros for stable reuse. Use includes for rendered fragments and imports for reusable macros or exported values.
- Keep block names and macro interfaces stable unless the task explicitly authorizes a broader refactor.
- Do not assume Python syntax and behavior transfer directly to Jinja. Use documented Jinja expressions, filters, tests, and control structures.
- Treat application-defined filters, tests, globals, and object methods as project APIs. Verify them locally before relying on them.

## Reference Routing

Load only the references needed for the task:

- Read [references/core-syntax.md](references/core-syntax.md) for delimiters, lookup behavior, literals, expressions, operators, filters, tests, comments, and undefined values.
- Read [references/control-flow-scope.md](references/control-flow-scope.md) for loops, conditionals, assignments, namespaces, filter blocks, `with`, recursion, and scope.
- Read [references/composition.md](references/composition.md) for inheritance, blocks, `super`, includes, imports, macros, and call blocks.
- Read [references/filters-tests-globals.md](references/filters-tests-globals.md) when selecting or reviewing a built-in filter, test, or global function.
- Read [references/escaping-whitespace-extensions.md](references/escaping-whitespace-extensions.md) for HTML safety, whitespace control, raw or line syntax, autoescape overrides, and extension-provided tags.
- Read [references/coverage-matrix.md](references/coverage-matrix.md) when auditing the skill, answering broad documentation questions, or checking whether a documented Templates topic is covered.

The references summarize Jinja 3.1 stable behavior. Verify the installed Jinja version and project configuration before relying on version-sensitive features or optional extensions.

This skill targets template authoring. For tasks limited to Python-side `Environment` setup, loaders, bytecode caching, extension implementation, sandbox construction, or Flask/Django integration, use the relevant project or framework guidance instead.
