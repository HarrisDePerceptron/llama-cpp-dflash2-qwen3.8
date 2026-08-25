# Control Flow and Scope

Use this reference for iteration, branching, assignment, recursion, and state that must cross a scope boundary.

## For Loops

```jinja
{% for user in users if user.enabled %}
  {{ loop.index }}. {{ user.name }}
{% else %}
  No enabled users.
{% endfor %}
```

Filtering in the `for` declaration keeps loop metadata aligned with the rendered items. The `else` branch runs when no item is iterated, including when filtering removes every item.

Available `loop` values:

| Value | Meaning |
| --- | --- |
| `index`, `index0` | Current position, one- or zero-based |
| `revindex`, `revindex0` | Remaining positions, one- or zero-based |
| `first`, `last`, `length` | Boundary flags and collection length |
| `previtem`, `nextitem` | Adjacent item, undefined at the boundary |
| `cycle(a, b, ...)` | Cycle through supplied values |
| `changed(value)` | True when the value differs from the prior call |
| `depth`, `depth0` | One- or zero-based recursion depth |

Jinja loops do not support `break` or `continue` unless the loop-controls extension is enabled. Prefer declarative filtering for portability.

## Recursive Loops

Add `recursive` to a loop and call `loop(children)` where nested output belongs:

```jinja
{% for item in tree recursive %}
  <li>{{ item.title }}
    {% if item.children %}<ul>{{ loop(item.children) }}</ul>{% endif %}
  </li>
{% endfor %}
```

If an inner loop needs the outer recursive callable, save it before entering the inner loop, for example `{% set outer_loop = loop %}`.

## Conditionals

Use `{% if %}`, `{% elif %}`, and `{% else %}`. An `if` statement does not introduce a new assignment scope, but blocks, loops, macros, and `with` do.

## Assignment

```jinja
{% set title = page.title %}
{% set left, right = pair %}
```

Top-level assignments are exported and can be imported by other templates. Names beginning with `_` are private to imports.

Assignments inside a loop are cleared when the iteration scope ends. They are not a way to mutate an outer scalar. Use a namespace for intentional cross-scope state:

```jinja
{% set state = namespace(found=false) %}
{% for item in items %}
  {% if item.active %}{% set state.found = true %}{% endif %}
{% endfor %}
```

Attribute assignment in `set` is valid only for namespace objects. Do not use Jinja 3.2 namespace multiple-assignment syntax when targeting the stable 3.1 series.

## Block Assignment and Filter Blocks

Capture rendered content with block `set`; a filter may be applied to the captured value:

```jinja
{% set navigation | trim %}
  {% include 'navigation.html' %}
{% endset %}
```

Apply a filter to a rendered region with a filter block:

```jinja
{% filter upper %}{{ heading }}{% endfilter %}
```

## With Scope

`with` creates an inner scope and is built in for supported Jinja 3.1 installations:

```jinja
{% with total=items|sum(attribute='price') %}
  {{ total }}
{% endwith %}
```

Values declared in the same `with` opening clause do not see one another's newly assigned values. Compute a dependency before the block or in a nested `with`.

## Scope Summary

| Construct | New local scope | Important behavior |
| --- | --- | --- |
| `if` | No | Assignments remain in the surrounding scope |
| `for` | Yes | Scalar assignments do not escape the loop |
| `block` | Yes | Outer variables in nested blocks require `scoped` |
| `macro` | Yes | Arguments and local assignments stay local |
| `with` | Yes | Temporary values disappear at `endwith` |
| `namespace` | Purpose-built | Attributes can carry state across scopes |

For block scoping and macro behavior, also read [composition.md](composition.md).
