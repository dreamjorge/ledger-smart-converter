# Validate Config File

Validate `config/rules.yml` syntax and required structure. $ARGUMENTS

## Validation Command

```bash
# Quick validation
python -c "
import yaml
from pathlib import Path

config = yaml.safe_load(Path('config/rules.yml').read_text())
required = ['banks', 'categories', 'rules']
missing = [k for k in required if k not in config]
if missing:
    print(f'ERROR: Missing required keys: {missing}')
else:
    print(f'OK: All required keys present')
    print(f'  Banks: {len(config[\"banks\"])}')
    print(f'  Categories: {len(config[\"categories\"])}')
    print(f'  Rules: {len(config[\"rules\"])}')
"
```

## Full Validation with Schema Check

```bash
# Run healthcheck (validates config + dependencies)
python src/healthcheck.py
```

## Required Config Structure

```yaml
banks:
  - name: <bank_name>
    closing_day: <int>

categories:
  - <category_name>

rules:
  - merchant: <pattern>
    category: <category>
```

## Common Issues

- **YAML syntax errors**: Use online YAML validator or `python -c "import yaml; yaml.safe_load(open('config/rules.yml'))"`
- **Missing required keys**: Add `banks`, `categories`, or `rules` sections
- **Invalid category references**: Ensure rule categories exist in `categories` list
- **Duplicate merchants**: System warns on merge, but check for conflicts

See `config/rules.yml` for the full annotated reference config.
