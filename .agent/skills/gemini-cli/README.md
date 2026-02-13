# Gemini CLI Integration

This skill provides AI-assisted code development through the Google Gemini CLI.

## 📂 Structure

```
gemini-cli/
├── SKILL.md              # Main skill documentation
├── scripts/
│   └── gemini_cli.py     # Python wrapper for safe Gemini CLI execution
└── README.md             # This file
```

## 🚀 Quick Start

### 1. Explain Code

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task explain \
  --file path/to/file.py
```

### 2. Generate Tests

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task test \
  --file path/to/file.py \
  --framework pytest
```

### 3. Refactor Code

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task refactor \
  --file path/to/file.py \
  --issue "DRY principle"
```

### 4. Add Documentation

```bash
python3 .agent/skills/gemini-cli/scripts/gemini_cli.py \
  --task doc \
  --file path/to/file.py
```

## 📖 Full Documentation

See [`SKILL.md`](SKILL.md) for:
- Complete delegation protocols
- Safety constraints and secret detection
- Task-specific templates
- Integration with existing workflows
- Best practices

## 🔄 Workflow Integration

Use the `/gemini` workflow for easy access:

```bash
# See available commands
cat .agent/workflows/gemini.md
```

## 🛡️ Safety Features

The wrapper automatically:
- ✅ Detects and redacts secrets
- ✅ Blocks unsafe files (.env, etc.)
- ✅ Warns about large files
- ✅ Provides timeout protection

## 🎯 Use Cases

**Good for:**
- Generating boilerplate code
- Explaining complex logic
- Creating test scaffolds
- Adding documentation
- Refactoring suggestions

**Avoid for:**
- Security-sensitive operations
- Production-critical logic without review
- Known patterns (use IDE snippets)

## ⚠️ Important

**Always review Gemini output before applying!** Never blind-commit AI-generated code.

---

For detailed usage, see [SKILL.md](SKILL.md) and [/gemini workflow](../../workflows/gemini.md).
