# Template Composition

Use inheritance for page structure, includes for rendered fragments, and imports for reusable macros or exported assignments.

## Inheritance and Blocks

```jinja
{% extends 'base.html' %}

{% block title %}Dashboard{% endblock %}
{% block content %}...{% endblock %}
```

- Put `extends` first. Output before it is rendered normally and can produce accidental content.
- A template cannot define two blocks with the same name.
- A block executes even if its declaration is textually inside a false conditional; block selection happens through inheritance.
- Named closing tags such as `{% endblock content %}` must match the opening block.
- A block can be rendered again with `self.block_name()`.
- A child block accesses its immediate parent with `super()` and can skip a level with chained calls such as `super.super()`.
- A nested block does not automatically see variables from an outer local scope. Mark it `scoped` when that access is intentional.
- A `required` block may contain only whitespace and comments until a descendant overrides it. Use modifier order `scoped required` when both apply.
- `extends`, `include`, and `import` may receive a template object supplied by the host, not only a template name.

Macros, `super()`, and `self.block_name()` return template-safe markup under autoescaping. Inputs interpolated inside them still require correct trust handling.

## Macros

```jinja
{% macro input(name, value='', type='text') -%}
  <input type="{{ type|e }}" name="{{ name|e }}" value="{{ value|e }}">
{%- endmacro %}
```

Macros expose metadata including `name`, `arguments`, `catch_varargs`, `catch_kwargs`, and `caller`. Extra positional arguments are available through `varargs`; extra keyword arguments through `kwargs`. A macro that references `caller` supports call blocks. Names beginning with `_` are private and cannot be imported.

A macro defined in a child template does not override a same-named macro referenced by the parent. Use blocks for inheritance-based replacement.

## Call Blocks

Use a call block when a macro owns the wrapper and the caller supplies body content:

```jinja
{% macro panel(title) %}
  <section><h2>{{ title }}</h2>{{ caller() }}</section>
{% endmacro %}

{% call panel('Account') %}{{ account_summary }}{% endcall %}
```

The caller can declare arguments to receive values yielded by the macro:

```jinja
{% call(item) render_list(items) %}{{ item.name }}{% endcall %}
```

## Includes

```jinja
{% include 'card.html' %}
{% include 'optional.html' ignore missing %}
{% include ['tenant-card.html', 'card.html'] %}
{% include 'isolated.html' without context %}
```

- Includes render another template at the current output position.
- The current context is passed by default; use `without context` to isolate it.
- `ignore missing` suppresses a missing-template error.
- A list selects the first existing template and provides an explicit fallback chain.
- An included template may itself extend another template, but blocks in the including template do not override the included template's blocks.

## Imports

```jinja
{% import 'forms.html' as forms %}
{% from 'forms.html' import input as field %}
```

- Imports expose macros and top-level exported assignments rather than rendering the template body.
- Imported templates are cached and do not receive the current context by default.
- `with context` passes current context and disables the normal import caching behavior; `without context` is explicit isolation.
- Private names beginning with `_` cannot be imported.

## Choosing a Mechanism

| Need | Mechanism |
| --- | --- |
| Replace named regions in a page skeleton | Inheritance and blocks |
| Render a fragment at one location | Include |
| Reuse a parameterized renderer | Macro/import |
| Let a reusable wrapper render caller content | Macro plus call block |
| Capture a rendered fragment into a value | Block assignment |

Preserve existing block names, macro arguments, and context expectations unless a coordinated refactor is authorized.
