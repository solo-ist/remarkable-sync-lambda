# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities through [GitHub's private vulnerability reporting](https://github.com/solo-ist/remarkable-sync-lambda/security/advisories/new) rather than opening a public issue.

I'll acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Scope

Security issues include:
- Authentication bypass
- Secret/credential exposure
- Injection vulnerabilities (command, SQL, etc.)
- Dependency vulnerabilities with known exploits

Regular bugs (crashes, incorrect output, formatting issues) can be reported as normal GitHub issues.

## Architecture Notes

This service uses a **Bring Your Own Key (BYOK)** model for Anthropic API access. User-provided API keys are passed through to Anthropic but are never stored, logged, or persisted. The Lambda's own authentication key is stored in AWS Secrets Manager.
