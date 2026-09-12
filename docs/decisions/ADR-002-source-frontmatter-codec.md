# ADR-002: Use deterministic JSON frontmatter for Canonical Source manifests

- Status: Accepted
- Date: 2026-09-12
- Scope: A1 implementation choice

## Decision

`source.md` stores the A1 manifest between Markdown `---` delimiters as
deterministic, UTF-8 JSON. JSON is a YAML 1.2-compatible subset, so the
frontmatter remains machine-readable without adding a YAML dependency. The
Markdown body is required to be empty; raw input is stored only at
`payload/original`.

## Consequences

- `serialize_source` and `parse_source` are the only codec path.
- Unknown fields and unsupported schema versions fail closed.
- A later external YAML presentation, if required, must preserve semantic
  equality and must not become a second persistence codec.
