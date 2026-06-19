The Room Model

At the heart of Roomify is the concept that a room is more than a collection of lights.

Traditional automation systems tend to operate on individual devices. Roomify instead treats the room itself as a first-class object with its own configuration, state, and behavior.

A Roomify room serves as a container for everything required to automate a physical space.

Occupancy Sources

Each room may designate one or more devices that contribute to occupancy determination.

Examples include:

* Motion sensors
* Presence sensors
* Contact sensors
* Occupancy sustainers
* Occupancy terminators

These devices help Roomify determine whether a room should currently be considered occupied or vacant.

Controlled Devices

A room may contain any number of devices whose state is managed by Roomify.

Examples include:

* Smart bulbs
* Dimmers
* Switches
* Outlets
* Relays

Roomify executes lighting decisions at the room level and then distributes those decisions to participating devices.

These same devices also provide feedback regarding actual device state, allowing Roomify to verify convergence, detect disruption, and optionally manage authority.

Room Configuration

Each room maintains its own automation preferences.

Examples include:

* Room type
* Preferred brightness levels
* Transition durations
* Lighting phase definitions
* Dormancy behavior
* Occupancy automation settings
* Guardrail settings

This configuration defines how the room should behave under various conditions.

Room Type

Every room is assigned a room type.

Examples include:

* Bedroom
* Stairway
* Hallway
* Kitchen
* Living Room
* Closet
* Garage

Room type acts as a policy designator.

A stairway should not necessarily behave like a bedroom, even when both are occupied under identical conditions.

Roomify uses room type information when shaping automation outcomes.

Runtime State

In addition to configuration, each room maintains runtime state.

Examples include:

* Occupied or vacant
* Aggregate room brightness
* Current automation target
* Dormancy status
* Authority status

This state represents Roomify’s current understanding of the room.

Aggregate Room Representation

Roomify exposes each room as a single Indigo device.

This virtual room device provides a unified view of the room’s configuration and current state.

Users can interact with the room directly rather than managing individual devices.

Key Principle

People do not think in terms of bulbs, switches, and sensors.

They think in terms of rooms.

Roomify allows Indigo to model the home the same way.