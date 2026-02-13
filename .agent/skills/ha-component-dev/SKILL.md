---
name: Home Assistant Component Development
description: Expert development workflow for Home Assistant custom components targeting 2025.12.5, Python 3.13+, with quality scale compliance
---

# Home Assistant Component Development Skill

## Overview

This skill provides comprehensive guidance for developing high-quality Home Assistant custom components, specifically tailored for **Home Assistant Core 2025.12.5** with **Python 3.13+**. It ensures compliance with Home Assistant's Integration Quality Scale and enforces best practices for async programming, typing, testing, and documentation.

## Target Projects

- **Component**: `growspace_manager` custom component
- **Location**: `/home/maxi/core/core/vendor/growspace_manager`
- **Quality Scale**: Silver (targeting Gold/Platinum)
- **Python Version**: 3.13+
- **Home Assistant Core**: 2025.12.5

## Core Principles

### 1. Quality Scale Compliance

Always check `manifest.json` for the current quality scale tier and verify compliance in `quality_scale.yaml`:

```yaml
# Track your progress
- rule: <rule_id>
  status: done | exempt | todo
  reason: "<exemption reason if applicable>"
```

**Quality Scale Tiers**:
- **Bronze**: Mandatory foundation (required for all integrations)
- **Silver**: Enhanced functionality and robustness (current target)
- **Gold**: Advanced features for polished integration
- **Platinum**: Highest standard, exemplary integrations

### 2. Modern Python Standards (Python 3.13+)

**Required Features**:
- ✅ Pattern matching (`match`/`case`)
- ✅ Comprehensive type hints (strict typing for Platinum)
- ✅ F-strings for ALL string formatting
- ✅ Dataclasses for data structures
- ✅ Walrus operator (`:=`) where appropriate
- ✅ Structural pattern matching for complex conditionals

**Type Hints**:
```python
# Custom config entry types
type MyIntegrationConfigEntry = ConfigEntry[MyClient]

# All functions need return type hints
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up from a config entry."""
    ...
```

### 3. Asynchronous Programming (Critical)

**All I/O operations MUST be asynchronous**:

✅ **Good**:
```python
# Use asyncio.gather for concurrent operations
results = await asyncio.gather(
    *[fetch_data(item) for item in items]
)

# Proper async client usage
client = MyClient(entry.data[CONF_HOST], async_get_clientsession(hass))
```

❌ **Bad**:
```python
# Never use sleep in loops
for item in items:
    await asyncio.sleep(1)
    result = await fetch_data(item)

# No blocking calls
import time
time.sleep(1)  # NEVER DO THIS
```

**WebSession Injection (Platinum)**:
```python
# Support passing websession to dependencies
from homeassistant.helpers.aiohttp_client import async_get_clientsession

client = MyClient(
    entry.data[CONF_HOST],
    async_get_clientsession(hass)
)
```

### 4. Error Handling

**Principles**:
- Use the most specific exception type
- Keep `try` blocks minimal (only wrap code that can throw)
- Avoid bare `except:` except for background tasks and config flows

```python
# Good - specific exception handling
try:
    data = await client.fetch_growth_data()
except ClientConnectionError as err:
    raise ConfigEntryNotReady(
        f"Connection failed: {err}"
    ) from err
except InvalidData as err:
    _LOGGER.error("Invalid data received: %s", err)
    return None

# Acceptable bare except for background tasks
async def _async_update_data():
    try:
        return await self._fetch_data()
    except Exception:  # OK for coordinator update
        _LOGGER.exception("Unexpected error fetching data")
        raise UpdateFailed
```

### 5. Logging Best Practices

**Format Rules**:
- ❌ No periods at end of log messages
- ✅ Use lazy logging (pass variables as arguments)
- ❌ Never log sensitive data (API keys, tokens, passwords)

```python
# Good - lazy logging
_LOGGER.debug("Processing growspace: %s", growspace_id)
_LOGGER.error("Failed to connect to %s: %s", host, error)

# Bad - eager formatting
_LOGGER.debug(f"Processing growspace: {growspace_id}")  # ❌
_LOGGER.error(f"Connection failed.")  # ❌ Has period
```

### 6. Testing Requirements

**Critical: Test-Driven Development**

Run tests **after every completed task**:

```bash
# For specific test file (after bug fixes)
./venv/bin/pytest tests/test_<module>.py -v

# For affected modules (after feature additions)
./venv/bin/pytest tests/test_<module1>.py tests/test_<module2>.py -v

# Full test suite (before completing any task)
./venv/bin/pytest tests/

# With coverage (for critical changes)
./venv/bin/pytest --cov=custom_components.growspace_manager \
  --cov-report=term-missing tests/
```

**Test Workflow**:
1. ✅ Run tests after every completed task
2. ✅ Before marking task as complete, verify all tests pass
3. ✅ For bug fixes, add test that reproduces bug first, then fix
4. ✅ For new features, implement tests alongside feature code
5. ✅ Never mark work complete while tests are failing

### 7. Documentation Standards

**Language**: American English
**Tone**: Friendly and informative
**Perspective**: Second-person ("you" and "your") for user-facing messages

**Formatting**:
- Use backticks for: file paths, filenames, variable names, field entries
- Use sentence case for all titles and messages
- Avoid abbreviations where possible

```python
# Good docstring
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the growspace manager from a config entry.
    
    This function initializes the coordinator, registers services,
    and sets up platforms for the integration.
    
    Args:
        hass: Home Assistant instance.
        entry: Config entry for this integration.
    
    Returns:
        True if setup was successful.
    
    Raises:
        ConfigEntryNotReady: If the connection cannot be established.
    """
```

## Development Workflow

### Phase 1: Planning

1. **Check Quality Scale Requirements**
   ```bash
   cat custom_components/growspace_manager/manifest.json | grep quality_scale
   cat custom_components/growspace_manager/quality_scale.yaml
   ```

2. **Research Documentation** (use Context7 tool)
   ```
   # Resolve Home Assistant library ID
   -resolve-library-id homeassistant
   
   # Get specific documentation
   -get-library-docs /websites/developers_home-assistant_io [topic]
   ```

3. **Create Implementation Plan**
   - Document proposed changes
   - Identify affected components
   - Plan verification strategy
   - Note any quality scale impacts

### Phase 2: Implementation

1. **Follow Code Standards**
   - Use Python 3.13+ features
   - Add comprehensive type hints
   - Ensure all I/O is async
   - Apply proper error handling

2. **Write Tests Alongside Code**
   ```python
   # Test structure
   async def test_feature_name(hass, config_entry):
       """Test that feature works correctly."""
       # Setup
       await async_setup_component(hass, DOMAIN, {})
       
       # Execute
       result = await target_function(hass, config_entry)
       
       # Assert
       assert result == expected
   ```

3. **Run Incremental Tests**
   ```bash
   # After each file
   ./venv/bin/pytest tests/test_<module>.py -v
   ```

### Phase 3: Verification

1. **Run Full Test Suite**
   ```bash
   ./venv/bin/pytest tests/ -v
   ```

2. **Check Coverage**
   ```bash
   ./venv/bin/pytest --cov=custom_components.growspace_manager \
     --cov-report=term-missing tests/
   ```

3. **Lint and Format** (handled by ruff)
   ```bash
   ruff check .
   ruff format .
   ```

4. **Verify Quality Scale Compliance**
   - Update `quality_scale.yaml`
   - Mark completed rules as `done`
   - Document any exemptions with reasons

### Phase 4: Documentation

1. **Update Docstrings**
   - All public functions
   - All classes
   - Complex logic sections

2. **Update README** (if applicable)
   - New features
   - Configuration changes
   - Breaking changes

3. **Create Walkthrough** (for significant features)
   - What was changed
   - What was tested
   - Validation results

## Common Patterns

### Coordinator Pattern

```python
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

class MyCoordinator(DataUpdateCoordinator[MyDataType]):
    """Coordinator for managing data updates."""
    
    def __init__(self, hass: HomeAssistant, client: MyClient) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
            always_update=False,  # Only update on data changes
        )
        self.client = client
    
    async def _async_update_data(self) -> MyDataType:
        """Fetch data from API."""
        try:
            return await self.client.fetch_data()
        except ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
```

### Config Flow

```python
class MyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                await self._test_connection(user_input[CONF_HOST])
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # OK in config flows
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_NAME): str,
            }),
            errors=errors,
        )
```

### Entity Platform

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform."""
    coordinator: MyCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        MySensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    
    async_add_entities(entities)


class MySensor(CoordinatorEntity[MyCoordinator], SensorEntity):
    """Representation of a sensor."""
    
    def __init__(
        self,
        coordinator: MyCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)
```

## Anti-Patterns to Avoid

❌ **Blocking I/O**
```python
import requests  # Never use synchronous requests
response = requests.get(url)  # ❌
```

❌ **Sleep in Loops**
```python
for item in items:
    await asyncio.sleep(1)  # ❌
    await process(item)
```

❌ **Eager String Formatting in Logs**
```python
_LOGGER.debug(f"Processing {item}.")  # ❌ (period + eager)
```

❌ **Missing Type Hints**
```python
async def fetch_data(item):  # ❌ Missing types
    return await client.get(item)
```

❌ **Broad Exception Catching (outside config flow/coordinator)**
```python
try:
    data = await fetch()
except Exception:  # ❌ Too broad
    pass
```

## External Documentation Access

Use the **Context7 MCP tool** for accessing Home Assistant documentation:

```bash
# 1. Resolve library ID
mcp_context7_resolve-library-id homeassistant

# 2. Query documentation
mcp_context7_query-docs /websites/developers_home-assistant_io "entity platforms"
mcp_context7_query-docs /websites/developers_home-assistant_io "config flow"
mcp_context7_query-docs /websites/developers_home-assistant_io "coordinator"
```

## Quick Reference

### File Structure
```
custom_components/growspace_manager/
├── __init__.py          # Integration setup
├── manifest.json        # Integration metadata
├── quality_scale.yaml   # Quality compliance tracking
├── config_flow.py       # Configuration UI
├── const.py             # Constants
├── coordinator.py       # Data update coordinator
├── sensor.py            # Sensor platform
├── binary_sensor.py     # Binary sensor platform
├── calendar.py          # Calendar platform
├── services/            # Service handlers
│   ├── plant.py
│   └── ...
├── models.py            # Data models
└── strings.json         # Translations
```

### Key Constants

```python
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)

DOMAIN = "growspace_manager"
```

### Helpful Imports

```python
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
```

## Success Criteria

Before marking any work complete:

- [ ] All tests pass (`./venv/bin/pytest tests/`)
- [ ] No linting errors (`ruff check .`)
- [ ] All functions have type hints
- [ ] No blocking I/O operations
- [ ] Proper error handling with specific exceptions
- [ ] Lazy logging used throughout
- [ ] No sensitive data in logs
- [ ] Docstrings for all public APIs
- [ ] Quality scale compliance verified
- [ ] Coverage maintained or improved

## Resources

- **Manifest**: `custom_components/growspace_manager/manifest.json`
- **Quality Scale**: `custom_components/growspace_manager/quality_scale.yaml`
- **Tests**: `tests/`
- **Virtual Environment**: `./venv/bin/pytest`

---

**Remember**: Quality and correctness over speed. Test-driven development is mandatory. Every I/O operation must be async. Type hints are not optional.
