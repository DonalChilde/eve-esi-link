# Schema handling refactor plan.

Right now, the cli offers fetching the schema and showing/saving in a couple of formats.

Cli commands also support the loading of a schema for use in processing commands, but the variety of schema formats can lead to confusion and complication, for little gain.

## Plan


  

## Future plan

application directory has a cache directory of EsiSchema format schema files.
  - needs function to discover and parse files names in a directory.
if not provided to cli, cli commands use the most recent compat_date cached file.
add cli commands to view, update, clear cached files, can cache all valid compat dates.
add setting for schema path directory, so its visible in the context.
cli commands fail if no schema in settings, and no schema passed into command.