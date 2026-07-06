Roomify Architecture

Roomify is a room-centric automation framework for Indigo.

Traditional home automation systems focus on individual devices. Roomify introduces the concept of a room as a first-class automation object. Occupancy, schedules, lighting phases, and house mode changes are evaluated at the room level to determine an appropriate lighting target.

The resulting room target is then applied to the devices that participate in that room.

Automation Flow

Roomify continuously evaluates changes in context, including:

* Occupancy changes
* House mode changes
* Lighting phase transitions
* Scheduled events
* Direct room commands

These context changes trigger an automation evaluation.

The evaluation determines the desired state of the room. That desired state is then passed through the Roomify policy layer, where house mode and room type influence the final outcome.

The resulting adjusted room target is executed through the Roomify room device and propagated to participating devices.

Key Principle

Roomify automates rooms, not devices.

Devices are implementation details. The room is the automation object.