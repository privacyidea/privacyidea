# Secrets Directory

This directory contains sensitive files required for the HA deployment. **Never commit these files to git!**

## Required Secret Files

### 1. `enckey` - PrivacyIDEA Encryption Key

The master encryption key used to encrypt tokens and sensitive data in the database.

**Generate:**
```bash
python3 -c "import os; print(os.urandom(96).hex())" > enckey
```

**Important:**
- This key is critical - losing it means you cannot decrypt your tokens
- Back it up securely and separately from your database backups
- Never change this key after tokens are created

### 2. `mariadb_password` - Database User Password

Password for the `pi` database user used by the application.

**Generate:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_password
```

**Note:** This password must also be set in your `.env` file as `MARIADB_PASSWORD`

### 3. `mariadb_root_password` - Database Root Password

Root password for MariaDB administrative access.

**Generate:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_root_password
```

**Note:** This password must also be set in your `.env` file as `MARIADB_ROOT_PASSWORD`

## Quick Setup

Generate all secrets at once:

```bash
cd secrets

# Generate encryption key
python3 -c "import os; print(os.urandom(96).hex())" > enckey

# Generate database passwords
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_password
python3 -c "import secrets; print(secrets.token_urlsafe(32))" > mariadb_root_password

# Verify files were created
ls -lh
```

## Security Best Practices

1. **File Permissions:** Ensure restrictive permissions
   ```bash
   chmod 600 secrets/*
   ```

2. **Backup:** Store encrypted backups in a secure location separate from your deployment

3. **Rotation:** Plan for periodic password rotation (except `enckey` which should never change)

4. **Access Control:** Only authorized personnel should have access to these files

5. **Git:** The parent `.gitignore` file prevents these from being committed, but always verify:
   ```bash
   git status
   ```

## Troubleshooting

**Problem:** Container can't read secret files
**Solution:** Check file permissions and ensure files exist with content (not empty)

**Problem:** Authentication failures
**Solution:** Verify passwords in secret files match those in `.env` file

**Problem:** Lost encryption key
**Solution:** If you lose `enckey`, encrypted data cannot be recovered. Always maintain backups!
