# Security Policy

## Supported Use

This project is intended for authorized use with a school-provided XipuAI web account. It does not bypass authentication, CAPTCHA, rate limits, or school access controls.

## Sensitive Local Files

Never commit these files:

- `school_gpt_state.json`
- `gateway_config.local.json`
- `.env`
- `request.json`
- `private_request.json`
- `*.local.json`
- `*.log`

The saved login state may contain cookies, localStorage data, and tokens for the signed-in school account. Treat it like a password.

## Reporting Issues

If you find a security issue, do not open a public issue containing secrets, cookies, tokens, or personal data. Rotate any exposed credentials immediately and report the issue privately to the repository owner.

## Safe Testing

Use the included tests and mocked adapters for development whenever possible. Avoid sending real prompts to the upstream school AI while testing gateway routing, model selection, configuration, or UI changes.
