# Making Requests Via The CLI

To make a single request, you might run
```bash
eve-link run --from ./status.request.json
```
This results in 
```json
{"players": 25236, "server_version": "3435006", "start_time": "2026-07-15T11:03:27Z"}
```
Because no schema was specified, the most recent cached schema was used. You should update the cached schemas when new ones come available.

You can also pipe the request json into the command
```bash
cat ./status.request.json | eve-link run
```

This can be useful when integrating with other scripts.

output can also be saved to a file, or piped
```bash
cat ./status.request.json | eve-link run --to ./status-response.json
# or
cat ./status.request.json | eve-link run | foo-do-something
```
For a single EsiRequest, the --debug flag will output the complete EsiResonse|FailedEsiResponse object
```bash
eve-link run --from ./status.request.json --debug --indent 2
```

EsiRequestGroup operates the same way, except that the output is always the complete EsiResponseGroup object. The expectation is, that group requests will normally be post processed by the user, so no assumptions are made about desired output format.

An example EsiRequestGroup
```bash
eve-link run-group --from ./languages.request-group.json --indent 2
```
