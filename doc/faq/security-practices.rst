.. _security_practices:

Security Development Practices
------------------------------

.. index:: Security, SDLC, Secure Development

privacyIDEA is security infrastructure — it guards authentication flows for
organizations that depend on it. The development practices described here
reflect that responsibility.

For cryptographic details see :ref:`crypto_considerations`.
For reporting vulnerabilities see `SECURITY.md <https://github.com/privacyidea/privacyidea/blob/master/SECURITY.md>`_.

Continuous Integration & Security Scanning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every pull request is checked by the following tools, and some of them also
run on a nightly schedule:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Tool
     - Purpose
   * - **Bandit** (SAST)
     - Python static security analysis. Results uploaded to the GitHub Security
       tab as SARIF. In CI, excludes ``./docs``, ``./tests``, and
       ``./migrations``.
   * - **CodeQL**
     - Semantic analysis for Python and JavaScript. Results to the GitHub
       Security tab.
   * - **pip-audit** (SCA)
     - Dependency vulnerability scanning against the OSV database for Python
       packages.
   * - **OSV-Scanner**
     - Dependency vulnerability scanning for the Angular frontend's npm
       dependencies. Results uploaded to the GitHub Security tab as SARIF.
   * - **Ruff**
     - Fast Python linter catching real bugs (unused variables, undefined names,
       format-string mistakes) beyond style enforcement.
   * - **Zizmor**
     - GitHub Actions workflow security analysis.
   * - **Dependency Review**
     - Warns on pull requests that introduce known-vulnerable packages.
   * - **GitHub Secret Scanning**
     - Detects leaked credentials in commits. Push protection is enabled,
       blocking pushes that contain recognized secrets before they reach the
       repository.

Testing
~~~~~~~

The test suite comprises thousands of test cases and extensive test code, run
by pytest with high code coverage. Tests execute against both **MariaDB** and
**PostgreSQL**.

Coverage by security-relevant area:

- **Cryptography:** AES encryption/decryption, Argon2 PIN/password hashing,
  ECC and RSA key operations, constant-time comparison, HSM integration.
- **Authentication:** SQL and LDAP resolver authentication, token-based 2FA
  flows, challenge-response validation, replay protection, fail counter
  mechanisms.
- **Token validation:** HOTP, TOTP, FIDO2/WebAuthn, passkeys, push, SMS,
  email, registration, and certificate tokens.
- **Access control:** Policy-based authorization, admin authentication, audit
  logging.
- **Database migrations:** Dedicated tests validate schema changes against
  real database instances.

Coverage is collected via pytest-cov and uploaded to Codecov.

Dependency Management
~~~~~~~~~~~~~~~~~~~~~

Python dependencies are managed via ``pip-compile`` with ``--generate-hashes``,
producing a fully pinned ``requirements.txt`` with SHA-256 hash verification for
every package. This prevents supply-chain substitution attacks — a compromised
package on PyPI that does not match the recorded hash will be rejected at
install time.

Dependencies are updated manually on a deliberate schedule rather than via
automated pull requests. Vulnerability detection is handled by pip-audit
(Python) and OSV-Scanner (npm) in CI, giving the team visibility into the
security posture without turning every upstream CVE into an unplanned emergency.

GitHub Actions versions are kept current via Dependabot (weekly).

Cryptographic Discipline
~~~~~~~~~~~~~~~~~~~~~~~~

- **No hand-rolled cryptography.** All operations use the ``cryptography``
  library or well-audited alternatives (``argon2-cffi``, ``bcrypt``).
- **Symmetric encryption:** For key-file based encryption of token, config,
  and value secrets, privacyIDEA uses AES-256-CBC with separate 256-bit keys
  stored in an encrypted key file. Other AES-CBC based import/export or legacy
  compatibility paths exist elsewhere in the codebase.
- **Password and PIN hashing:** Argon2 (9 rounds). Admin passwords use an
  additional per-installation pepper.
- **Constant-time comparison:** ``hmac.compare_digest()`` for PIN and token
  verification (prevents timing attacks).
- **Random generation:** Cryptographically secure randomness via
  ``os.urandom`` / ``secrets`` where appropriate.
- **HSM support:** PKCS#11 interface for hardware-backed key storage.
- **Audit trail signing:** RSA 2048-bit with SHA-256 (configurable).
- **Safe parsing:** ``defusedxml`` for XML (prevents XXE), ``yaml.safe_load()``
  for YAML.
- **Security headers:** Flask-Talisman integration with Content Security Policy.

See :ref:`crypto_considerations` for details on key management, hash algorithms,
and audit signing.

Release Process
~~~~~~~~~~~~~~~

- **Release artifacts:** Tag-triggered GitHub Actions workflows build the
  WebUI and Python distribution artifacts for each tagged release.
- **GitHub releases:** The automated workflow creates a GitHub release as part
  of the tagged release process. Any signing or package index publication steps
  should be considered separate from the workflow unless explicitly documented
  elsewhere.
- **Changelog:** Versioned entries documenting features, enhancements, and
  fixes.

Responsible Disclosure
~~~~~~~~~~~~~~~~~~~~~~

Security vulnerabilities can be reported to ``security@privacyidea.org``.
An anonymous upload option is also available. See
`SECURITY.md <https://github.com/privacyidea/privacyidea/blob/master/SECURITY.md>`_
for details.
