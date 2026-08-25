# Escaping, Whitespace, and Optional Syntax

Use this reference when rendered bytes, HTML trust, or optional environment features affect correctness.

## HTML Escaping

Autoescaping is selected by the host environment, commonly according to template name. Never infer it from a file extension alone.

- Under manual escaping, use `|e` for data placed into HTML.
- Under autoescaping, ordinary values are escaped and trusted markup can be represented by the host or asserted with `|safe`.
- Use `|safe` only for content already trusted or sanitized under the application's security contract.
- Markup safety can be lost when values pass through ordinary Python strings, and escaping an already escaped value can double-escape it.
- Macros, `super()`, and `self.block()` return template-safe data; this does not make their untrusted inputs inherently safe.
- String literals inside templates are considered unsafe under autoescaping.

Escape for the actual output context. HTML text, HTML attributes, URLs, JavaScript, CSS, and JSON do not share one universal escaping rule. Prefer application or framework facilities for context-sensitive security.

## Autoescape Blocks

When supported, temporarily override the current policy:

```jinja
{% autoescape false %}
  {{ trusted_legacy_fragment }}
{% endautoescape %}
```

The prior state is restored after the block. Treat disabling autoescape as a security-sensitive exception requiring a clear trust rationale.

## Whitespace Control

Environment options control baseline behavior:

- `trim_blocks` removes the first newline after a block tag.
- `lstrip_blocks` strips leading spaces and tabs before block tags.
- `keep_trailing_newline` preserves the template's final newline; otherwise one trailing newline is removed by default.

Local modifiers provide precise control:

- `-` strips whitespace adjacent to a delimiter: `{%-`, `-%}`, `{{-`, `-}}`, `{#-`, `-#}`.
- `+` can locally disable configured block trimming or left stripping at the relevant edge.
- Do not insert whitespace between a delimiter and its `-` or `+` modifier.

Use modifiers sparingly. Aggressive stripping can concatenate words or HTML nodes unexpectedly. Render representative inputs when output whitespace is significant.

## Raw Blocks and Literal Syntax

```jinja
{% raw %}
  {{ this_is_documentation_not_a_variable }}
{% endraw %}
```

`{% raw -%}` also removes whitespace before the raw content begins. For a single literal delimiter, an expression such as `{{ '{{' }}` is often clearer.

## Line Statements and Line Comments

The host may configure prefixes that turn lines into statements or comments. A line statement prefix can appear after indentation, may use an optional trailing colon, and can span lines while parentheses, brackets, or braces remain open. These forms are unavailable unless configured, so follow local conventions rather than assuming a prefix.

## Extension-Provided Features

These tags require environment support unless noted:

- Internationalization extension: `trans`, optional variable bindings, `pluralize`, translation context, and trimmed or untrimmed whitespace. Use named placeholders so translators can reorder values. Only simple variable expressions are allowed inside translation blocks; compute complex values beforehand.
- Expression-statement extension: `{% do expression %}` evaluates an expression without emitting its return value.
- Loop-controls extension: `{% break %}` and `{% continue %}` add imperative loop control.
- Debug extension: `{% debug %}` emits the current context plus available filters and tests; avoid exposing it in user-facing production output.
- `with`: creates a local scope and is built into modern Jinja, so it does not require the historical extension in Jinja 3.1.
- Autoescape override: `{% autoescape true %}` and `{% autoescape false %}` are built into modern Jinja.

Translation function names may include `_`, `gettext`, `ngettext`, `pgettext`, and `npgettext` depending on environment installation. Treat them as host-provided APIs and verify availability.

## Safety Review

- Trace each rendered value back to its trust source.
- Check the output context, not only whether autoescape is enabled.
- Confirm all optional tags and line prefixes are enabled locally.
- Review whitespace using actual rendered output when producing plain text, email, code, or whitespace-sensitive HTML.
