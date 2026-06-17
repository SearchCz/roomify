# Roomify Actions Reference

## Dormancy Cutoff Settings

These actions control Roomify's room dormancy cutoff system.

### System-Level Actions

|Action|Scope|Description|
|---|---|---|
|System Enable: Room Dormancy Cutoff|Global|Enables the dormancy cutoff feature for all rooms.|
|System Disable: Room Dormancy Cutoff|Global|Disables the dormancy cutoff feature for all rooms.|
|System Toggle: Room Dormancy Cutoff|Global|Toggles the global dormancy cutoff setting.|

### Room-Level Actions

|Action|Scope|Description|
|---|---|---|
|Room Activate: Dormancy Cutoff|Room|Enables dormancy cutoff for a specific room.|
|Room De-Activate: Dormancy Cutoff|Room|Disables dormancy cutoff for a specific room.|
|Room Toggle: Dormancy Cutoff|Room|Toggles dormancy cutoff for a specific room.|

---

## Occupancy-Triggered Automation

These actions control occupancy-based automation behavior.

### System-Level Actions

|Action|Scope|Description|
|---|---|---|
|System Enable: Occupancy-Triggered Automation|Global|Enables occupancy automation globally.|
|System Disable: Occupancy-Triggered Automation|Global|Disables occupancy automation globally.|
|System Toggle: Occupancy-Triggered Automation|Global|Toggles global occupancy automation.|

### Room-Level Actions

|Action|Scope|Description|
|---|---|---|
|Room Activate: Occupancy-Triggered Automation|Room|Enables automation for a room.|
|Room De-Activate: Occupancy-Triggered Automation|Room|Disables automation for a room.|
|Room Toggle: Occupancy-Triggered Automation|Room|Toggles automation for a room.|

### Automation Authority

Automation authority determines whether Roomify may automatically control the room.

| Action                               | Scope | Description                                               |
| ------------------------------------ | ----- | --------------------------------------------------------- |
| Room: Resume Automation Authority    | Room  | Returns control authority to Roomify automation.          |
| Room: Surrender Automation Authority | Room  | Prevents Roomify from making automated changes.           |
| Room: Toggle Automation Authority    | Room  | Toggles automation authority state.                       |
| Room: Advance Automation Status      | Room  | Advances the room automation lifecycle to the next state. |

---

## Room Occupancy

These actions directly manipulate room occupancy status.

|Action|Scope|Description|
|---|---|---|
|Set To Occupied|Room|Forces the room into an occupied state.|
|Set To Vacant|Room|Forces the room into a vacant state.|
|Toggle Occupancy Flag|Room|Toggles occupancy between occupied and vacant.|

> These actions are primarily intended for testing, troubleshooting, and advanced automation workflows.

---

## Set House Mode

House Modes influence Roomify behavior across the entire installation.

### Available Modes

|Action|
|---|
|Set House Mode to Morning|
|Set House Mode to Day|
|Set House Mode to Evening|
|Set House Mode to Night|
|Set House Mode to Sleep|
|Set House Mode to Cleaning|
|Set House Mode to Away|

---

## Set Room Mode

Room Modes define the behavioral profile associated with a Roomify Room.

### Available Room Types

|Mode|
|---|
|Bedroom|
|Bathroom|
|Closet|
|Dining Room|
|Garage|
|Hallway|
|Stairway|
|Kitchen|
|Living Room|
|Media Room|
|Office|
|Patio|
|Utility|

---

## System-Level Settings

### Guardrails

Guardrails provide additional protection against unintended automation behavior.

|Action|Description|
|---|---|
|Enable Guardrails|Enables Roomify guardrail protections.|
|Disable Guardrails|Disables Roomify guardrail protections.|
||
![](images/RoomifyLogo215.png)