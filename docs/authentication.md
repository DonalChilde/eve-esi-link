# Authentication

To make requests to ESI's authenticated endpoints, you will need to register an app with EVE Online. This is free, and easy to do.

## Create `credentials.json` from EVE Developers

1. Go to https://developers.eveonline.com/applications and sign in.
2. Create a new ESI application, or open an existing one. Selecting all scopes is recommended.
3. Copy/paste the application JSON payload from the portal to a file.
4. Save it locally as `<my-credentials>.json`.

Expected JSON shape:

```json
{
  "name": "My ESI App",
  "description": "Optional human-readable description",
  "clientId": "your_client_id",
  "clientSecret": "your_client_secret",
  "callbackUrl": "http://localhost:8080/callback",
  "scopes": ["scope1", "scope2"]
}
```

## Add Credentials and Authorize a Character

Add your app credentials to the eve-link auth store
```bash
eve-link auth-manager credentials add --from ./<my-credentials>.json
eve-link auth-manager credentials display
```
Note the credential id, you will use this in authenticated requests.

To add a character to the auth store, you need the character id. You can look it up with
```bash
eve-link auth-manager characters search --name "My Cool Name"
```
This actually searches all in game names, so
```bash
eve-link auth-manager characters search --name "Tritanium"
```
gets back a character, and a mineral.

Now, authorize the character
```bash
eve-link auth-manager characters add <character_id> --cred-name "My ESI App Name"
eve-link auth-manager characters display
```
The add character command should open your system web browser to finish the authentication.

!!! note
    eve-link should support multiple separate sets of credentials and characters, but it hasn't been tested.