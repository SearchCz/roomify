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

## System-Wide Actions

### Automation Authority / Occupancy State

These actions are useful when you want a particular outcome throughout all rooms of the home. Times when you want a temporary break from the automations, like when cleaning the house or hosting a party. Times when you want all the rooms to turn off, like when everyone has left the home or gone to bed. 

| Action                         | Description                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------ |
| Surrender Authority Everywhere | Places all rooms into standby mode.                                            |
| Resume Authority Everywhere    | Returns all rooms to active mode.                                              |
| Occupy All Rooms               | Simulates occupancy in all rooms, intiating automations where permitted.       |
| Vacate All Rooms               | Simulates vacancy in all rooms, initiatiating vacancy behavir where permitted. |

These actions affect occupancy and authority state. They do not directly control lighitng, but rooms will typically respond by changing their lighitng where appropriate. 

Used in sequence (and with house modes) these can invoke lighting changes everywhere. Here are a few possibilities to consider:

**Start Cleaning Mode Sequence:**
1. Resume Authority Everywhere - prepares all the rooms to execute their automations
2. Occupy All Rooms - initiates automations everywhere, lighting those rooms
3. Set House Mode to Cleaning - raises automated lights to their brightest potential, everywhere
4. Surrender Authority Everywhere - so that the rooms don't switch themselves off

**End Cleaning Mode Sequence:**
1. Resume Authority Everywhere - prepares rooms to execute theit automations
2. Set House Mode to Day (or whatever) - lighting changes accordingly
3. Occupy All Rooms - returns all room automations to their initial state. Rooms will progress through any configured lighting phases eventually landing on vacancy if no presence is detected in the room. Or, Vacate All Rooms and the lights go out.

**Exit Sequence**
1. Resume Authority Everywhere - prepares rooms to execute their automations
2. Vacate All Rooms - bypasses lighting transitions and delays, moving the room directly into its vacant state.
3. Set House Mode to Away (optionally) 

**Bedtime Sequence**
1. Resume Authority Everywhere
2. Set House Mode to Night
   
   --- then, after a delay or confirmation that all are in bed ---
   
3. Set House Mode to Sleep
4. Vacate All Rooms
   





![](images/RoomifyLogo215.png)