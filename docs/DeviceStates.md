# Device States Reference

## Roomify Observer

The Roomify Observer device is a read-only device maintained by the plugin. It provides visibility into Roomify's current global operating state.

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

## Roomify Room

A Roomify Room device represents a logical room and exposes occupancy, automation, lighting, scheduling, and diagnostic state information.

### Core Occupancy States

|State|Type|Description|
|---|---|---|
|`occupied`|Boolean|Current occupancy status of the room.|
|`onState`|Boolean|Current room lighting state.|
|`brightness`|Number|Current room brightness level.|
|`lightingPhase`|String|Current phased-lighting stage.|
|`phasedLightingEnabled`|Boolean|Indicates whether phased lighting is enabled.|

### Automation Configuration

|State|Type|Description|
|---|---|---|
|`roomOccupancyAutomationActive`|Boolean|Occupancy-triggered automation enabled for this room.|
|`automationsAuthorized`|Boolean|Indicates whether automation execution is currently authorized.|
|`automationGateStatus`|Boolean|Result of evaluating configured automation gates.|
|`autoOffBrightness`|Number|Brightness level used when automating an OFF action.|
|`initialBrightness`|Number|Initial brightness applied on occupancy.|
|`delayedBrightness`|Number|Brightness applied during delayed phase.|
|`outroBrightness`|Number|Brightness applied during outro phase.|

### Occupancy Cutoff / Watchdog

|State|Type|Description|
|---|---|---|
|`roomDormancyCutoffActive`|Boolean|Room-specific dormancy cutoff enabled.|
|`watchdogMinutes`|Number|Current watchdog duration.|
|`watchdogCutoff`|Number|Watchdog cutoff value.|
|`watchdogCutoffDisplay`|String|Human-readable watchdog cutoff.|
|`occupancyCutoff`|Number|Occupancy cutoff value.|
|`occupancyCutoffUI`|String|Human-readable occupancy cutoff.|
|`cutoffCyclesRemaining`|Number|Remaining cutoff extension cycles.|
|`cutoffCyclesIncrement`|Number|Cutoff increment applied per cycle.|

### Automation Lifecycle

|State|Type|Description|
|---|---|---|
|`automationState`|Number|Internal automation state identifier.|
|`automationStateUI`|String|Human-readable automation state.|
|`minutesRemaining`|Number|Minutes remaining in current automation phase.|
|`activeModifier`|String|Currently active automation modifier.|

### Lighting Schedule

|State|Type|Description|
|---|---|---|
|`delayedLightingStarttime`|Number|Epoch timestamp for delayed lighting phase start.|
|`delayedLightingStarttimeUI`|String|Human-readable delayed lighting start time.|
|`outroLightingStarttime`|Number|Epoch timestamp for outro lighting phase start.|
|`outroLightingStarttimeUI`|String|Human-readable outro lighting start time.|

### Evaluation Scheduler

|State|Type|Description|
|---|---|---|
|`nextEvaluationTime`|Number|Next scheduled room evaluation time.|
|`nextEvaluationTimeUI`|String|Human-readable next evaluation time.|
|`nextEvaluationInitiator`|String|Source that scheduled the evaluation.|
|`nextEvaluationClass`|String|Classification of the scheduled evaluation.|

### Authority Tracking

|State|Type|Description|
|---|---|---|
|`authorityChangePriorState`|Boolean|Previous authority state.|
|`authorityChangeNewState`|Boolean|New authority state.|
|`authorityChangeInitiator`|String|Source of authority change.|
|`authorityChangeTimestamp`|String|Timestamp of authority change.|
|`authorityChangeEpoch`|Number|Epoch timestamp of authority change.|

### Audit and Diagnostics

| State                    | Type    | Description                            |
| ------------------------ | ------- | -------------------------------------- |
| `auditBurden`            | Number  | Current audit workload value.          |
| `auditPending`           | Boolean | Indicates whether an audit is pending. |
| `auditAttemptsRemaining` | Number  | Remaining audit attempts.              |
|                          |         |                                        |
![](images/RoomifyLogo215.png)