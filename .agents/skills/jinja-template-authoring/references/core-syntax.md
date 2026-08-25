# Core Syntax and Expressions

Use this reference for the language shared by most Jinja templates. Confirm project-defined delimiters and undefined behavior when they affect the result.

## Template Syntax

- `{{ expression }}` emits a value.
- `{% statement %}` controls rendering or composition.
- `{# comment #}` is removed from the output.
- A host application may configure different delimiters, line statements, or line comments.
- Templates are text files; their extension does not define Jinja semantics.

## Variables and Lookup

The host supplies the template context. Do not invent names that are absent from call sites, fixtures, or documented context contracts.

- `foo.bar` checks the attribute first, then the item.
- `foo['bar']` checks the item first, then the attribute.
- `foo|attr('bar')` performs attribute lookup only.
- Chained access is allowed, but each segment can become undefined.
- Undefined values may print silently or raise immediately depending on the configured undefined type.

Distinguish these cases deliberately:

```jinja
{% if value is undefined %}not supplied{% endif %}
{% if value is none %}explicitly empty{% endif %}
{% if not value %}false, zero, none, undefined, or empty{% endif %}
{{ value|default('fallback') }}
{{ value|default('fallback', true) }} {# also replaces falsey values #}
```

## Literals

Jinja supports strings, integers, floats, scientific notation, lists, tuples, dictionaries, booleans, and `none`. Numeric underscores are allowed. Prefer lowercase `true`, `false`, and `none`.

```jinja
{% set label = 'Open' %}
{% set ids = [1, 2, 3] %}
{% set one_item_tuple = (1,) %}
{% set options = {'compact': true, 'limit': 1_000} %}
```

## Operators

- Arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, and `**`.
- Comparison: `==`, `!=`, `<`, `<=`, `>`, and `>=`.
- Logic: `and`, `or`, `not`, with parentheses for grouping.
- Membership: `value in sequence` and `value not in sequence`.
- Tests: `value is test` and `value is not test`.
- Filtering: `value|filter(args)`.
- Concatenation: `left ~ right`, which converts operands to strings.
- Access and calls: `.`, `[]`, and `()`.

Jinja chained exponentiation evaluates left to right, unlike Python. Keep complex calculations in application code.

## Conditional Expressions

```jinja
{{ 'active' if user.enabled else 'inactive' }}
```

The `else` part may be omitted, but the false branch then produces an undefined value regardless of the configured undefined type. Prefer an explicit branch when output matters.

## Filters and Tests

Filters transform values and can be chained:

```jinja
{{ users|selectattr('enabled')|map(attribute='name')|join(', ') }}
```

Tests answer a condition and are used with `is`:

```jinja
{% if user is defined and user.email is string %}...{% endif %}
```

Parenthesize complex combinations so filter and test binding is unambiguous. Filters, tests, globals, and callable object methods can be application-defined; verify them in the project before use. See [filters-tests-globals.md](filters-tests-globals.md) for the built-in catalogs and important edge behavior.

## Comments and Literal Delimiters

Jinja comments do not appear in output. To emit a short delimiter literally, place it in an expression, such as `{{ '{{' }}`. Use a `raw` block for larger examples; see [escaping-whitespace-extensions.md](escaping-whitespace-extensions.md).

## Review Checklist

- Verify every context name and custom callable.
- Check missing, `none`, false, zero, and empty inputs separately.
- Confirm the installed Jinja version before using recently added syntax.
- Do not assume Python operator details, object behavior, or scoping apply unchanged.
