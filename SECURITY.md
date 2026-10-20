# Security

## Reporting a problem

If you find something here that shouldn't be public (a key, a password, an email address, an account number, a
private name) or a script that does something unsafe, please report it privately: open this repository's
**Security** tab and choose **Report a vulnerability**, or use the contact form at
https://giddyupdata.com/contact.html. Please don't open a public issue for these.

I'm one person. I aim to reply within a week; when I'm teaching or traveling it can take longer. There is no bug
bounty.

## In scope

- Secrets or personal details committed by mistake, anywhere in the repository.

## Out of scope

- This is an example built for my own machine, not supported software. Problems other than secrets can go in an
  ordinary issue.
- Vulnerabilities in third-party tools. Please report those to their maintainers.

## If you adapt these scripts

- Never commit keys. Keep them in a secrets manager, your operating system's keyring or environment variables, and
  set up `.gitignore` before you create any `.env` file.
- The scripts were run on a one-person machine where the agent runs with its permission prompts off. Don't copy
  that: keep the prompts on, and on a shared or company computer start from the stricter settings in the starter
  kit ([ai-workspace-blueprints](https://github.com/david-giddyupdata/ai-workspace-blueprints), `use/settings/`).
- The scripts drive a browser that you have signed in to. Anything that browser can do as you, a script can do.
