# Templates Documentation Coverage Matrix

This matrix maps the Jinja 3.1 stable [Template Designer Documentation](https://jinja.palletsprojects.com/en/stable/templates/) to the skill's routed references. It is an audit aid, not a substitute for checking the installed version or exact API signatures.

| Official topic | Covered in this skill |
| --- | --- |
| Synopsis and delimiters | [core-syntax.md](core-syntax.md) — Template Syntax |
| Variables, attribute/item lookup, undefined | [core-syntax.md](core-syntax.md) — Variables and Lookup |
| Filters and tests syntax | [core-syntax.md](core-syntax.md) — Filters and Tests |
| Comments | [core-syntax.md](core-syntax.md) — Comments and Literal Delimiters |
| Whitespace control | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Whitespace Control |
| Escaping and raw blocks | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Raw Blocks and Literal Syntax |
| Line statements and line comments | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Line Statements and Line Comments |
| Template inheritance | [composition.md](composition.md) — Inheritance and Blocks |
| Base templates, child templates, block nesting | [composition.md](composition.md) — Inheritance and Blocks |
| `super`, `self`, named end blocks | [composition.md](composition.md) — Inheritance and Blocks |
| Block nesting, scope, `scoped`, `required` | [composition.md](composition.md) — Inheritance and Blocks |
| HTML escaping, manual and automatic | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — HTML Escaping |
| Working with manual escaping | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — HTML Escaping |
| Working with automatic escaping | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — HTML Escaping and Autoescape Blocks |
| For loops and loop metadata | [control-flow-scope.md](control-flow-scope.md) — For Loops |
| Filtered loops, loop `else`, recursive loops | [control-flow-scope.md](control-flow-scope.md) — For Loops and Recursive Loops |
| If statements | [control-flow-scope.md](control-flow-scope.md) — Conditionals |
| Macros and macro metadata | [composition.md](composition.md) — Macros |
| Call blocks | [composition.md](composition.md) — Call Blocks |
| Filter blocks | [control-flow-scope.md](control-flow-scope.md) — Block Assignment and Filter Blocks |
| Assignments, namespace objects, block assignment | [control-flow-scope.md](control-flow-scope.md) — Assignment and Block Assignment |
| Include | [composition.md](composition.md) — Includes |
| Import and from-import context behavior | [composition.md](composition.md) — Imports |
| Literals | [core-syntax.md](core-syntax.md) — Literals |
| Math, comparisons, logic, and other operators | [core-syntax.md](core-syntax.md) — Operators |
| Inline conditional expression | [core-syntax.md](core-syntax.md) — Conditional Expressions |
| Built-in filters | [filters-tests-globals.md](filters-tests-globals.md) — Built-in Filters |
| Built-in tests | [filters-tests-globals.md](filters-tests-globals.md) — Built-in Tests |
| Built-in global functions | [filters-tests-globals.md](filters-tests-globals.md) — Built-in Global Functions |
| Internationalization extension | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Extension-Provided Features |
| Expression statement (`do`) extension | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Extension-Provided Features |
| Loop controls extension | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Extension-Provided Features |
| Debug extension | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Extension-Provided Features |
| With statement | [control-flow-scope.md](control-flow-scope.md) — With Scope |
| Autoescape overrides | [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md) — Autoescape Blocks |

## Coverage Boundary

The Templates page explains language behavior and the effects of environment choices. This skill covers those effects when authoring templates. It intentionally does not teach Python-side environment construction, loader setup, bytecode caching, sandbox implementation, custom extension implementation, or framework-specific integration.

## Audit Procedure

1. Compare the official page's table of contents with the rows above.
2. Check the stable documentation version against the project's installed Jinja version.
3. Confirm that each linked section gives enough guidance to choose correct template syntax without copying the whole manual.
4. For exact filter, test, or global signatures, follow the official API entry because signatures and version notes can change.
5. Add a matrix row and focused reference guidance whenever the official Templates page gains a new author-facing topic.

Last audited against the stable Jinja 3.1 Templates documentation on 2026-08-25.
