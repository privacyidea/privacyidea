# Security

## Development Practices

privacyIDEA is security infrastructure and is developed accordingly. Every pull
request is checked by static analysis (Bandit, CodeQL), dependency scanning
(pip-audit for Python, OSV-Scanner for npm), and a linter (Ruff). Push protection for secret
scanning is enabled. The test suite provides extensive automated coverage against real MariaDB
and PostgreSQL instances. Python dependencies are fully pinned with SHA-256 hash verification.

For the full description of our security development practices, see the
[Security Development Practices](https://privacyidea.readthedocs.io/en/latest/faq/security-practices.html)
page in our documentation.

## How to report a security vulnerability

If you found a problematic security vulnerability, please
refrain from reporting an issue at GitHub but send this vulnerability to
us directly.
Please include the following details:

* The name and version of the problematic software component,
  and if possible

  * the location of the issue and 
  * the potential impact

* A detailed description to reproduce the vulnerability and

* Your name, (handle or alias) to be included in the
  disclosure and hall of fame.

You can send this information to the privacyIDEA core development team by
sending an email to

   security@privacyidea.org

or, if you want to stay anonymous/pseudonymous, you can upload your information to

   https://lancelot.netknights.it/owncloud/s/a6sVvOT0Fb3utd9

Thanks a lot for your support and your discretion.
