# Security

Airline Cascades is a single-operator simulation with no user accounts. It
is meant to run locally or behind your own authentication, not exposed on
the open internet.

What it does protect against:

- **CSRF:** every HTML form carries a per-session token, checked on every
  POST. The JSON API only accepts `application/json` bodies, which a
  cross-site form can't send.
- **SQL injection:** all values are passed as query parameters. The few
  identifiers built into SQL (table and column names on the admin and schema
  pages) come from a fixed configuration or are checked against
  `information_schema` first.
- **Secrets:** nothing is committed; settings come from the environment or
  an untracked `.env`. Set `SECRET_KEY` in any shared deployment.

## Reporting a problem

Please report vulnerabilities privately through GitHub's
[security advisory form](https://github.com/banitsriram/AIRLINE-CASCADES/security/advisories/new)
rather than in a public issue.
