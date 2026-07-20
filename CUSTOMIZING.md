# Customizing the profile

The editable profile settings are grouped at the top of `generate_profile.py`:

- `BIRTH_DATE` controls the age calculation.
- `WEBSITE_URL` controls the clickable website beneath the text panel.
- `ASCII_MAX_LINES` controls how much of the portrait is displayed. The profile uses the first nonblank lines from `ascii-art.txt`.
- `INFO_WIDTH` controls the width of the terminal information panel.

Edit `ascii-art.txt` to replace the portrait. The generator automatically aligns the portrait and information panel, then writes `README.md`.

## Private statistics

GitHub's built-in workflow token can only access the repository containing the workflow. The profile therefore works without configuration but cannot enumerate your other private repositories.

To include the private-repository count, create a fine-grained personal access token that can access the repositories you want counted. Grant read-only access and no write permissions, then store it as a repository secret named `PROFILE_STATS_TOKEN`:

```powershell
gh secret set PROFILE_STATS_TOKEN --repo lostspaceship/lostspaceship
```

Paste the token when prompted. Never add the token to a file or commit it. The workflow automatically prefers this secret when present and otherwise falls back to its repository-scoped `GITHUB_TOKEN`.
