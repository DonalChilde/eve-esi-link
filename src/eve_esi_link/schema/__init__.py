"""Schema subsystem package.

This package provides schema-focused utilities used by both CLI and library flows:

- OpenAPI operation modeling via ``EsiSchema`` and ``SchemaOperation``.
- Local schema cache management keyed by compatibility date.
- Schema loading helpers for supported JSON envelope formats.
- Markdown generation from schema operations.

Behavior and contract details are documented in
``docs/schema-package-contracts.md``.
"""
