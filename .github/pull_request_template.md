## Problem

Describe the user or maintainer problem this change addresses.

## Changes

-

## Validation

```text
python -m compileall -q app.py config.py services
python -m unittest discover -s tests -v
bash -n deploy.sh manage.sh
```

## Checklist

- [ ] The change is focused and contains no credentials, private media, generated files, or logs.
- [ ] Tests cover new or changed deterministic behavior.
- [ ] English and Chinese documentation are updated when user-facing behavior changes.
- [ ] External backend, FFmpeg, GPU, and platform assumptions are stated explicitly.
