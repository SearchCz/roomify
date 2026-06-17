# The Observer Model

Roomify supports an optional Observer device that provides visibility into plugin-wide state and activity.

Unlike Roomify room devices, which represent individual spaces within the home, the Observer represents the Roomify system as a whole.

The Observer does not control anything.

Its purpose is to publish information.

## Why an Observer Exists

Indigo devices provide a convenient way to expose information to:

* Control Pages
* Variables
* Scripts
* Triggers
* Other plugins
* Homeowners  

Rather than requiring users to inspect log files or internal plugin data, Roomify publishes important global information through a dedicated Observer device.

## Published Information

Depending on the version of Roomify and enabled features, the Observer may publish information such as:

* Current house mode
* Last publish timestamp
* Automation status
* Plugin status
* Diagnostic information
  
The Observer acts as a read-only window into the current state of the Roomify system.

## One Observer, Many Rooms
 
A Roomify installation may contain many room devices.

Each room represents a single physical space.

The Observer exists separately from those rooms and represents information that applies to the plugin as a whole.

## Integration with Indigo

Because the Observer is implemented as a standard Indigo device, its states can be consumed by:

* Trigger conditions
* Scripts
* Control Pages
* Variables
* Third-party plugins

This allows users to incorporate Roomify-wide information into broader automation workflows.
 
## Design Philosophy

Room devices answer the question:
“What is happening in this room?”

The Observer answers the question:
“What is happening in Roomify?”

By separating room-level state from plugin-level state, Roomify provides visibility into both the individual spaces being automated and the overall system responsible for automating them.


### States

|State|Type|Description|
|---|---|---|
|`houseMode`|String|Current Roomify house mode.|
|`roomDormancyCutoffEnabled`|String|Indicates whether room dormancy cutoff functionality is globally enabled.|
|`occupancyAutomationEnabled`|String|Indicates whether occupancy-triggered automation is globally enabled.|
|`roomAutomationCalmingPeriod`|String|Global automation calming period configuration.|
|`houseModesEnabled`|String|Indicates whether house mode functionality is enabled.|
|`lastPublishTimestamp`|String|Timestamp of the last observer state publication.|

---


![](images/RoomifyLogo215.png)