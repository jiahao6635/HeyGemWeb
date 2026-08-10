# Security Policy

## Supported version

Security fixes are applied to the latest revision of the `main` branch. The project does not currently publish stable release branches.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue. Use [GitHub private vulnerability reporting](https://github.com/jiahao6635/HeyGemWeb/security/advisories/new) and include:

- affected revision or commit;
- deployment assumptions and required backend services;
- reproduction steps using non-sensitive test data;
- impact and any known workaround.

Do not include real credentials, access tokens, private service URLs, personal media, generated biometric material, or private logs. The maintainer will acknowledge a complete report as soon as practical and coordinate disclosure after a fix or mitigation is available.

## Deployment responsibility

HeyGemWeb processes uploaded media and communicates with separately deployed services. Operators are responsible for HTTPS, network isolation, storage permissions, retention, consent, and compliance appropriate to their environment. Gradio server-side authentication protects the UI and API endpoints, but it does not provide MFA, rate limiting, or a complete public multi-tenant security boundary.
