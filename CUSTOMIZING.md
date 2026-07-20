# Customizing the profile

The editable profile settings are grouped at the top of `generate_profile.py`:

- `BIRTH_DATE` controls the age calculation.
- `WEBSITE_URL` controls the clickable website beneath the text panel.
- `ASCII_STRETCH` controls the portrait width. `1.0` is unchanged and `1.15` is 15% wider.
- `INFO_WIDTH` controls the width of the information panel.
- `USE_RED_HIGHLIGHT` uses GitHub's selectable `diff` syntax highlighting to approximate a red-on-dark terminal. Set it to `False` for neutral text.

Edit `ascii-art.txt` to replace the portrait. The generator automatically aligns the portrait and information panel.

## Private statistics

GitHub's built-in workflow token can only access the repository containing the workflow. The profile therefore works without configuration but cannot enumerate your other private repositories.

To include the private-repository count, create a fine-grained personal access token that can access the repositories you want counted. Grant read-only access and no write permissions, then store it as a repository secret named `PROFILE_STATS_TOKEN`:

```powershell
gh secret set PROFILE_STATS_TOKEN --repo lostspaceship/lostspaceship
```

Paste the token when prompted. Never add the token to a file or commit it. The workflow automatically prefers this secret when present and otherwise falls back to its repository-scoped `GITHUB_TOKEN`.
