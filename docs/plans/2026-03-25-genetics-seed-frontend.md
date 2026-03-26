# Genetics & seed inventory implementation plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add seed batch inventory, pollination logging, phenotype scoring, and seed harvest workflow — backend services plus frontend UI in the lovelace card.

**Architecture:** Backend adds `SeedBatch`/`PollinationEvent` models, a `GeneticsManager`, four new HA services, and one WebSocket endpoint. Frontend adds a `GeneticsAPI`, a Seeds tab in the strain library dialog, and a Genetics tab in the plant overview dialog.

**Tech Stack:** Python 3.13 (backend), Lit + TypeScript (frontend), Home Assistant service/WebSocket APIs.

**Working directory:** `/home/maxi/core/core/.worktrees/genetics-seed-frontend`

**Run tests with:**
```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

---

## Task 1: Add SeedBatch and PollinationEvent models

**Files:**
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/models.py`

**Step 1: Add models after the `ECRampCurve` class (line ~466)**

Find the `ECRampCurve` class and add immediately after it:

```python
@dataclass(slots=True)
class SeedBatch(BaseModel):
    """A batch of seeds tracked in the genetics inventory."""

    batch_id: str = ""
    strain_name: str = ""
    breeder: str = ""
    quantity: int = 0
    acquisition_date: str = ""  # ISO date YYYY-MM-DD
    generation: str = ""  # e.g. F1, S1, BX1
    lineage: str = ""
    notes: str = ""


@dataclass(slots=True)
class PollinationEvent(BaseModel):
    """Records a pollination between two plants."""

    event_id: str = ""
    date: str = ""  # ISO date YYYY-MM-DD
    donor_plant_id: str = ""
    receiver_plant_id: str = ""
    notes: str = ""
    result_seed_batch_id: str | None = None
```

**Step 2: Run tests to confirm nothing is broken**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

Expected: all existing tests pass.

**Step 3: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/models.py
git commit -m "feat(genetics): add SeedBatch and PollinationEvent models"
```

---

## Task 2: Add constants for genetics services and attributes

**Files:**
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/const.py`

**Step 1: Add service names to `GrowspaceService` enum**

Find the `GrowspaceService` (or `SERVICES`) StrEnum and add:

```python
ADD_SEED_BATCH = "add_seed_batch"
LOG_POLLINATION = "log_pollination"
HARVEST_SEEDS = "harvest_seeds"
```

**Step 2: Add attribute constants**

Find the existing attribute constants block and add:

```python
ATTR_ACQUISITION_DATE = "acquisition_date"
ATTR_GENERATION = "generation"
ATTR_DONOR_PLANT_ID = "donor_plant_id"
ATTR_RECEIVER_PLANT_ID = "receiver_plant_id"
ATTR_EVENT_ID = "event_id"
ATTR_BATCH_ID = "batch_id"
```

Note: `ATTR_VIGOR`, `ATTR_RESIN`, `ATTR_LINEAGE`, `ATTR_BREEDER` already exist — do not duplicate them.

**Step 3: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

**Step 4: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/const.py
git commit -m "feat(genetics): add service names and attribute constants"
```

---

## Task 3: Add service schemas

**Files:**
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/schemas.py`

**Step 1: Import new constants at top of schemas.py**

Find the existing imports block. Add `ATTR_ACQUISITION_DATE`, `ATTR_GENERATION`, `ATTR_DONOR_PLANT_ID`, `ATTR_RECEIVER_PLANT_ID`, `ATTR_EVENT_ID`, `ATTR_BATCH_ID` to the const import line.

**Step 2: Add schemas at the bottom of schemas.py**

```python
ADD_SEED_BATCH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_STRAIN_NAME): cv.string,
        vol.Required(ATTR_BREEDER): cv.string,
        vol.Required(ATTR_QUANTITY): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_ACQUISITION_DATE): cv.string,
        vol.Required(ATTR_GENERATION): cv.string,
        vol.Required(ATTR_LINEAGE): cv.string,
        vol.Optional(ATTR_NOTES, default=""): cv.string,
    }
)

LOG_POLLINATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DATE): cv.string,
        vol.Required(ATTR_DONOR_PLANT_ID): cv.string,
        vol.Required(ATTR_RECEIVER_PLANT_ID): cv.string,
        vol.Optional(ATTR_NOTES, default=""): cv.string,
    }
)

HARVEST_SEEDS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_EVENT_ID): cv.string,
        vol.Required(ATTR_QUANTITY): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional(ATTR_NOTES, default=""): cv.string,
    }
)
```

Note: `ATTR_STRAIN_NAME` and `ATTR_DATE` should already exist; check and import if missing.

**Step 3: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

**Step 4: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/schemas.py
git commit -m "feat(genetics): add service validation schemas"
```

---

## Task 4: Create GeneticsManager

**Files:**
- Create: `vendor/growspace_manager/custom_components/growspace_manager/managers/genetics.py`

**Step 1: Create the file**

```python
"""Manages seed batch inventory and pollination event tracking."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import date
from typing import TYPE_CHECKING, Any

from ..models import PollinationEvent, SeedBatch

if TYPE_CHECKING:
    from ..data_access.growspace_repository import GrowspaceRepository


class GeneticsManager:
    """Manages seed batches and pollination events."""

    def __init__(
        self,
        repository: GrowspaceRepository,
        save_callback: Callable[[], Awaitable[None]],
    ) -> None:
        """Initialize the GeneticsManager."""
        self.repository = repository
        self.save_callback = save_callback
        self.seed_batches: dict[str, SeedBatch] = {}
        self.pollination_events: dict[str, PollinationEvent] = {}

    def load_data(
        self,
        seed_batches: dict[str, SeedBatch],
        pollination_events: dict[str, PollinationEvent],
    ) -> None:
        """Load data into the manager."""
        self.seed_batches = seed_batches
        self.pollination_events = pollination_events

    async def async_add_seed_batch(
        self,
        strain_name: str,
        breeder: str,
        quantity: int,
        acquisition_date: str,
        generation: str,
        lineage: str,
        notes: str = "",
    ) -> SeedBatch:
        """Add a new seed batch to the inventory."""
        batch_id = str(uuid.uuid4())
        batch = SeedBatch(
            batch_id=batch_id,
            strain_name=strain_name,
            breeder=breeder,
            quantity=quantity,
            acquisition_date=acquisition_date,
            generation=generation,
            lineage=lineage,
            notes=notes,
        )
        self.seed_batches[batch_id] = batch
        await self.save_callback()
        return batch

    async def async_log_pollination(
        self,
        event_date: str,
        donor_plant_id: str,
        receiver_plant_id: str,
        notes: str = "",
    ) -> PollinationEvent:
        """Log a pollination event between two plants."""
        event_id = str(uuid.uuid4())
        event = PollinationEvent(
            event_id=event_id,
            date=event_date,
            donor_plant_id=donor_plant_id,
            receiver_plant_id=receiver_plant_id,
            notes=notes,
        )
        self.pollination_events[event_id] = event
        await self.save_callback()
        return event

    async def async_harvest_seeds(
        self,
        event_id: str,
        quantity: int,
        notes: str = "",
    ) -> SeedBatch:
        """Convert a pollination event into a new seed batch."""
        event = self.pollination_events.get(event_id)
        if event is None:
            msg = f"Pollination event {event_id} not found"
            raise ValueError(msg)
        if event.result_seed_batch_id is not None:
            msg = f"Event {event_id} already has a seed batch"
            raise ValueError(msg)

        donor = self.repository.plants.get(event.donor_plant_id)
        receiver = self.repository.plants.get(event.receiver_plant_id)
        donor_name = donor.genetics.strain_name if donor else event.donor_plant_id
        receiver_name = (
            receiver.genetics.strain_name if receiver else event.receiver_plant_id
        )

        batch_id = str(uuid.uuid4())
        batch = SeedBatch(
            batch_id=batch_id,
            strain_name=f"{receiver_name} x {donor_name}",
            breeder="Self",
            quantity=quantity,
            acquisition_date=date.today().isoformat(),
            generation="F1",
            lineage=f"{receiver_name} x {donor_name}",
            notes=notes,
        )
        self.seed_batches[batch_id] = batch
        event.result_seed_batch_id = batch_id
        await self.save_callback()
        return batch

    def get_serialization_data(self) -> dict[str, Any]:
        """Return data for serialization."""
        return {
            "seed_batches": {
                bid: asdict(b) for bid, b in self.seed_batches.items()
            },
            "pollination_events": {
                eid: asdict(e) for eid, e in self.pollination_events.items()
            },
        }
```

**Step 2: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

**Step 3: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/managers/genetics.py
git commit -m "feat(genetics): add GeneticsManager"
```

---

## Task 5: Create genetics service handlers

**Files:**
- Create: `vendor/growspace_manager/custom_components/growspace_manager/services/genetics.py`

**Step 1: Create the file**

```python
"""Service handlers for genetics and seed inventory operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError

from ..const import (
    ATTR_ACQUISITION_DATE,
    ATTR_BREEDER,
    ATTR_DATE,
    ATTR_DONOR_PLANT_ID,
    ATTR_EVENT_ID,
    ATTR_GENERATION,
    ATTR_LINEAGE,
    ATTR_NOTES,
    ATTR_QUANTITY,
    ATTR_RECEIVER_PLANT_ID,
    ATTR_STRAIN_NAME,
)
from .utils import handle_service_errors

if TYPE_CHECKING:
    from ..coordinator import GrowspaceCoordinator
    from ..strain_library import StrainLibrary


@handle_service_errors
async def handle_add_seed_batch(
    hass: HomeAssistant,
    coordinator: GrowspaceCoordinator,
    strain_library: StrainLibrary,
    call: ServiceCall,
) -> None:
    """Handle the add_seed_batch service call."""
    await coordinator.genetics_manager.async_add_seed_batch(
        strain_name=call.data[ATTR_STRAIN_NAME],
        breeder=call.data[ATTR_BREEDER],
        quantity=call.data[ATTR_QUANTITY],
        acquisition_date=call.data[ATTR_ACQUISITION_DATE],
        generation=call.data[ATTR_GENERATION],
        lineage=call.data[ATTR_LINEAGE],
        notes=call.data.get(ATTR_NOTES, ""),
    )


@handle_service_errors
async def handle_log_pollination(
    hass: HomeAssistant,
    coordinator: GrowspaceCoordinator,
    strain_library: StrainLibrary,
    call: ServiceCall,
) -> None:
    """Handle the log_pollination service call."""
    await coordinator.genetics_manager.async_log_pollination(
        event_date=call.data[ATTR_DATE],
        donor_plant_id=call.data[ATTR_DONOR_PLANT_ID],
        receiver_plant_id=call.data[ATTR_RECEIVER_PLANT_ID],
        notes=call.data.get(ATTR_NOTES, ""),
    )


@handle_service_errors
async def handle_harvest_seeds(
    hass: HomeAssistant,
    coordinator: GrowspaceCoordinator,
    strain_library: StrainLibrary,
    call: ServiceCall,
) -> None:
    """Handle the harvest_seeds service call."""
    try:
        await coordinator.genetics_manager.async_harvest_seeds(
            event_id=call.data[ATTR_EVENT_ID],
            quantity=call.data[ATTR_QUANTITY],
            notes=call.data.get(ATTR_NOTES, ""),
        )
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
```

**Step 2: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

**Step 3: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/services/genetics.py
git commit -m "feat(genetics): add genetics service handlers"
```

---

## Task 6: Register genetics services

**Files:**
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/service_registration.py`
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/services/__init__.py`

**Step 1: Import new schemas and service handlers in service_registration.py**

Add to imports:
```python
from .schemas import (
    # ... existing imports ...
    ADD_SEED_BATCH_SCHEMA,
    HARVEST_SEEDS_SCHEMA,
    LOG_POLLINATION_SCHEMA,
)
from .services import genetics
```

**Step 2: Register the three new services**

Find the services registration block and add:
```python
GrowspaceService.ADD_SEED_BATCH,
wrap(genetics.handle_add_seed_batch, False),
ADD_SEED_BATCH_SCHEMA,

GrowspaceService.LOG_POLLINATION,
wrap(genetics.handle_log_pollination, False),
LOG_POLLINATION_SCHEMA,

GrowspaceService.HARVEST_SEEDS,
wrap(genetics.handle_harvest_seeds, False),
HARVEST_SEEDS_SCHEMA,
```

**Step 3: Update test_core_init.py expected_services**

In `tests/core/test_core_init.py`, add to `expected_services`:
```python
"add_seed_batch": ADD_SEED_BATCH_SCHEMA,
"log_pollination": LOG_POLLINATION_SCHEMA,
"harvest_seeds": HARVEST_SEEDS_SCHEMA,
```

And import those schemas at the top of the test file.

**Step 4: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/core/test_core_init.py -q --tb=short
```

**Step 5: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/service_registration.py \
        vendor/growspace_manager/custom_components/growspace_manager/services/__init__.py \
        vendor/growspace_manager/tests/core/test_core_init.py
git commit -m "feat(genetics): register genetics services"
```

---

## Task 7: Wire GeneticsManager into coordinator and storage

**Files:**
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/coordinator.py`
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/storage_manager.py`

**Step 1: Add GeneticsManager to coordinator.py**

Import:
```python
from .managers.genetics import GeneticsManager
```

In `__init__` or initialization block (alongside where `NutrientManager` is initialized):
```python
self.genetics_manager = GeneticsManager(
    self.data_repository,
    self._async_save,
)
```

Pass `genetics_manager` to `StorageManager` constructor:
```python
self.storage_manager = StorageManager(
    self.hass, self.data_repository, self.nutrient_manager, self.genetics_manager
)
```

After loading storage, call:
```python
self.genetics_manager.load_data(
    self.genetics_manager.seed_batches,
    self.genetics_manager.pollination_events,
)
```

(Storage manager will populate these — see step 2.)

**Step 2: Update storage_manager.py**

Import:
```python
from .managers.genetics import GeneticsManager
from .models import PollinationEvent, SeedBatch
```

Add `genetics_manager` parameter to `__init__`:
```python
def __init__(
    self,
    hass: HomeAssistant,
    repository: GrowspaceRepository,
    nutrient_manager: NutrientManager,
    genetics_manager: GeneticsManager,
) -> None:
    ...
    self.genetics_manager = genetics_manager
```

In `_get_config_data()`, merge genetics data:
```python
genetics_data = self.genetics_manager.get_serialization_data()
config.update(genetics_data)
```

In `_load_config()`, load genetics data:
```python
seed_batches = {
    bid: SeedBatch.from_dict(b)
    for bid, b in data.get("seed_batches", {}).items()
}
pollination_events = {
    eid: PollinationEvent.from_dict(e)
    for eid, e in data.get("pollination_events", {}).items()
}
self.genetics_manager.load_data(seed_batches, pollination_events)
```

**Step 3: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

**Step 4: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/coordinator.py \
        vendor/growspace_manager/custom_components/growspace_manager/storage_manager.py
git commit -m "feat(genetics): wire GeneticsManager into coordinator and storage"
```

---

## Task 8: Add get_genetics_data WebSocket handler

**Files:**
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/websocket.py`

**Step 1: Add constants near the other WS_TYPE constants**

```python
WS_TYPE_GET_GENETICS_DATA = f"{DOMAIN}/get_genetics_data"
SCHEMA_WS_GET_GENETICS_DATA = websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend(
    {
        vol.Required("type"): WS_TYPE_GET_GENETICS_DATA,
    }
)
```

**Step 2: Add handler function (use the sync pattern like `websocket_get_strain_library`)**

```python
@callback
def websocket_get_genetics_data(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle get genetics data command via WebSocket."""
    try:
        if DOMAIN not in hass.data or "coordinator" not in hass.data[DOMAIN]:
            connection.send_error(
                msg["id"], "not_loaded", "Growspace Manager not loaded"
            )
            return

        coordinator = hass.data[DOMAIN]["coordinator"]
        connection.send_result(
            msg["id"],
            coordinator.genetics_manager.get_serialization_data(),
        )
    except Exception as err:
        _LOGGER.exception("Error handling websocket_get_genetics_data")
        connection.send_error(msg["id"], "unknown_error", str(err))
```

**Step 3: Register in `async_register_websocket_api`**

Add at the end of the registration function:
```python
websocket_api.async_register_command(
    hass,
    WS_TYPE_GET_GENETICS_DATA,
    websocket_get_genetics_data,
    SCHEMA_WS_GET_GENETICS_DATA,
)
```

**Step 4: Check how coordinator is stored in hass.data**

Run:
```bash
grep -n "hass.data\[DOMAIN\]" vendor/growspace_manager/custom_components/growspace_manager/__init__.py | head -10
```

Use the same key the coordinator is stored under. If it's different from `"coordinator"`, update the handler accordingly.

**Step 5: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

**Step 6: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/websocket.py
git commit -m "feat(genetics): add get_genetics_data WebSocket handler"
```

---

## Task 9: Add genetics services to services.yaml

**Files:**
- Modify: `vendor/growspace_manager/custom_components/growspace_manager/services.yaml`

**Step 1: Add service definitions at the end of services.yaml**

```yaml
add_seed_batch:
  name: Add seed batch
  description: Add a batch of seeds to the genetics inventory.
  fields:
    strain_name:
      name: Strain name
      description: Name of the strain.
      required: true
      example: "Blue Dream"
      selector:
        text:
    breeder:
      name: Breeder
      description: Breeder or source of the seeds.
      required: true
      example: "Humboldt Seed Co"
      selector:
        text:
    quantity:
      name: Quantity
      description: Number of seeds in the batch.
      required: true
      example: 10
      selector:
        number:
          min: 1
    acquisition_date:
      name: Acquisition date
      description: Date the seeds were acquired (YYYY-MM-DD).
      required: true
      example: "2026-01-15"
      selector:
        text:
    generation:
      name: Generation
      description: Seed generation (e.g. F1, S1, BX1).
      required: true
      example: "F1"
      selector:
        text:
    lineage:
      name: Lineage
      description: Parent strains (e.g. OG Kush x Blueberry).
      required: true
      example: "OG Kush x Blueberry"
      selector:
        text:
    notes:
      name: Notes
      description: Optional notes about this batch.
      required: false
      example: "Purchased at local dispensary"
      selector:
        text:

log_pollination:
  name: Log pollination
  description: Record a pollination event between two plants.
  fields:
    date:
      name: Date
      description: Date of pollination (YYYY-MM-DD).
      required: true
      example: "2026-03-10"
      selector:
        text:
    donor_plant_id:
      name: Donor plant ID
      description: Entity ID of the pollen donor (male or reversed female).
      required: true
      example: "sensor.growspace_plant_abc123"
      selector:
        entity:
          domain: sensor
    receiver_plant_id:
      name: Receiver plant ID
      description: Entity ID of the female plant being pollinated.
      required: true
      example: "sensor.growspace_plant_def456"
      selector:
        entity:
          domain: sensor
    notes:
      name: Notes
      description: Optional notes.
      required: false
      selector:
        text:

harvest_seeds:
  name: Harvest seeds
  description: Convert a logged pollination event into a new seed batch.
  fields:
    event_id:
      name: Event ID
      description: ID of the pollination event to harvest.
      required: true
      example: "550e8400-e29b-41d4-a716-446655440000"
      selector:
        text:
    quantity:
      name: Quantity
      description: Number of seeds harvested.
      required: true
      example: 25
      selector:
        number:
          min: 1
    notes:
      name: Notes
      description: Optional notes about the harvest.
      required: false
      selector:
        text:
```

**Step 2: Run tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

**Step 3: Commit**

```bash
git add vendor/growspace_manager/custom_components/growspace_manager/services.yaml
git commit -m "feat(genetics): add genetics service definitions to services.yaml"
```

---

## Task 10: Frontend — add genetics types

**Files:**
- Modify: `vendor/lovelace-growspace-manager-card/src/types.ts`

**Step 1: Add types at the bottom of types.ts**

```typescript
export interface SeedBatch {
  batch_id: string;
  strain_name: string;
  breeder: string;
  quantity: number;
  acquisition_date: string;
  generation: string;
  lineage: string;
  notes: string;
}

export interface PollinationEvent {
  event_id: string;
  date: string;
  donor_plant_id: string;
  receiver_plant_id: string;
  notes: string;
  result_seed_batch_id: string | null;
}

export interface PhenotypeScores {
  vigor: number | null;
  structure: number | null;
  aroma: number | null;
  resin: number | null;
  pest_resistance: number | null;
}
```

Note: `PhenotypeScores` mirrors the existing backend `PlantScores` model fields.

**Step 2: Commit**

```bash
git add vendor/lovelace-growspace-manager-card/src/types.ts
git commit -m "feat(genetics): add frontend genetics types"
```

---

## Task 11: Frontend — create GeneticsAPI

**Files:**
- Create: `vendor/lovelace-growspace-manager-card/src/services/api/genetics-api.ts`

**Step 1: Create the file**

```typescript
import type { HomeAssistant } from 'custom-card-helpers';
import type { PollinationEvent, SeedBatch } from '../../types';
import { BaseAPI } from './base-api';

const DOMAIN = 'growspace_manager';

export interface GeneticsData {
  seed_batches: Record<string, SeedBatch>;
  pollination_events: Record<string, PollinationEvent>;
}

export class GeneticsAPI extends BaseAPI {
  constructor(hass: HomeAssistant) {
    super(hass);
  }

  async fetchGeneticsData(): Promise<GeneticsData> {
    const result = await this.sendWebSocket<GeneticsData>(
      `${DOMAIN}/get_genetics_data`
    );
    return result ?? { seed_batches: {}, pollination_events: {} };
  }

  async addSeedBatch(data: {
    strain_name: string;
    breeder: string;
    quantity: number;
    acquisition_date: string;
    generation: string;
    lineage: string;
    notes?: string;
  }): Promise<void> {
    await this.callService(DOMAIN, 'add_seed_batch', data);
  }

  async logPollination(data: {
    date: string;
    donor_plant_id: string;
    receiver_plant_id: string;
    notes?: string;
  }): Promise<void> {
    await this.callService(DOMAIN, 'log_pollination', data);
  }

  async harvestSeeds(data: {
    event_id: string;
    quantity: number;
    notes?: string;
  }): Promise<void> {
    await this.callService(DOMAIN, 'harvest_seeds', data);
  }

  async scorePlant(data: {
    plant_id: string;
    vigor?: number | null;
    structure?: number | null;
    aroma?: number | null;
    resin?: number | null;
    pest_resistance?: number | null;
  }): Promise<void> {
    // Remove null values before sending
    const payload = Object.fromEntries(
      Object.entries(data).filter(([, v]) => v != null)
    );
    await this.callService(DOMAIN, 'score_plant', payload);
  }
}
```

**Step 2: Check the BaseAPI import path**

Run:
```bash
head -5 vendor/lovelace-growspace-manager-card/src/services/api/strain-api.ts
```

Match the same import for `BaseAPI`.

**Step 3: Commit**

```bash
git add vendor/lovelace-growspace-manager-card/src/services/api/genetics-api.ts
git commit -m "feat(genetics): add GeneticsAPI"
```

---

## Task 12: Register GeneticsAPI on DataService

**Files:**
- Modify: `vendor/lovelace-growspace-manager-card/src/services/data-service.ts`

**Step 1: Import GeneticsAPI**

```typescript
import { GeneticsAPI } from './api/genetics-api';
```

**Step 2: Add private field**

```typescript
private _geneticsAPI: GeneticsAPI;
```

**Step 3: Initialize in constructor**

```typescript
this._geneticsAPI = new GeneticsAPI(hass);
```

**Step 4: Include in updateHass array**

```typescript
this._geneticsAPI,
```

**Step 5: Add public getter and delegations**

```typescript
get geneticsAPI(): GeneticsAPI {
  return this._geneticsAPI;
}

fetchGeneticsData = () => this._geneticsAPI.fetchGeneticsData();
addSeedBatch = (data: Parameters<GeneticsAPI['addSeedBatch']>[0]) =>
  this._geneticsAPI.addSeedBatch(data);
logPollination = (data: Parameters<GeneticsAPI['logPollination']>[0]) =>
  this._geneticsAPI.logPollination(data);
harvestSeeds = (data: Parameters<GeneticsAPI['harvestSeeds']>[0]) =>
  this._geneticsAPI.harvestSeeds(data);
```

**Step 6: Build to check for type errors**

```bash
cd vendor/lovelace-growspace-manager-card && npm run build 2>&1 | grep -E "error|Error" | head -20
```

Fix any import/type errors.

**Step 7: Commit**

```bash
git add vendor/lovelace-growspace-manager-card/src/services/data-service.ts
git commit -m "feat(genetics): register GeneticsAPI on DataService"
```

---

## Task 13: Update StrainLibraryDialogState and ui-actions

**Files:**
- Modify: `vendor/lovelace-growspace-manager-card/src/lib/types/dialog.ts`
- Modify: `vendor/lovelace-growspace-manager-card/src/store/ui/ui-actions.ts`

**Step 1: Add initialTab to StrainLibraryDialogState in dialog.ts**

Find `StrainLibraryDialogState` and add:
```typescript
export interface StrainLibraryDialogState {
  editingStrain?: StrainEntry;
  source?: 'add-plant' | 'add-plants' | 'plant-overview';
  returnPayload?: unknown;
  initialTab?: 'strains' | 'seeds';  // add this line
}
```

**Step 2: Update openStrainLibraryDialog in ui-actions.ts**

Find:
```typescript
export function openStrainLibraryDialog(ctx: ActionContext) {
  ctx.ui.setActiveDialog({ type: 'STRAIN_LIBRARY', payload: {} });
}
```

Replace with:
```typescript
export function openStrainLibraryDialog(
  ctx: ActionContext,
  initialTab?: 'strains' | 'seeds'
) {
  ctx.ui.setActiveDialog({
    type: 'STRAIN_LIBRARY',
    payload: { initialTab },
  });
}
```

**Step 3: Build check**

```bash
cd vendor/lovelace-growspace-manager-card && npm run build 2>&1 | grep -E "error|Error" | head -20
```

**Step 4: Commit**

```bash
git add vendor/lovelace-growspace-manager-card/src/lib/types/dialog.ts \
        vendor/lovelace-growspace-manager-card/src/store/ui/ui-actions.ts
git commit -m "feat(genetics): add initialTab to strain library dialog state"
```

---

## Task 14: Update dialog-host to pass genetics data

**Files:**
- Modify: `vendor/lovelace-growspace-manager-card/src/components/manager/dialog-host.ts`

**Step 1: Import types**

Add to imports:
```typescript
import type { SeedBatch, PollinationEvent } from '../../types';
```

**Step 2: Add state properties**

```typescript
@state() private _seedBatches: Record<string, SeedBatch> = {};
@state() private _pollinationEvents: Record<string, PollinationEvent> = {};
```

**Step 3: Fetch genetics data when strain library dialog opens**

In `_renderStrainLibraryDialog`, before rendering, check if data needs loading. The simplest approach: fetch genetics data in `connectedCallback` or lazily when the tab is active. For simplicity, fetch once on first open.

Add a `_geneticsLoaded` flag:
```typescript
private _geneticsLoaded = false;
```

In `_renderStrainLibraryDialog`:
```typescript
if (!this._geneticsLoaded) {
  this._geneticsLoaded = true;
  this.store.dataService.fetchGeneticsData().then((data) => {
    if (data) {
      this._seedBatches = data.seed_batches;
      this._pollinationEvents = data.pollination_events;
    }
  });
}
```

**Step 4: Pass data and initialTab to the dialog element**

In `_renderStrainLibraryDialog`, add props:
```typescript
.seedBatches=${Object.values(this._seedBatches)}
.pollinationEvents=${Object.values(this._pollinationEvents)}
.initialTab=${(active.payload as StrainLibraryDialogState).initialTab ?? 'strains'}
.onSeedDataChanged=${() => {
  // Refresh genetics data after mutations
  this.store.dataService.fetchGeneticsData().then((data) => {
    if (data) {
      this._seedBatches = data.seed_batches;
      this._pollinationEvents = data.pollination_events;
    }
  });
}}
```

**Step 5: Build check**

```bash
cd vendor/lovelace-growspace-manager-card && npm run build 2>&1 | grep -E "error|Error" | head -20
```

**Step 6: Commit**

```bash
git add vendor/lovelace-growspace-manager-card/src/components/manager/dialog-host.ts
git commit -m "feat(genetics): pass genetics data from dialog-host to strain library"
```

---

## Task 15: Add Seeds tab to strain-library-dialog

**Files:**
- Modify: `vendor/lovelace-growspace-manager-card/src/dialogs/strain-library-dialog.ts`

This is the largest UI task. The dialog currently uses `_view: 'browse' | 'editor'`. We add a top-level tab bar with `_activeMainTab: 'strains' | 'seeds'`.

**Step 1: Add new state properties and inputs**

```typescript
@property({ type: Array }) seedBatches: SeedBatch[] = [];
@property({ type: Array }) pollinationEvents: PollinationEvent[] = [];
@property({ type: String }) initialTab: 'strains' | 'seeds' = 'strains';
@property({ type: Function }) onSeedDataChanged?: () => void;

@state() private _activeMainTab: 'strains' | 'seeds' = 'strains';
@state() private _seedSubView: 'list' | 'add-batch' | 'log-pollination' | 'harvest' = 'list';
@state() private _selectedEventId: string | null = null;

// Add-batch form state
@state() private _batchForm = {
  strain_name: '', breeder: '', quantity: 1,
  acquisition_date: '', generation: 'F1', lineage: '', notes: ''
};

// Log-pollination form state
@state() private _pollinationForm = {
  date: '', donor_plant_id: '', receiver_plant_id: '', notes: ''
};

// Harvest form state
@state() private _harvestForm = { quantity: 1, notes: '' };
```

**Step 2: In `updated()` lifecycle, sync initialTab**

```typescript
updated(changedProperties: Map<string, unknown>) {
  super.updated?.(changedProperties);
  if (changedProperties.has('initialTab')) {
    this._activeMainTab = this.initialTab;
  }
}
```

**Step 3: Update render() to add tab bar above existing content**

At the top of `render()`, add a tab bar:
```typescript
render() {
  return html`
    <ha-dialog open .heading=${'Strain Library'} @closed=${this._handleClose}>
      <div slot="heading">
        <div class="tab-bar">
          <button
            class="tab-btn ${this._activeMainTab === 'strains' ? 'active' : ''}"
            @click=${() => { this._activeMainTab = 'strains'; }}
          >Strains</button>
          <button
            class="tab-btn ${this._activeMainTab === 'seeds' ? 'active' : ''}"
            @click=${() => { this._activeMainTab = 'seeds'; }}
          >Seeds & Genetics</button>
        </div>
      </div>

      ${this._activeMainTab === 'strains'
        ? html`
            ${this._view === 'browse' ? this.renderBrowseView() : this.renderEditorView()}
            ${this._isCropping ? this.renderCropOverlay() : nothing}
            ${this._isImageSelectorOpen ? this.renderImageSelector() : nothing}
            ${this._importDialogOpen ? this.renderImportDialog() : nothing}
            ${this._pendingDeleteKey ? this.renderDeleteConfirmation() : nothing}
            ${this._breederDialogOpen ? this.renderBreederDialog() : nothing}
            ${this._pendingDeleteBreeder ? this.renderBreederDeleteConfirmation() : nothing}
          `
        : this._renderSeedsTab()
      }
    </ha-dialog>
  `;
}
```

Note: Study the existing `render()` method carefully and wrap the existing content — do not duplicate or remove the overlays.

**Step 4: Implement `_renderSeedsTab()`**

```typescript
private _renderSeedsTab() {
  if (this._seedSubView === 'add-batch') return this._renderAddBatchForm();
  if (this._seedSubView === 'log-pollination') return this._renderLogPollinationForm();
  if (this._seedSubView === 'harvest') return this._renderHarvestForm();
  return this._renderSeedList();
}

private _renderSeedList() {
  return html`
    <div class="seeds-header">
      <h3>Seed inventory (${this.seedBatches.length} batches)</h3>
      <button class="md3-button filled" @click=${() => this._seedSubView = 'add-batch'}>
        Add batch
      </button>
    </div>

    ${this.seedBatches.length === 0
      ? html`<p class="empty-state">No seed batches yet.</p>`
      : this.seedBatches.map(b => html`
          <div class="seed-batch-card">
            <div class="seed-batch-name">${b.strain_name}</div>
            <div class="seed-batch-meta">
              ${b.breeder} · ${b.generation} · ${b.quantity} seeds
            </div>
            <div class="seed-batch-date">${b.acquisition_date}</div>
            ${b.lineage ? html`<div class="seed-batch-lineage">${b.lineage}</div>` : nothing}
          </div>
        `)
    }

    <h3>Pollination log (${this.pollinationEvents.length} events)</h3>
    <button class="md3-button tonal" @click=${() => this._seedSubView = 'log-pollination'}>
      Log pollination
    </button>

    ${this.pollinationEvents.map(e => html`
      <div class="pollination-card">
        <div class="pollination-date">${e.date}</div>
        <div class="pollination-plants">
          Donor: ${e.donor_plant_id} × Receiver: ${e.receiver_plant_id}
        </div>
        ${e.notes ? html`<div class="pollination-notes">${e.notes}</div>` : nothing}
        ${e.result_seed_batch_id
          ? html`<span class="badge">Seeds harvested</span>`
          : html`
              <button class="md3-button tonal" @click=${() => {
                this._selectedEventId = e.event_id;
                this._seedSubView = 'harvest';
              }}>
                Harvest seeds
              </button>
            `
        }
      </div>
    `)}
  `;
}
```

**Step 5: Implement form views**

```typescript
private _renderAddBatchForm() {
  return html`
    <div class="form-header">
      <button @click=${() => this._seedSubView = 'list'}>← Back</button>
      <h3>Add seed batch</h3>
    </div>
    <div class="form-body">
      <label>Strain name
        <input type="text" .value=${this._batchForm.strain_name}
          @input=${(e: Event) => this._batchForm = { ...this._batchForm, strain_name: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Breeder
        <input type="text" .value=${this._batchForm.breeder}
          @input=${(e: Event) => this._batchForm = { ...this._batchForm, breeder: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Quantity
        <input type="number" min="1" .value=${String(this._batchForm.quantity)}
          @input=${(e: Event) => this._batchForm = { ...this._batchForm, quantity: parseInt((e.target as HTMLInputElement).value) || 1 }} />
      </label>
      <label>Acquisition date
        <input type="date" .value=${this._batchForm.acquisition_date}
          @input=${(e: Event) => this._batchForm = { ...this._batchForm, acquisition_date: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Generation
        <input type="text" placeholder="F1, S1, BX1…" .value=${this._batchForm.generation}
          @input=${(e: Event) => this._batchForm = { ...this._batchForm, generation: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Lineage
        <input type="text" placeholder="Strain A x Strain B" .value=${this._batchForm.lineage}
          @input=${(e: Event) => this._batchForm = { ...this._batchForm, lineage: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Notes
        <input type="text" .value=${this._batchForm.notes}
          @input=${(e: Event) => this._batchForm = { ...this._batchForm, notes: (e.target as HTMLInputElement).value }} />
      </label>
    </div>
    <div class="form-actions">
      <button class="md3-button tonal" @click=${() => this._seedSubView = 'list'}>Cancel</button>
      <button class="md3-button filled" @click=${this._submitAddBatch}>Save</button>
    </div>
  `;
}

private _renderLogPollinationForm() {
  return html`
    <div class="form-header">
      <button @click=${() => this._seedSubView = 'list'}>← Back</button>
      <h3>Log pollination</h3>
    </div>
    <div class="form-body">
      <label>Date
        <input type="date" .value=${this._pollinationForm.date}
          @input=${(e: Event) => this._pollinationForm = { ...this._pollinationForm, date: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Donor plant ID
        <input type="text" placeholder="sensor.growspace_plant_…"
          .value=${this._pollinationForm.donor_plant_id}
          @input=${(e: Event) => this._pollinationForm = { ...this._pollinationForm, donor_plant_id: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Receiver plant ID
        <input type="text" placeholder="sensor.growspace_plant_…"
          .value=${this._pollinationForm.receiver_plant_id}
          @input=${(e: Event) => this._pollinationForm = { ...this._pollinationForm, receiver_plant_id: (e.target as HTMLInputElement).value }} />
      </label>
      <label>Notes
        <input type="text" .value=${this._pollinationForm.notes}
          @input=${(e: Event) => this._pollinationForm = { ...this._pollinationForm, notes: (e.target as HTMLInputElement).value }} />
      </label>
    </div>
    <div class="form-actions">
      <button class="md3-button tonal" @click=${() => this._seedSubView = 'list'}>Cancel</button>
      <button class="md3-button filled" @click=${this._submitLogPollination}>Save</button>
    </div>
  `;
}

private _renderHarvestForm() {
  return html`
    <div class="form-header">
      <button @click=${() => { this._seedSubView = 'list'; this._selectedEventId = null; }}>← Back</button>
      <h3>Harvest seeds</h3>
    </div>
    <div class="form-body">
      <label>Quantity harvested
        <input type="number" min="1" .value=${String(this._harvestForm.quantity)}
          @input=${(e: Event) => this._harvestForm = { ...this._harvestForm, quantity: parseInt((e.target as HTMLInputElement).value) || 1 }} />
      </label>
      <label>Notes
        <input type="text" .value=${this._harvestForm.notes}
          @input=${(e: Event) => this._harvestForm = { ...this._harvestForm, notes: (e.target as HTMLInputElement).value }} />
      </label>
    </div>
    <div class="form-actions">
      <button class="md3-button tonal" @click=${() => { this._seedSubView = 'list'; this._selectedEventId = null; }}>Cancel</button>
      <button class="md3-button filled" @click=${this._submitHarvestSeeds}>Save</button>
    </div>
  `;
}
```

**Step 6: Implement submit handlers**

```typescript
private async _submitAddBatch() {
  const f = this._batchForm;
  if (!f.strain_name || !f.breeder || !f.acquisition_date || !f.generation || !f.lineage) return;
  try {
    await this._hass.callService('growspace_manager', 'add_seed_batch', {
      strain_name: f.strain_name, breeder: f.breeder, quantity: f.quantity,
      acquisition_date: f.acquisition_date, generation: f.generation,
      lineage: f.lineage, notes: f.notes,
    });
    this._seedSubView = 'list';
    this._batchForm = { strain_name: '', breeder: '', quantity: 1, acquisition_date: '', generation: 'F1', lineage: '', notes: '' };
    this.onSeedDataChanged?.();
  } catch (e) {
    console.error('Failed to add seed batch', e);
  }
}

private async _submitLogPollination() {
  const f = this._pollinationForm;
  if (!f.date || !f.donor_plant_id || !f.receiver_plant_id) return;
  try {
    await this._hass.callService('growspace_manager', 'log_pollination', {
      date: f.date, donor_plant_id: f.donor_plant_id,
      receiver_plant_id: f.receiver_plant_id, notes: f.notes,
    });
    this._seedSubView = 'list';
    this._pollinationForm = { date: '', donor_plant_id: '', receiver_plant_id: '', notes: '' };
    this.onSeedDataChanged?.();
  } catch (e) {
    console.error('Failed to log pollination', e);
  }
}

private async _submitHarvestSeeds() {
  if (!this._selectedEventId) return;
  try {
    await this._hass.callService('growspace_manager', 'harvest_seeds', {
      event_id: this._selectedEventId, quantity: this._harvestForm.quantity,
      notes: this._harvestForm.notes,
    });
    this._seedSubView = 'list';
    this._selectedEventId = null;
    this._harvestForm = { quantity: 1, notes: '' };
    this.onSeedDataChanged?.();
  } catch (e) {
    console.error('Failed to harvest seeds', e);
  }
}
```

Note: Check how `_hass` is accessed in this dialog (may be `this.hass` — look at existing service calls in the file).

**Step 7: Build check**

```bash
cd vendor/lovelace-growspace-manager-card && npm run build 2>&1 | grep -E "error|Error" | head -20
```

Fix any type errors.

**Step 8: Commit**

```bash
git add vendor/lovelace-growspace-manager-card/src/dialogs/strain-library-dialog.ts
git commit -m "feat(genetics): add Seeds & Genetics tab to strain library dialog"
```

---

## Task 16: Add Genetics tab to plant-overview-dialog

**Files:**
- Modify: `vendor/lovelace-growspace-manager-card/src/dialogs/plant-overview-dialog.ts`

The dialog type already references `activeTab: 'genetics'` in `PlantOverviewDialogState`. We need to add the tab button and render the genetics content.

**Step 1: Update tab type**

The `_activeTab` state is already typed as `'dashboard' | 'actions' | 'timeline' | 'harvest'`. Add `'genetics'`:

```typescript
@state() private _activeTab: 'dashboard' | 'actions' | 'timeline' | 'harvest' | 'genetics' = 'dashboard';
```

Also update the `updated()` guard that validates `activeTab`:
```typescript
if (
  this.dialog.activeTab === 'dashboard' ||
  this.dialog.activeTab === 'actions' ||
  this.dialog.activeTab === 'timeline' ||
  this.dialog.activeTab === 'genetics'   // add this
) {
  this._activeTab = this.dialog.activeTab;
}
```

**Step 2: Add Genetics tab button**

Find the tab button block (around line 956) and add after the Timeline tab:

```typescript
<button
  class="tab-btn ${this._activeTab === 'genetics' ? 'active' : ''}"
  @click=${() => (this._activeTab = 'genetics')}
>
  Genetics
</button>
```

**Step 3: Add genetics rendering to the content switch**

Find:
```typescript
${this._activeTab === 'dashboard'
  ? this._renderDashboard(attributes)
  : this._activeTab === 'actions'
    ? this._renderActions()
    : this._activeTab === 'harvest'
      ? this._renderHarvestTab()
      : this._renderTimeline()}
```

Update to:
```typescript
${this._activeTab === 'dashboard'
  ? this._renderDashboard(attributes)
  : this._activeTab === 'actions'
    ? this._renderActions()
    : this._activeTab === 'harvest'
      ? this._renderHarvestTab()
      : this._activeTab === 'genetics'
        ? this._renderGeneticsTab()
        : this._renderTimeline()}
```

**Step 4: Implement `_renderGeneticsTab()`**

```typescript
private _renderGeneticsTab() {
  const attributes = this.dialog.plant?.attributes;
  const scores = attributes?.scores ?? {};

  return html`
    <div class="genetics-tab">
      <h4>Phenotype scores</h4>
      <p class="genetics-subtitle">Rate 1–10, leave blank to skip</p>

      ${(['vigor', 'structure', 'aroma', 'resin', 'pest_resistance'] as const).map(
        (trait) => html`
          <div class="score-row">
            <label class="score-label">${trait.replace('_', ' ')}</label>
            <input
              type="number"
              min="1"
              max="10"
              .value=${scores[trait] != null ? String(scores[trait]) : ''}
              @input=${(e: Event) => {
                const val = parseInt((e.target as HTMLInputElement).value);
                this._scoresEdit = {
                  ...this._scoresEdit,
                  [trait]: isNaN(val) ? null : Math.min(10, Math.max(1, val)),
                };
              }}
            />
          </div>
        `
      )}

      <button
        class="md3-button filled"
        @click=${this._saveScores}
      >
        Save scores
      </button>

      <div class="genetics-actions">
        <h4>Pollination</h4>
        <button
          class="md3-button tonal"
          @click=${() => {
            this.dispatchEvent(
              new CustomEvent('open-log-pollination', {
                detail: { plant_id: this.dialog.plant?.entity_id },
                bubbles: true,
                composed: true,
              })
            );
          }}
        >
          Log pollination
        </button>
      </div>
    </div>
  `;
}

private async _saveScores() {
  const plant = this.dialog.plant;
  if (!plant) return;

  const scores = this._scoresEdit;
  const payload: Record<string, unknown> = { plant_id: plant.entity_id };

  for (const [key, val] of Object.entries(scores)) {
    if (val != null) payload[key] = val;
  }

  try {
    await this.hass.callService('growspace_manager', 'score_plant', payload);
    this._scoresEdit = {};
  } catch (e) {
    console.error('Failed to save scores', e);
  }
}
```

Note: Check how `this.hass` and `_scoresEdit` are accessed — `_scoresEdit` already exists in this dialog for the harvest tab. Reuse it or add a separate `_phenotypeScoresEdit`.

**Step 5: Handle open-log-pollination event in dialog-host**

In `dialog-host.ts`, listen for `open-log-pollination` on the plant overview dialog element and call `openStrainLibraryDialog(ctx, 'seeds')`.

**Step 6: Build check**

```bash
cd vendor/lovelace-growspace-manager-card && npm run build 2>&1 | grep -E "error|Error" | head -20
```

Fix any type errors.

**Step 7: Commit**

```bash
git add vendor/lovelace-growspace-manager-card/src/dialogs/plant-overview-dialog.ts \
        vendor/lovelace-growspace-manager-card/src/components/manager/dialog-host.ts
git commit -m "feat(genetics): add Genetics tab to plant overview dialog"
```

---

## Task 17: Final build and test run

**Step 1: Run full backend tests**

```bash
cd vendor/growspace_manager && /home/maxi/core/core/.venv/bin/pytest tests/ -q --tb=short
```

All tests must pass.

**Step 2: Run full frontend build**

```bash
cd vendor/lovelace-growspace-manager-card && npm run build 2>&1 | tail -10
```

Must complete with no errors.

**Step 3: Commit if anything was missed**

```bash
git add -p
git commit -m "fix(genetics): address build/test issues"
```

---

## Key files reference

### Backend
- `vendor/growspace_manager/custom_components/growspace_manager/models.py` — add SeedBatch, PollinationEvent
- `vendor/growspace_manager/custom_components/growspace_manager/const.py` — new constants
- `vendor/growspace_manager/custom_components/growspace_manager/schemas.py` — new schemas
- `vendor/growspace_manager/custom_components/growspace_manager/managers/genetics.py` — new file
- `vendor/growspace_manager/custom_components/growspace_manager/services/genetics.py` — new file
- `vendor/growspace_manager/custom_components/growspace_manager/service_registration.py` — register services
- `vendor/growspace_manager/custom_components/growspace_manager/coordinator.py` — add genetics_manager
- `vendor/growspace_manager/custom_components/growspace_manager/storage_manager.py` — persist genetics
- `vendor/growspace_manager/custom_components/growspace_manager/websocket.py` — add WS handler
- `vendor/growspace_manager/custom_components/growspace_manager/services.yaml` — service docs
- `vendor/growspace_manager/tests/core/test_core_init.py` — update service count

### Frontend
- `vendor/lovelace-growspace-manager-card/src/types.ts` — genetics types
- `vendor/lovelace-growspace-manager-card/src/services/api/genetics-api.ts` — new file
- `vendor/lovelace-growspace-manager-card/src/services/data-service.ts` — register API
- `vendor/lovelace-growspace-manager-card/src/lib/types/dialog.ts` — update dialog state
- `vendor/lovelace-growspace-manager-card/src/store/ui/ui-actions.ts` — initialTab param
- `vendor/lovelace-growspace-manager-card/src/components/manager/dialog-host.ts` — pass genetics data
- `vendor/lovelace-growspace-manager-card/src/dialogs/strain-library-dialog.ts` — Seeds tab
- `vendor/lovelace-growspace-manager-card/src/dialogs/plant-overview-dialog.ts` — Genetics tab
