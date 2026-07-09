import json

from yaml import safe_dump

from .models import EsiSchema, SchemaOperation

# TODO generate documentation in markdown for an EsiSchema, grouping operations by tag,
# then operationid, sorted. Include the download date of the schema. The documentation should include the
# operation ID, path, method, description, parameters, request body, and response schema
# for each operation. Offer a choice of output formats (JSON or YAML) for the sections
# that must be fenced code blocks. The output format
# should be configurable by the user. The documentation should be generated in a way
# that is easy to read and understand, with clear headings and subheadings for each
# section. The documentation should also include a table of contents that links to each
# section of the document. The documentation should be generated in a way that is easy
# to navigate, with clear links to each section of the document.
