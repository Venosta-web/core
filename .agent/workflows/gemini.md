---
description: Delegate tasks to Gemini CLI for code assistance
---

# Gemini CLI Workflow

Use this workflow to delegate complex development tasks to the Gemini CLI.

## Available Tasks

### 1. Code Explanation

Explain logic and flow of code:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task explain \
  --file <path/to/file>
```

### 2. Test Generation

Generate comprehensive tests:

```bash
# For Python (pytest)
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task test \
  --file <path/to/file.py> \
  --framework pytest

# For TypeScript (Jest)
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task test \
  --file <path/to/file.ts> \
  --framework jest
```

### 3. Code Refactoring

Suggest refactoring improvements:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task refactor \
  --file <path/to/file> \
  --issue "DRY principle"
```

Common refactoring issues:
- "DRY principle"
- "SOLID principles"
- "async/await conversion"
- "type safety improvements"
- "code complexity reduction"

### 4. Documentation Generation

Add comprehensive docstrings:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task doc \
  --file <path/to/file>
```

### 5. Debug Assistance

Analyze errors and suggest fixes:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task debug \
  --file <path/to/file> \
  --error "AttributeError: 'NoneType' object has no attribute 'foo'"
```

### 6. Code Migration

Migrate code to modern standards:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task migrate \
  --file <path/to/file>
```

## Integration with Existing Workflows

### With /codereview

During code review, use Gemini CLI to:
- Explain complex logic sections
- Suggest type hints and documentation
- Identify potential bugs

```bash
# Review a coordinator file
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task explain \
  --file vendor/growspace_manager/custom_components/growspace_manager/coordinator.py
```

### With /pytest

Enhance test coverage:

```bash
# Generate tests for uncovered code
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task test \
  --file vendor/growspace_manager/custom_components/growspace_manager/services/plant.py \
  --framework pytest
```

### With /quality_scale

Support quality scale compliance:

```bash
# Add missing docstrings (Platinum requirement)
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task doc \
  --file vendor/growspace_manager/custom_components/growspace_manager/binary_sensor.py
```

## Advanced Usage

### Custom Context

Provide additional context for better results:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task refactor \
  --file path/to/file.py \
  --context "This is part of a Home Assistant coordinator that manages plant lifecycle data"
```

### Output to File

Save Gemini output to a file for review:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task test \
  --file path/to/file.py \
  --output /tmp/generated_tests.py
```

### Token Limit Control

Adjust maximum lines sent to Gemini:

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task explain \
  --file path/to/large_file.py \
  --max-lines 5000
```

## Safety Features

The wrapper script automatically:

- ✅ Detects and redacts secrets (API keys, passwords, tokens)
- ✅ Warns about large files (>10,000 lines)
- ✅ Blocks forbidden files (.env, secrets.yaml)
- ✅ Validates file extensions for safety
- ✅ Provides timeout protection (2 minutes)

**Never sends:**
- Environment files (.env)
- Hardcoded credentials
- PII (Personally Identifiable Information)
- Secret keys or certificates

## Best Practices

1. **Start Small**: Test with small files first
2. **Review Output**: Always review Gemini output before applying
3. **Run Tests**: Verify generated code passes tests
4. **Check Linting**: Ensure output follows project standards
5. **Be Specific**: Use `--context` and `--issue` flags for targeted results

## Troubleshooting

### "Unsafe file" Error

The file type isn't allowed. Check:
- Is it a `.env` file? (forbidden)
- Is the extension in SAFE_EXTENSIONS?

### "Found secrets" Warning

The script detected potential secrets and will redact them. Review the output to ensure nothing sensitive is sent.

### Timeout Error

File is too large or Gemini is taking too long:
- Try `--max-lines` with a lower value
- Split the file into smaller chunks
- Focus on specific functions/classes

---

**Remember**: Gemini CLI is a powerful assistant, but **human review is mandatory**. Always verify output before committing.
