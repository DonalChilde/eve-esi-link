# Schema handling refactor plan.

Right now, the cli offers fetching the schema and showing/saving in a couple of formats.

Cli commands also support the loading of a schema for use in processing commands, but the variety of schema formats can lead to confusion and complication, for little gain.

## Plan

- narrow saved schema format to unaltered, and dereferenced-timestamped.
- include compatibility date, iso_date (downloaded, UTC, second precision) in output file name.
  - unaltered schema name - "{compatibility_date}-{download_date}-schema.json"
  - dereferenced file name - "{compatibility_date}-{download_date}-link-schema.json"
- NOTE: dereferenced-timestamped is the serialized formet of EsiSchema. EsiSchemaRoot can be used to deserialize.


- cli commands that make use of schema to make an EsiSchema can autodetect the format based on internal structure, so that an already dereferenced schema is not derefed twice.
  - helper function to load schema from file, with optional timestamp, return EsiSchema
    - load json object
    - try EsiSchemaRoot first
    - if fail, then EsiSchema from unaltered schema with optional timestamp.
  - ensure helper function `is_dereferenced` that uses internal structure to determine dereferenced.
  

## Future plan

application directory has a cache directory of dereferenced-timestamped schema files, named as per above fetch file name scheme
  - needs function to discover and parse files names in a directory.
if not provided to cli, cli commands use the most recent compat_date cached file.
add cli commands to view, update, clear cached files, can cache all valid compat dates.
add setting for schema path directory, so its visible in the context.
cli commands fail if no schema in settings, and no schema passed into command.