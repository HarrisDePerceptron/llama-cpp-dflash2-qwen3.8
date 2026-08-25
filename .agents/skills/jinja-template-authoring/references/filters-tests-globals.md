# Built-in Filters, Tests, and Globals

This catalog targets the Jinja 3.1 stable Templates documentation. A project may add, remove, wrap, or policy-configure names. Check the installed version and environment when exact signatures matter.

## Built-in Filters

The documented filters are grouped here for discovery, not by exact signature:

- Text and markup: `capitalize`, `center`, `escape` (`e`), `forceescape`, `format`, `indent`, `lower`, `replace`, `safe`, `string`, `striptags`, `title`, `trim`, `truncate`, `upper`, `wordcount`, `wordwrap`.
- Sequence selection and transformation: `batch`, `first`, `groupby`, `join`, `last`, `list`, `map`, `random`, `reject`, `rejectattr`, `reverse`, `select`, `selectattr`, `slice`, `sort`, `unique`.
- Numbers and aggregation: `abs`, `filesizeformat`, `float`, `int`, `max`, `min`, `round`, `sum`.
- Mapping and object access: `attr`, `dictsort`, `items`, `xmlattr`.
- Defaults and serialization: `default` (`d`), `pprint`, `tojson`, `urlencode`, `urlize`.
- General sequence size: `length` (`count`).

Important behavior:

- `attr` does not fall back to item lookup.
- `default(value, true)` replaces falsey values as well as undefined ones.
- `map`, `select`, `selectattr`, `reject`, `rejectattr`, and `unique` return lazy iterators; use `list` only when materialization is needed.
- `groupby` sorts before grouping. In Jinja 3.1 its default comparison is case-insensitive and it supports a fallback value for missing attributes.
- `items` produces an empty iterator for undefined input and was added in Jinja 3.1.
- `last` requires a reversible sequence; convert a generator with `list` first when appropriate.
- `safe` asserts a trust boundary. Do not apply it to unsanitized user-controlled HTML.
- `forceescape` escapes even safe values and can produce double escaping.
- `tojson` is safe for HTML and `<script>` content, but not directly for a double-quoted HTML attribute. Prefer a single-quoted attribute or apply the documented escaping strategy.
- `xmlattr` is for trusted attribute keys. Never allow user-controlled keys; modern 3.1 releases reject spaces and delimiter characters in keys.
- `urlize` behavior can depend on environment policies and it is not an HTML sanitizer.

## Built-in Tests

The documented tests are:

- Presence and type: `defined`, `undefined`, `none`, `boolean`, `true`, `false`, `integer`, `float`, `number`, `string`, `mapping`, `sequence`, `iterable`, `callable`.
- Value properties: `even`, `odd`, `divisibleby`, `lower`, `upper`, `escaped`.
- Comparison and identity: `eq` (`equalto`, `==`), `ne` (`!=`), `lt` (`<`), `le` (`<=`), `gt` (`>`), `ge` (`>=`), `in`, `sameas`.
- Environment capability: `filter`, `test`.

Important distinctions:

- `sameas` checks object identity, not equality.
- `escaped` checks whether a value is marked safe markup; it does not prove that untrusted content was sanitized correctly.
- `filter` and `test` let a template check whether an optional named filter or test exists before using it.
- Combine tests with `and`, `or`, and `not`; write `is not` and `not in` in that order.

## Built-in Global Functions

- `range`: `range(start, stop, step)` produces integer ranges for iteration.
- `dict`: constructs a dictionary using Python-style forms supported by Jinja.
- `cycler`: cycles supplied values and exposes `current`, `next()`, and `reset()`.
- `joiner`: emits nothing on its first call and the configured separator on later calls.
- `namespace`: creates an object whose attributes can carry state across scopes.
- `lipsum`: generates placeholder text and should not be treated as application content.

## Selection Guidance

- Prefer a test for a condition and a filter for a transformation.
- Prefer project data shaping over long pipelines that obscure business rules.
- Check the official API entry when argument order, async behavior, HTML safety, or a version-added detail affects correctness.
- Never assume a built-in name is available when the project uses a restricted or customized environment.
