"""
Roomify Plugin

Copyright (c) 2026 Daniel Czewski

This software is licensed under the Roomify Community License v1.0.
See LICENSE.md for full terms.

Redistribution and modification must preserve this notice.
"""

from unittest import case

import indigo
import threading
import time
import datetime
import uuid
from collections import deque


#latest changes:
# - 2024.06.20 introducing allOccuoancy and allAuthority capabilities so that roomify can
# -            surrender and resume automation authority everywhere
# -            treat all rooms as occupied or vacant everywhere
# - added the concept of "automation grace period" which is a period of time after occupancy
# - added occupancy indicator sensibilities to better differentiate occupancy beginning -v- continuing occupancy (e.g. occupancy authority sensor that extends the grace period when on)

# - isOn replaces deviceIsOn

#To Do:
# - clean up the intereaction between [sonsors] <--> [occupancy] <--> [timer]
#
# - add brightness control (including a possible fade option)
# - add a periodic reset option (e.g. reset all rooms at 3am every
# - revisit uistatus and indigo.kStateImageSel and (possibly) some state(s) to record the last action taken and/or the reason for that last action ?

# - implement 
class Plugin(indigo.PluginBase):

    def refreshObservers(self):
        observers = indigo.devices.iter("self.roomifyObserver")
        for observer in observers:
            observer.stateListOrDisplayStateIdChanged()


    def buildDeviceStartupTrace(self, devId):
        dev = indigo.devices[devId]
        on = getattr(dev, "onState", None)

        if self.isDimmable(dev):
            brightness = getattr(dev, "brightness", 0)
        else:
            if on:
                brightness = 100
            else:
                brightness = 0
        self.recordDeviceStartup(dev,on,brightness)


    def allAuthority(self, mode):
        rooms = indigo.devices.iter("self.roomifyRoom")
        for room in rooms:
            rc = self.roomCache[room.id]
            if mode:
                rc["automationsAuthorized"] = mode
                self.authorityLog(f"Room '{room.name}' is resuming automation authority.")
                self.recordTransferOfAuthority(room, room.states.get("automationsAuthorized"), True, "INTENTION: Resume authoirty everywhere")
                room.updateStateOnServer("automationsAuthorized",mode)
                self.evaluateAutomationState(room)
            else:
                rc["automationsAuthorized"] = False
                self.recordTransferOfAuthority(room, room.states.get("automationsAuthorized"), False, "INTENTION: Suspend authoirty everywhere")
                room.updateStateOnServer( "automationsAuthorized",False)
                self.evaluateAutomationState(room)


    def allStandby(self, action):
        self.authorityLog(f"Placing all rooms on standby")
        self.allAuthority(False)

    def allAuthorize(self, action):
        self.authorityLog(f"Authorizing all rooms")
        self.allAuthority(True)

    def allOccupy(self, action):
        self.allOccupancy(True)

    def allVacate(self, action):
        self.allOccupancy(False)

    def allOccupancy(self, mode):
        rooms = indigo.devices.iter("self.roomifyRoom")
        for room in rooms:
            self.setOccupancy(room,mode)


    def systemAutomationX(self, action):
        mode = action.pluginTypeId  # e.g. "setNight"
        oldValue = self.globalOccupancyAutomationEnabled
        first6 = mode[:6].lower()

        if first6 == "enable":
            newValue = True 
        elif first6 == "disabl":
            newValue = False        
        elif first6 == "toggle":
            newValue = (not oldValue)

        self.pluginPrefs["ocupancyAutamationEnabled"] = newValue
        self.globalOccupancyAutomationEnabled = newValue
        self.publishToAllObservers()

    def dormancyCutoffX(self, action):
        mode = action.pluginTypeId 
        oldValue = self.globalRoomDormancyCutoffEnabled
        first6 = mode[:6].lower()

        if first6 == "enable":
            newValue = True 
        elif first6 == "disabl":
            newValue = False        
        elif first6 == "toggle":
            newValue = not oldValue

        self.pluginPrefs["roomDormancyCutoffEnabled"] = newValue
        self.globalRoomDormancyCutoffEnabled = newValue
        self.publishToAllObservers()

    def timeoutsX(self, action, device):

        mode = action.pluginTypeId  # e.g. "setNight"
        oldValue = device.states.get("roomDormancyCutoffActive")
        first6 = mode[:6].lower()

        if first6 == "enable":
            newValue = True
        elif first6 == "disabl":
            newValue = False       
        elif first6 == "toggle":
            newValue = not oldValue

        device.updateStateOnServer("roomDormancyCutoffActive",newValue)

    def roomAutomationX(self, action, device):

        mode = action.pluginTypeId  # e.g. "setNight"
        oldValue = device.states.get("roomOccupancyAutomationActive")
        first6 = mode[:6].lower()
        newValue = ""

        if first6 == "activa":
            newValue = True
        elif first6 == "deacti":
            newValue = False       
        elif first6 == "toggle":
            newValue = not oldValue

        self.roomCache[device.id]["roomOccupancyAutomationActive"] = newValue
        device.updateStateOnServer("roomOccupancyAutomationActive",newValue)
        self.evaluateAutomationState(device)

    def roomAuthorityX(self, action, device):

        mode = action.pluginTypeId  # e.g. "setNight"
        oldValue = device.states.get("automationsAuthorized")
        first5 = mode[:5].lower()

        if first5 == "grant":
            newValue = True
        elif first5 == "revok":
            newValue = False       
        elif first5 == "toggl":
            newValue = not oldValue

        rc = self.roomCache[device.id]
        rc["automationsAuthorized"] = newValue

        self.recordTransferOfAuthority(device, oldValue,newValue, "INTENTION: Indigo Callback Invoked")

        device.updateStateOnServer("automationsAuthorized",newValue)
        self.evaluateAutomationState(device)

    def roomOccupancyX(self, action, device):

        rc = self.roomCache[device.id]
        mode = action.pluginTypeId  # e.g. "setNight"

        oldValue = rc.get("occupied")

        newMode = mode.removeprefix("set").upper()


        if newMode == "OCCUPIED":
            newValue = True
        elif newMode == "VACANT":
            newValue = False       
        elif newMode == "TOGGLE":
            newValue = not oldValue

        self.debugLog(f"Setting {device.name} occupancy to {newValue}")
        self.setOccupancy(device,newValue)

        #device.updateStateOnServer("occupied",newValue)


    def deviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        
        menu = [("none", "(none)")]
        for dev in indigo.devices:
            menu.append((str(dev.id), dev.name))

        menu.append(("none","(none)"))
        return menu


    def recordTransferOfAuthority(self, room, priorState, newState, cause):
        rc = self.roomCache[room.id]
        rc["authorityChangeInitiator"] = cause
        now = time.time()
        humanTime = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        self.authorityLog(f"{room.name} automations authorized state from {priorState} to {newState} due to {cause}")
        room.updateStatesOnServer([
            {"key": "authorityChangePriorState", "value": priorState},
            {"key": "authorityChangeNewState", "value": newState},
            {"key": "authorityChangeInitiator", "value": cause},
            {"key": "authorityChangeTimestamp", "value": humanTime},
            {"key": "authorityChangeEpoch", "value": now},
        ])


    def getBoundedTargetBrightness(self, room, targetBrightness):

        roomType = room.pluginProps.get("roomType")
        profile = self.getRoomTypeDefaults(roomType)

        defaultLow = profile.get("autoBrightnessLowLimit", 20)
        defaultHigh = profile.get("autoBrightnessHighLimit", 100)

        def parse(value, fallback):
            if value is None:
                return fallback
            if isinstance(value, str):
                if value.lower() in ["default", "defaut", ""]:
                    return fallback
                try:
                    return int(value)
                except:
                    return fallback
            return int(value)

        roomLow = parse(room.pluginProps.get("autoBrightnessLowLimit"), defaultLow)
        roomHigh = parse(room.pluginProps.get("autoBrightnessHighLimit"), defaultHigh)

        # safety swap if misconfigured
        if roomLow > roomHigh:
            roomLow, roomHigh = roomHigh, roomLow

        targetBrightness = int(targetBrightness)

        clamped = max(roomLow, min(targetBrightness, roomHigh))

        self.debugLog(
            f"{roomType} room {room.name} "
            f"proposed={targetBrightness} clamped={clamped} "
            f"(low={roomLow}, high={roomHigh})"
        )

        return clamped
    
    def getBoundedTargetBrightnessX(self, room, targetBrightness):
        roomType = room.states.get("roomType")
        profile = self.getRoomTypeDefaults(roomType)

        defaultLow = profile.get("autoBrightnessLowLimit", 20)
        defaultHigh = profile.get("autoBrightnessHighLimit", 100)
        defaultOff = profile.get("autoOffBrightness", 0)

        roomLow = room.states.get("autoBrightnessLowLimit")
        if not roomLow:
            roomLow = defaultLow
        elif roomLow == "Default":
            roomLow = defaultLow
        else:
            roomLow = int(roomLow)

        roomHigh = room.states.get("autoBrightnessHighLimit")
        if not roomHigh:
            roomHigh = defaultHigh
        elif roomHigh == "Defautl":
            roomHigh = defaultHigh
        else:
            roomHigh = int(roomHigh)

        clamped = max(roomLow, min(targetBrightness, roomHigh))

        self.automationLog(f"{roomType} roomm {room.name} has proposed brightness of {targetBrightness} clamped at {clamped}")

        return clamped

    def getRoomTypeDefaults(self, roomType):
        """
        Returns default boundary settings for a given room type.
        Falls back to safe global defaults if unknown.
        """

        fallback = {
            "automationGates": None,
            "autoOffBrightness": 0,
            "autoBrightnessLowLimit": 20,
            "autoBrightnessHighLimit": 100
        }

        return self.roomTypeDefaults.get(roomType, fallback)

    def buildRoomTypeDefaults(self):
        """
        Initializes default brightness/automation boundaries per room type.
        Stored in self.roomTypeDefaults
        """

        self.roomTypeDefaults = {
            "BEDROOM": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 0,   # allow full dim
                "autoBrightnessHighLimit": 100
            },

            "BATHROOM": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 10,
                "autoBrightnessHighLimit": 100
            },

            "CLOSET": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 50,
                "autoBrightnessHighLimit": 100
            },

            "DININGROOM": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 20,
                "autoBrightnessHighLimit": 100
            },

            "GARAGE": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 75,  # safety visibility bias
                "autoBrightnessHighLimit": 100
            },

            "HALLWAY": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 50,
                "autoBrightnessHighLimit": 100
            },

            "STAIRWAY": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 75,
                "autoBrightnessHighLimit": 100
            },

            "KITCHEN": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 30,
                "autoBrightnessHighLimit": 100
            },

            "LIVINGROOM": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 20,
                "autoBrightnessHighLimit": 100
            },

            "MEDIAROOM": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 15,
                "autoBrightnessHighLimit": 80
            },

            "OFFICE": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 20,
                "autoBrightnessHighLimit": 100
            },

            "PATIO": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 40,
                "autoBrightnessHighLimit": 100
            },

            "UTILITY": {
                "automationGates": None,
                "autoOffBrightness": 0,
                "autoBrightnessLowLimit": 20,
                "autoBrightnessHighLimit": 80
            },
        }

    def recordRoomifyIntent(self, dev, onState, brightness):
        state = self.canonical.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        state["lastUpdate"] = time.time()
        state["source"] = "Roomify"
        self.canonical[dev.id] = state
        self.trace(dev.id, dev.name, "intent", state)


    def checkForCompliance(self, devId, onState, brightness):
        if self.checkForDivergence( devId, onState, brightness):
            return False
        else:
            return True
        

    def checkForDivergence(self, devId, onState, brightness):
        state = self.canonical.get(devId, {})

        if state:
            if ( state["onState"] != onState ):
                return True

            if brightness == None or state["brightness"] == None:
                return False
            
            if brightness != state["brightness"]:
                return True

        return False

    def recordDeviceStartup(self, dev, onState, brightness):
        #LATENCY ?
        state = self.lastreport.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        state["lastUpdate"] = time.time()
        state["source"] = "Startup"

        self.lastreport[dev.id] = state
        self.trace(dev.id, dev.name, "startup", state)



    def recordDeviceDisrupt(self, dev, onState, brightness):
        #DEPRECATED
        #LATENCY ?
        state = self.lastreport.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        state["lastUpdate"] = time.time()
        state["source"] = "Unknown"

        self.lastreport[dev.id] = state
        self.trace(dev.id, dev.name, "unsolicited", state)

    def recordDeviceReport(self, dev, onState, brightness, alignment, authorityImpact):
        #LATENCY ?
        state = self.lastreport.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        if alignment is not None:
            state["alignment"] = alignment

        if authorityImpact is not None:
            state["authorityImpact"] = authorityImpact

        state["lastUpdate"] = time.time()
        state["source"] = "Device"

#        self.logger.info(f"Recording device report for {dev.name} (id {dev.id}) with state: {state}")

        self.lastreport[dev.id] = state
        self.trace(dev.id, dev.name, "report", state)




    def recordSensorReport(self, dev, onState, brightness):
        #LATENCY ?

        sensor = dev

        #self.logger.info(f">>> Sensor {sensor.name} recording {onState} state. <<<")
        #self.logger.info(sensor.states)

        state = self.lastsense.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        state["lastUpdate"] = time.time()
        state["source"] = "Sensor"

        self.lastsense[dev.id] = state
        self.trace(dev.id, dev.name, "sensor", state)



    def recordDeviceReportX(self, dev, onState, brightness):
        #LATENCY ?
        state = self.lastnoise.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        state["lastUpdate"] = time.time()
        state["source"] = "Device"
        

        self.lastnoise[dev.id] = state
        self.trace(dev.id, dev.name,  "noise", state)


    def recordDeviceCommand(self, dev, onState, brightness):
        state = self.lastcommand.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        state["lastCommand"] = time.time()
        state["source"] = "Unknown"

        self.lastcommand[dev.id] = state
        self.trace(dev.id, dev.name, "command", state)

    # LATENCY
    def trace(self, devId, devName, eventType, state):

        if devId not in self.traceCache:
            self.traceCache[devId] = {
                "devName": devName,
                "trace": deque(maxlen=50),
                "initialLatency": None,
                "latencyTotal": 0.0,
                "latencyCount": 0,
                "complied": False,
            }
#            if eventType in [ "report","noise" ]:
#                dev = indigo.devices[devId]
#                self.recordDeviceDisrupt( dev, state.get("onState"), state.get("brightness"))
#                self.revokeRooms(devId)


        cache = self.traceCache[devId]
        trace = cache["trace"]

        previous = trace[-1] if trace else None

        delta = None
        average = None
        il = None

        if previous is not None:
            delta = state["lastUpdate"] - previous["time"]
        else:
            delta = 0

        # New intent starts a fresh measurement cycle
        responseWindow = 15
        if cache["initialLatency"] != None:
            responseWindow = (cache["latencyTotal"] / cache["latencyCount"]) * self.K
        else:
            responseWindow = 15

        if responseWindow == None:
            responseWindow = 15

        il = cache["initialLatency"]
        if eventType == "intent":
            cache["initialLatency"] = None
            #cache["latencyTotal"] = 0.0
            #cache["latencyCount"] = 0
            cache["complied"] = False

        # Ignore disrupted reports in the average
        elif delta is not None and eventType in ["report","noise"] and cache["initialLatency"] == None:
            il = delta
            cache["initialLatency"] = delta
            cache["latencyTotal"] += delta
            cache["latencyCount"] += 1

        if cache["latencyCount"]:
            average = cache["latencyTotal"] / cache["latencyCount"]

        newConversation = False

        if eventType == "intent":
            newConversation = True

        if eventType == "report":
            if self.checkForCompliance(devId, state.get("onState"), state.get("brightness")):
                cache["complied"] = True

            #CZEWSKI: NEW DISRUPTION LOGIC LIVES HERE
#            if cache["complied"] == True and cache["initialLatency"] != None and delta > responseWindow and eventType in ["report","noise"]:
            if cache["complied"] == True and eventType == "report":
                if delta > responseWindow:
                    newConversation = True
                looksLikeNonCompliance = self.looksLikeNonCompliance(devId, state)
                if looksLikeNonCompliance:
                    self.logger.info(f"********************************** NON-COMPLIANCE SUSPECTED ON DEVICE {devName} *****************************************")
                    self.refreshDeviceStatus(devId)
#                if not looksLikeNonCompliance:
#                    DISS = self.checkForDivergence(devId, state.get("onState"), state.get("brightness"))
#                    if DISS:
#                        dev = indigo.devices[devId]
#                        self.recordDeviceDisrupt( dev, state.get("onState"), state.get("brightness"))
#                        self.revokeRooms(devId)

        #ADDING on 2026-7-10 to begin a new trace whenever any "intent" is reported
        if eventType == "intent":
            keep = list(trace)[-10:]
            trace.clear()
            trace.extend(keep)
    #            cache["latencyTotal"] = 0.0
    #            cache["latencyCount"] = 0

#        self.logger.info(f"DEBUG il={locals().get('il', '<missing>')}")

        trace.append({
            "newConversation": newConversation,
            "uuid": state.get("uuid"),
            "time": state["lastUpdate"],
            "type": eventType,
            "initialLatency": il,
            "delta": delta,
            "average": average,
            "onState": state.get("onState"),
            "brightness": state.get("brightness"),
            "source": state.get("source"),
            "alignment": state.get("alignment"),
            "authorityImpact": state.get("authorityImpact")
        })


    def looksLikeNonCompliance(self, devId, state):

        cache = self.traceCache.get(devId)
        if cache is None:
            trace = []
        else:
            trace = cache["trace"]

        intent = None
        priorReport = None

        #
        # Walk backwards:
        #   report (current) ...
        #   intent
        #   report (pre-intent)
        #
        for entry in reversed(trace):

            if intent is None:
                if entry["type"] == "intent":
                    intent = entry
                continue

            if entry["type"] == "report":
                priorReport = entry
                break

        if intent is None or priorReport is None:
            return False

        #
        # Too old to be considered a reversion.
        #
        if time.time() - intent["time"] > 70:
            return False

        #
        # Did we return to the pre-intent state?
        #
        if priorReport["onState"] != state.get("onState"):
            return False

        pb = priorReport.get("brightness")
        cb = state.get("brightness")

        if pb is None or cb is None:
            return True

        return pb == cb

    def refreshRoomStatus(self, action, device):
        self.requestRoomStatus(device.id)

    def reportRoomCache(self, action, device):
        self.dumpRoomCache(device.id)

    def reportRoomTrace(self, action, device):

        events = []

        devId = device

        room = indigo.devices[devId]
        self.logger.info(f"*********** Reporting Conversation Trace for {room.name} ***********")
        controlled = room.pluginProps.get("controlledDevices") or []
        sensed = room.pluginProps.get("occupancyIndicators") or []

        self.logger.info(f"controlled: {repr(controlled)}")
        self.logger.info(f"sensed:     {repr(sensed)}")

        #SENSORS
#        sensed = room.pluginProps.get("occupancyIndicators") or []


        for devId in sensed:
            devId = int(devId)
            self.logger.info(f"Looking for reports from sesor ID {devId}")

            cache = self.traceCache.get(devId)
            if not cache:
                continue

            self.logger.info(f"Processing Reports from {cache['devName']}")
            for event in cache["trace"]:
                events.append({
                **event,
                "device": cache["devName"],
            })

        #LIGHTS
        controlled = room.pluginProps.get("controlledDevices") or []
        controlled = [int(x) for x in controlled]

        
        for devId in controlled:
            cache = self.traceCache.get(devId)
            if not cache:
                continue

            for event in cache["trace"]:
                events.append({
                **event,
                "device": cache["devName"],
            })


        events.sort(key=lambda e: e["time"])

#        self.logger.info("")
#        self.logger.info(f"Trace for '{room.name}'")
#        self.logger.info("-" * 100)

        for e in events:
            timestamp = time.strftime("%H:%M:%S", time.localtime(e["time"]))
            delta = "--" if e["delta"] is None else f"{e['delta']:6.3f}s"
            average = "--" if e["average"] is None else f"{e['average']:6.3f}s"

            initial = "--"
            if e["initialLatency"] is not None:
                initial = f"{e['initialLatency']:.3f}s"

            traceCat = self.traceEventCategory(e["source"]) + " " + e['type']

            p = e['source'] + " " + e['type']
            o=""
            a = e.get('alignment')
            if a == None:
                a = "--"
            else:
                a = "(" + str(a) + ")"

            if e['onState'] == True:
                o = "ON"    
            else:
                o = "OFF"

            auth=e.get('authorityImpact')
            if auth == None or auth == "None":
                auth = ""
            else:
                auth = str(auth)



            self.logger.info(
                f"{timestamp}  "
                f"{e['device']:<20}  "
                f"{p:<16}  "
                f"{o:<3} "
                f"{e['brightness']!s:4}  "
                f"{auth:<12} "
                f"Δ={delta}  "
                f"i={initial:>8}  "
                f"μ={average}  "
            )



    def reportDeviceTrace(self, action, device):
        devId = int(action.props["device"])
        self.reportTrace(devId)

    def reportTrace(self, devId):

        devId = int(devId)

        if devId == 0:
            self.logger.warning("No device selected.")
            return

        dev = indigo.devices[int(devId)]
        cache = self.traceCache.get(devId)

        self.logger.info("")
        self.logger.info(f"Trace for '{dev.name} id {dev.id}'")
        self.logger.info("-" * 100)

        if not cache:
            self.logger.info("No trace recorded.")
            return

        trace = cache["trace"]

        for event in trace:

            delta = "--"
            if event["delta"] is not None:
                delta = f"{event['delta']:.3f}s"

            average = "--"
            if event["average"] is not None:
                average = f"{event['average']:.3f}s"

            timestamp = datetime.datetime.fromtimestamp(
                event["time"]
            ).strftime("%H:%M:%S.%f")[:-3]

            uuid = str(event.get("uuid") or "--------")[:8]

            marker = ""
            if event.get("newConversation"):
                marker = "************************ NEW ************************"
                self.logger.info(marker)

            if event["type"] == "intent":
                self.logger.info("")

            #traceCat = self.traceEventCategory(event["source"]) + " " + event['type']
            initial = "--"
            if event["initialLatency"] is not None:
                initial = f"{event['initialLatency']:.3f}s"

            p = event['source'] + " " + event['type']
            o=""
            a = event.get('alignment')
            if a == None:
                a = "--"
            else:
                a = "(" + str(a) + ")"

            if event['onState'] == True:
                o = "ON"    
            else:
                o = "OFF"

            auth=event.get('authorityImpact')
            if auth == None or auth == "None":
                auth = ""
            else:
                auth = "Auth " + str(auth)

            self.logger.info(
                f"{timestamp}  "
                f"{p:<16}  "
                f"{o:<3} "
                f"{event['brightness']!s:4}  "
                f"{a:<12} "
                f"Δ={delta:>8}  "
                f"i={initial:>8}  "
                f"μ={average:>8}  "
            )


    def traceEventCategory(self, eventType):
        """
        Return the origin/role of a Roomify trace event.

        RAction - action initiated by Roomify
        IDevice - device event delivered by Indigo
        RClass  - Roomify classification/interpretation of an event
        """

        categories = {
            "intent":       "(r)Action",
            "report":       "(i)Device",
            "unsolicited":  "(r)Class",
            "noise":        "(i)Device",
        }

        return categories.get(eventType, "Unknown")


    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):

        pluginProps["occupancyAutomationEnabled"] = str(self.pluginPrefs.get("occupancyAutomationEnabled", False)).lower()
        pluginProps["roomDormancyCutoffEnabled"] = str(self.pluginPrefs.get("roomDormancyCutoffEnabled", False)).lower()
#        pluginProps["phasedLightingEnabled"] = str(self.pluginPrefs.get("phasedLightingEnabled", False)).lower()


        return super().getDeviceConfigUiValues(pluginProps, typeId, devId)


#    def getConfigUiValues(self, valuesDict, typeId, devId):
#        dev = indigo.devices[devId]
#
#        valuesDict["roomIdentity"] = dev.name
#        valuesDict["roomTypeDisplay"] = dev.pluginProps.get("roomType", "UNKNOWN")
#
#        return valuesDict

    def recomputeRoom(self, room):

        # this block should recalculate the potential brightness targets for a given room
        # 1) starting with the values specified in the device config
        # 2) applying the modification factor
        # 3) applying the guardrail constraints inferred by roomMode
        # save that in the device state for possible application in the room
        self.recomputePhase(room, "initial")
        self.recomputePhase(room, "delayed")
        self.recomputePhase(room, "outro")
        self.evaluateAutomationState(room)
        if self.isOn(room) and self.automationsActionable(room):
            self.automationLog(f"Relighting room {room.name}")
            lightingPhase = room.states.get("lightingPhase")
            room.updateStateOnServer("lightingPhase","inFlux")
            self.autoRoomBrightness(room, lightingPhase)

    def recomputePhase(self, room, phase):
        propKey = phase + "Brightness"
        val = room.pluginProps.get(propKey)
        #self.debugLog(f"Room {room.name} phase {phase} key {propKey} value {val}")
        e = self.computeBrightnessTarget(room,int(val))
        room.updateStateOnServer(propKey,e)


    def setRoomModeX(self, action, device):

        mode = action.pluginTypeId  # e.g. "setNight"
        newType = mode.removeprefix("set").upper()
        oldType = device.pluginProps.get("roomType","UNKNOWN")


        if oldType == newType:
            self.automationLog(f"Room Mode already {newType}, ignoring")
            return
        self.automationLog(f"Setting {device.name} to type {newType}")
        newProps = dict(device.pluginProps)
        newProps["roomType"] = newType

        device.replacePluginPropsOnServer(newProps)
        self.recomputeRoom(device)



# HOUSE MODE CODE

    def suggestHouseMode(self, newMode):
        #this is the entry point for roomify to suggest that other plugins adopt a new housemode
        self.debugLog(f"XTALK: May Suggest house mode {newMode} to Securify")
        if self.suspendCrosstalk:
            self.debugLog("XTALK: Cross-talk suspended. Not suggesting house mode.")
            self.suspendCrosstalk = False
            return
        if self.securifyPlugin and self.securifyPlugin.isEnabled():
            self.debugLog(f"XTALK: Suggesting house mode {newMode} to Securify")
            try:
                self.securifyPlugin.executeAction(
                    "set" + newMode.capitalize() + "Suggested"
                )
            except:
                self.debugLog("XTALK: Error suggesting house mode to Securify")
        else:
            self.debugLog("Securify plugin not available or not enabled. Cannot suggest house mode.")

    def considerHouseModeX(self, action):
        #this is the entry point for roomify to suggest we adopt a new housemode
        #since the roomify plugin is not a dependency, we will only do this if 
        #securify allows this cooperation 
        self.suspendCrosstalk = True
        if self.securifyCooperationEnabled:
            newMode = action.pluginTypeId.removeprefix("set").removesuffix("Suggested").upper()
            self.debugLog(f"XTALK: Accepting suggested house mode {newMode}")
            self.suspendCrosstalk = True
            self.setHouseMode(newMode)

    def shareHouseModeX(self, action):
        #this is how we responde to requests for our current houseMode
        return self.houseMode

    def requestHouseMode(self, action):
        if self.securifyPlugin and self.securifyPlugin.isEnabled():
            self.debugLog(f"XTALK: fetching house mode from Securify")
            try:
                newMode = self.securifyPlugin.executeAction("shareHouseMode")
                self.suspendCrosstalk = True
                self.setHouseMode(newMode)
            except:
                self.debugLog("XTALK: Error fetching house mode from Securify")
        else:
            self.debugLog("Securify plugin not available or not enabled. Cannot suggest house mode.")
        
    def setHouseMode(self, newMode):

        oldMode = self.houseMode

        self.debugLog(f"HouseMode change requested: {oldMode} → {newMode} ... suspend xtalk = {self.suspendCrosstalk}")

        if oldMode == newMode:
            self.deviceLog(f"HouseMode already {newMode}, ignoring")
            self.suspendCrosstalk = False
            return

        self.automationLog(f"HouseMode change: {oldMode} → {newMode} suspend={self.suspendCrosstalk}")
        self.pluginPrefs["houseMode"] = newMode
        self.houseMode = newMode
        self.debugLog(f"NEW ROOMIFY HOUSEMODE={self.houseMode}")

        if self.securifyCooperationEnabled and ( not self.suspendCrosstalk  ):
            self.suggestHouseMode(newMode)

        self.suspendCrosstalk  = False

        # trigger side effects
        self.publishToAllObservers()

        self.recomputeAllRooms()

    def setHouseModeX(self, action):

        mode = action.pluginTypeId  # e.g. "setNight"
        newMode = mode.removeprefix("set").upper()

        self.setHouseMode(newMode)



    def publishToAllObservers(self):
        now = time.time()
        humanTime = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

        if self.nextEvaluationDue is None:
            nextTime = "N/A"
        else:
            nextTime = datetime.datetime.fromtimestamp(self.nextEvaluationDue).strftime("%Y-%m-%d %H:%M:%S")
        observers = indigo.devices.iter("self.roomifyObserver")
        for observer in observers:
            self.publishToObserver(observer,humanTime,nextTime)

    def publishToObserver(self, observer, now, nextTime):
        self.debugLog(f"Publishing houseMode {self.houseMode} to observer {observer.name}")

        observer.updateStatesOnServer([
            {"key": "houseMode", "value": self.houseMode},
            {"key": "roomDormancyCutoffEnabled", "value": self.globalRoomDormancyCutoffEnabled},
            {"key": "occupancyAutomationEnabled", "value": self.globalOccupancyAutomationEnabled},
            {"key": "roomAutomationCalmingPeriod", "value": self.globalRoomAutomationCalmingPeriod},
            {"key": "houseModesEnabled", "value": self.globalHouseModesEnabled},
            {"key": "lastPublishTimestamp", "value": now},
            {"key": "nextEvaluationEpoch", "value": self.nextEvaluationDue},
            {"key": "nextEvaluationUI", "value": nextTime},
        ])


    def recomputeAllRooms(self):
        rooms = indigo.devices.iter("self.roomifyRoom")

        for room in rooms:
            self.recomputeRoom(room)


    def recomputeActiveRooms(self):

        rooms = indigo.devices.iter("self.roomifyRoom")

        for room in rooms:
            if not room.onState:
                self.automationLog(f"Skipping recompute of room {room.name} as room is currently off")
            elif not self.automationsActionable(room):
                self.automationLog(f"Skipping recompute of room {room.name} as room is currently not automated")
            else:
                self.automationLog(f"Recomputing room {room.name}")
                lightingPhase = room.states.get("lightingPhase")
                self.autoRoomBrightness(room, lightingPhase)



    def computeBrightnessTarget(self, room, targetBrightness):



        mode = self.houseMode
        roomType = room.pluginProps.get("roomType", "UNKNOWN")



        scaleMap = {

            "MORNING": float(self.pluginPrefs.get("morningModeFactor", 0.66)),

            "DAY": float(self.pluginPrefs.get("dayModeFactor", 1.00)),

            "EVENING": float(self.pluginPrefs.get("eveningModeFactor", 0.66)),

            "NIGHT": float(self.pluginPrefs.get("nightModeFactor", 0.33)),

            "BEDTIME": float(self.pluginPrefs.get("bedtimeModeFactor", 0.20)),

            "SLEEP": float(self.pluginPrefs.get("sleepModeFactor", 0.00)),

            "AWAY": float(self.pluginPrefs.get("awayModeFactor", 1.00)),

            "CLEANING": float(self.pluginPrefs.get("cleaningModeFactor", 2.00)),

            "QUIET": float(self.pluginPrefs.get("quietModeFactor", 0.40)),

        }


        scale = scaleMap.get(mode, 1.0)

        if self.globalHouseModesEnabled:
            self.automationLog(f"Applying house mode {mode} to {roomType} {room.name} / Scale = {scale}")
            result = int(targetBrightness * scale)

        # safety bounds
        result = self.getBoundedTargetBrightness(room,result)

        self.debugLog(f"Target brightness of {targetBrightness} adjusted to effective brightness of {result}")
        return result


##################

    def RoomDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):

        options = []

        for dev in indigo.devices.iter(self.pluginId.roomifyRoom):
            if dev.deviceTypeId in [ "Room", "roomifyRoom"]:
                options.append((dev.id, dev.name))

        return options

#   ConfigUI Validation

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):

        if typeId == "roomifyObserver":
            return(True, valuesDict)

        errorDict = indigo.Dict()



        for field in [
            "initialTimeout",
            "delayedMinutes",
            "outroMinutes"
        ]:

            try:
                value = int(valuesDict[field])

                if (value < 0) or (value != int(value)) :
                    raise ValueError()

            except:
                errorDict[field] = "Enter a numeric integer."



        for field in [
            "initialBrightness",
            "delayedBrightness",
            "outroBrightness"
        ]:

            try:
                value = int(valuesDict[field])

                if value < 0 or value > 100:
                    raise ValueError()

            except:
                errorDict[field] = "Enter a number from 0 to 100."

####

####

        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)

        return (True, valuesDict)

    def validatePrefsConfigUi(self, valuesDict):
        errorsDict = indigo.Dict()

        factor_fields = [
            "morningModeFactor",
            "dayModeFactor",
            "eveningModeFactor",
            "nightModeFactor",
            "bedtimeModeFactor",
            "sleepModeFactor",
            "awayModeFactor",
            "cleaningModeFactor",
            "quietModeFactor",
        ]

        for field_id in factor_fields:
            raw_value = valuesDict.get(field_id, "").strip()

            try:
                factor = float(raw_value)
            except ValueError:
                errorsDict[field_id] = "Enter a numeric brightness multiplier."
                continue

            if factor < 0:
                errorsDict[field_id] = "Brightness multiplier cannot be negative."
                continue

            valuesDict[field_id] = f"{factor:.2f}"

        if errorsDict:
            return False, valuesDict, errorsDict

        return True, valuesDict

#   AUTOMATION BLOCK

    def autoRoomBrightness(self, room, key, default=0):

        currentPhase = room.states.get("lightingPhase") 

        self.automationLog(f"Room {room.name} lighting phase change requested: from {currentPhase} to {key}")

        if key == currentPhase:
            return

        room.updateStateOnServer("lightingPhase", key)
        propKey = f"{key}Brightness"

        # 1. runtime state first
        val = room.states.get(propKey)
        self.debugLog(f"{room.name} indicates a {propKey} of {val}")

        # 2. fallback to config props
        if val is None or val == "":
            val = room.pluginProps.get(propKey, default)

        # 3. safe conversion
        try:
            targetBrightness = int(val)
        except:
            targetBrightness = default

#        targetBrightness = self.computeBrightnessTarget(room, targetBrightness)

        roomType = room.states.get("roomType")

#DEBOUNCE REPETITIVE ASSERTION OF DUPLICATE INTENT
        targetBrightness = self.getBoundedTargetBrightness(room, targetBrightness)

        rc = self.roomCache[room.id]
        roomifyIntent1 = rc.get("roomifyIntent1")

        try:
            roomifyIntent1 = int(roomifyIntent1) if roomifyIntent1 is not None else None
        except (TypeError, ValueError):
            roomifyIntent1 = None

        if targetBrightness != roomifyIntent1:
            self.autoBrightness(room, targetBrightness)
                
    def autoBrightness(self, room, targetBrightness):
        if self.automationsActionable(room):
            self.turnRoomOn(room, targetBrightness)


    def directRoom(self, room, onState, targetBrightness, delay):
        #self.ignoreNextRoomChange(room, "Roomify-Initiated Change", onState, targetBrightness)
#        rc = self.roomCache[room.id]
#        rc["brightness"] = targetBrightness
        room.updateStatesOnServer([
            {"key": "onState", "value": onState},
            {"key": "onOffState", "value": onState},
            {"key": "brightness", "value": targetBrightness},
            {"key": "brightnessLevel", "value": targetBrightness},
        ])
        rt = self.getRoomRuntime(room.id)
        rt["auditBurden"] = 0
        rt["auditAttemptsRemaining"] = 4
        rt["auditPending"] = False
        #room.updateStateOnServer("auditBurden", 0)
        #room.updateStateOnServer("auditAttemptsRemaining", 4)
        #room.updateStateOnServer("auditPending", False)

        self.applyTargetStateToDevices(room, onState, targetBrightness, 0)

        if targetBrightness == 0:
            self.roomJustTurnedOff(room)


    def turnRoomOn(self, room, targetBrightness):
        self.automationLog(f"Turning ON room: {room.name} to brightness {targetBrightness}")
        self.directRoom(room, True, targetBrightness, 0)
        self.automationLog(f"Setting watchdog cutoff for room '{room.name}'")
        self.setRoomTimeout(room)
        
    def dormancyCutoff(self, room):
        self.turnOff(room, 60)
        nextTime = time.time()+90
        nextName = "Dormancy Cutoff"
        self.scheduleRoomEvaluaiton(room, nextTime, nextName, "Heartbeat")
        #careful here czewski. there is a new global to consider. 

    def dormancyCutoffExtender(self, room):
        nextTime = time.time()+90
        nextName = "Dormancy Cutoff"
        self.scheduleRoomEvaluaiton(room, nextTime, nextName, "Heartbeat")

    def turnRoomOff(self, room):
        self.turnOff(room, 0)

    def turnOff(self, room, delay):
        self.automationLog(f"Turning OFF room: {room.name}")

        #maybe off doesn't really mean off ? 
        autoOffBrightness = room.states.get("autoOffBrightness")
        if autoOffBrightness:
            autoOffBrightness = int(autoOffBrightness)
        if autoOffBrightness > 0:
            self.automationLog(f"Auto-off brightness of {autoOffBrightness} detected for room {room.name}, dimming instead of turning off")
            self.turnRoomOn(room, int(autoOffBrightness), delay)
        else:
            self.directRoom(room, False, 0, delay)
            room.updateStatesOnServer([
                {"key": "lightingPhase", "value": "off"},
                {"key": "watchdogCutoff", "value": None},
                {"key": "watchdogCutoffDisplay", "value": None},
            ])  
            self.roomJustTurnedOff(room)

            #2026-6-6 lets make sure off is off
            #indigo.device.turnOff(room.id)
            self.automationLog(f"Clearing watchdog cutoff for room '{room.name}'")
            self.clearRoomTimeout(room)
        


    def automationsActionable(self, room):

        rc = self.roomCache[room.id]
        gated = True
        actionable =  rc.get("automationsAuthorized", True) and rc.get("roomOccupancyAutomationActive", True) and self.globalOccupancyAutomationEnabled and rc.get("automationGateStatus")
        self.automationLog(f"Room {room.name} automationsActionable = {actionable}")
        return actionable
        gated = room.states.get("automationGateStatus")
        self.debugLog(f"{room.name} automation gate status is {gated}")
        if ( gated is None ) or (gated == "") or (gated == "none"):
            gated = True

        return room.states.get("automationsAuthorized", True) and room.states.get("roomOccupancyAutomationActive", True) and self.globalOccupancyAutomationEnabled and gated
    # ---------------------------------------------------------
    #
    # OCUPANCY management
    #
    # ---------------------------------------------------------
#   Occupancy should be very straigntforward.
#   The sensation of occupancy should aways:
#       - set the "occupancy timeout" for the presumption of occupancy ONLY - not for changes in lighting or any other stats
#           * "extending" isn't really a spacial case at all. its just giving the room occupancy all of its minutes
#           * "clearing" MIGHT be wothwhile whenever ANTHING endeavors to turn the occupancy off. as in, manual changes ?
#           * focus on isolating this room state (presumed occupied) from any other actions
#           * a lighting change does NOT indicate a change of occupancy
#
#   Occupancy Timeout Period is ONLY connected to occupancy. It ONLY needs to change in responde to:
#           * the sensation of presence (or the manual setting of occupancy) SETS it
#           * the passage of time (when occupancy authority is recognized) SETS it (again)
#           * temporal changes PAST expiry signal an END to occupancy (which should CLEAR this state)
#           * this is an OCCUPANCY timeout, not an AUTOMATION timeout
#
#   Let's accomplish this with a few new methods, and clear out all the old ones
#       New Method(s):
#           * setRoomOccupancy(self, room, True/False)
#               - called with room, true each and every time something (sensor, manual override) suggests occupancy
#                   (might change lighting)
#               - called with room, false when accupancy is though to have ended (heartbeat+timeout, manual override) 
#                   (might change lighting)

    def toggleOccupancy(self, action):
        # this one is callable from ourside of the plugin. some EXTERNAL action is pushing this button

        rc = self.roomCache[action.deviceId]

        device = indigo.devices[action.deviceId]
        self.automationLog(f"Toggling occupancy for device: {device.name}")

        current = rc.get(
            "occupied",
            0)
        
        next = not current
        self.setOccupancy(device, next)

    def setOccupancy(self, room, newState):
        # this one is invoked by occupancy sensations, occuoancy cutoff expiration, or manual intervention
        # IMPORTANT - THIS IS THE PRIMARY INITIATOR OF AUTOMATED LIGHTING CHANGES
        rc = self.roomCache[room.id]

        room.updateStateOnServer("occupied", newState)

        oldState = rc.get(
            "occupied",
            False)
        rc["occupied"] = newState
        stateChange = ( newState != oldState)

        if stateChange:
            self.automationLog(f"Occupancy state for {room.name} changing from {oldState} to {newState}")
            if newState == True:
                # occupancy turned on
                self.setOccupancyExpiry(room)
                if self.automationsActionable(room):
                    self.autoRoomBrightness(room,"initial")
            else:
                # occupancy turned off
                self.clearOccupancyExpiry(room)
                self.clearNextObligation(room)
                if self.automationsActionable(room):
                    self.turnRoomOff(room)
                else:
                    if not self.isOn(room):
                        self.roomJustTurnedOff(room)
#                        rc["automationsAuthorized"] = True
#                        room.updateStateOnServer("automationsAuthorized",True)
#                        self.evaluateAutomationState(room)

        else:
            # state reasserted
            if newState == True:
                self.setOccupancyExpiry(room)
                # targetBrightness = room.pluginProps.get("initialBrightness") 
                if self.automationsActionable(room):
                    self.automationLog(f"Re-asserting {newState} occupancy state for {room.name}")
                    self.autoRoomBrightness(room,"initial")

        self.identifyNextRoomObligation(room)


    def setOccupancyExpiry(self, room):
        # this section just got complicated, because we have sifferent pluginProps to consider
        # and multiple *expiration* timestamps to calculate and store for use in the heartbeat
        #
        # initialTimeout 



        rc = self.roomCache[room.id]

        totalMinutes = float(0)

        initialTimeout = float(room.pluginProps.get("initialTimeout", self.globalGrace  ))

#        transitionEnabled = bool(room.pluginProps.get("transitionEnabled", False  ))
#        outroEnabled = bool(room.pluginProps.get("outroEnabled", False  ))

        transitionEnabled = self.globalPhasedLightingEnabled
        outroEnabled = self.globalPhasedLightingEnabled


        delayedMinutes = 0

        if transitionEnabled:
            initialTimeout = float(room.pluginProps.get("initialTimeout", 5  ))
#            totalMinutes = initialTimeout+delayedMinutes+outroMinutes
            transitionTime = time.time() + (initialTimeout * 60)
            transitionTimeUI = datetime.datetime.fromtimestamp(transitionTime).strftime("%I:%M:%S %p")
            self.scheduleRoomEvaluation(room, transitionTime, room.name, "Transition")

        else:
            delayedMinutes = 0
            transitionTime = 0
            transitionTimeUI = ""
#            totalMinutes = initialTimeout

        if outroEnabled == True:
            initialTimeout = float(room.pluginProps.get("initialTimeout", 5  ))
            delayedMinutes = float(room.pluginProps.get("delayedMinutes", 5  ))
            outroMinutes = float(room.pluginProps.get("outroMinutes", 2  ))
            outroTime = time.time() + ((initialTimeout + delayedMinutes) * 60) 
            outroTimeUI = datetime.datetime.fromtimestamp(outroTime).strftime("%I:%M:%S %p")
        else:
            outroMinutes = 0
            outroTime = 0
            outroTimeUI = ""

        totalMinutes = float(initialTimeout+delayedMinutes+outroMinutes)
        

        expiry = time.time() + (totalMinutes * 60)
        displayTime = datetime.datetime.fromtimestamp(
            expiry).strftime("%I:%M:%S %p")
        
        rc["occupied"] = True

        room.updateStatesOnServer([
            {"key": "occupied", "value": True},
            {"key": "occupancyCutoff", "value": expiry},
            {"key": "occupancyCutoffUI", "value": displayTime},
            {"key": "delayedLightingStarttime", "value": transitionTime},
            {"key": "outroLightingStarttime", "value": outroTime},
            {"key": "delayedLightingStarttimeUI", "value": transitionTimeUI},
            {"key": "outroLightingStarttimeUI", "value": outroTimeUI},
        ])

        

    def clearOccupancyExpiry(self, room):

        rc = self.roomCache[room.id]
        rc["occupied"] = False

        room.updateStatesOnServer([
            {"key": "occupied", "value": False},
            {"key": "occupancyCutoff", "value": None},
            {"key": "occupancyCutoffUI", "value": None},
            {"key": "delayedLightingStarttime", "value": None},
            {"key": "outroLightingStarttime", "value": None},
            {"key": "delayedLightingStarttimeUI", "value": None},
            {"key": "outroLightingStarttimeUI", "value": None},
        ])


    # ---------------------------------------------------------
    # 
    # ROOMIFY PLUGIN & MANAGER METHODS UP FRONT
    #     
    # ---------------------------------------------------------


    # runs when plugin loads. good for initializing variables, loading prefs, etc. but not for doing anything with devices since they might not be loaded yet (that's deviceStartComm)
    def startup(self):
        self.initialized = False
        self.suspendCrosstalk = False

        # K = factor that determines if new repors constitute new conversations
        self.K = 2

        self.nextEvaluationDue = None

        self.houseMode = ""

        #self.logger.info(indigo.dimmer.setBrightness.__doc__)
        self.roomRuntime = {}

        self.roomCache = {}
        self.buildRoomCache()

        self.buildRoomTypeDefaults()
        self.recentlyControlled = {}
        self.canonical = {}
        self.lastnoise = {}
        self.lastcommand = {}
        self.lastsense = {}
        self.lastreport = {}
        self.traceCache = {}
        self.loadPluginPrefs()

        self.debugLog("[DEBUG]Roomify plugin starting")

#        self.houseMode = self.pluginPrefs.get("houseMode", "DAY")
        
        indigo.devices.subscribeToChanges()
        self.suppressEvaluationDepth = 0
        self.devicesBeingControlled = set()
        self.buildDeviceRoomIndex() #also build roomm cache ?
        self.buildIndicatorRoomIndex()
        self.buildVacancyAuthorityRoomIndex()
        self.buildGateRoomIndex()

        self.refreshObservers()

        self.initializeHouseMode()
        self.publishToAllObservers()
        self.initialized = True

    def shutdown(self):
        self.debugLog("Roomify plugin shutting down")
        self.initialized = False
#        indigo.devices.unsubscribeFromChanges()
        self.automationLog("Roomify plugin shutdown complete")

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):

        # If user hit Cancel, do nothing
        if userCancelled:
            return

        # Get the updated device
        if typeId == "roomifyRoom":
            self.configStable = False
            self.configChangedDeviceId = devId


    def reInitRoom(self, devId):
        dev = indigo.devices[devId]
        self.buildDeviceRoomIndex()
        self.buildIndicatorRoomIndex()
        self.buildVacancyAuthorityRoomIndex()
        self.buildGateRoomIndex()
        self.initializeRoom(dev)
        self.recomputeRoom(dev)
        if dev.deviceTypeId == "roomifyRoom":
            self.configChangedDeviceId = None
            self.configStable = True        

    def closedConfigUi(self, valuesDict, userCancelled, typeId, devId):
        if userCancelled:
            return
        
        self.buildDeviceRoomIndex()
        self.buildIndicatorRoomIndex()
        self.buildVacancyAuthorityRoomIndex()
        self.buildGateRoomIndex()

        if typeId in [ "Room", "roomifyRoom" ]:
            device = indigo.devices[devId]
            self.initializeRoom(device)

#CZEWSKI delete this manager stuff

        if typeId in [ "Manager", "roomifyManager"]:
            device = indigo.devices[devId]
            self.initializemanager(device)


    # invoked by startup(self) at plugin initialization, 
    # and also meant ot be invoked  by closedPrefsConfigUi(self, valuesDict, userCancelled) when the user saves changes to the plugin configuration. good for loading prefs into variables that can be used throughout the plugin.
    def loadPluginPrefs(self):
        self.configStable = True
        self.configChangedDeviceId = None

        self.globalGrace = int(self.pluginPrefs.get("vacancyGracePeriod", 5))
        self.globalResetEnabled = self.pluginPrefs.get("periodicResetAuthorized", False)
        self.globalResetTime = self.pluginPrefs.get("resetTime", "03:00:00")

        self.globalOccupancyAutomationEnabled = self.pluginPrefs.get("occupancyAutomationEnabled", False)
        self.globalAuthorityAutoStandbyRecovery = self.pluginPrefs.get("authorityAutoStandbyRecovery", True)

        self.globalRoomDormancyCutoffEnabled = self.pluginPrefs.get("roomDormancyCutoffEnabled", False)
        self.globalRoomDormancyDefault = self.pluginPrefs.get("roomDormancyCutoffDefault", 360)
        self.globalPhasedLightingEnabled = self.pluginPrefs.get("phasedLightingEnabled", False)
        self.globalRemediationEnabled = self.pluginPrefs.get("remediationEnabled", True)
        self.globalRoomAutomationCalmingPeriod = float(self.pluginPrefs.get("roomAutomationCalmingPeriod",5))
        self.globalHouseModesEnabled = self.pluginPrefs.get("houseModesEnabled", False)

        self.guardrailsEnabled = self.pluginPrefs.get("guardrailsEnabled", False)
        self.defaultVacantRoomMinBrightness = self.pluginPrefs.get("defaultVacantRoomMinBrightness", False)
        self.defaultOccupiedRoomMinBrightness = self.pluginPrefs.get("defaultOccupiedRoomMinBrightness", False)
        self.defaultOccupiedRoomMaxBrightness = self.pluginPrefs.get("defaultOccupiedRoomMaxBrightness", False)

        self.loggingEnabled = self.pluginPrefs.get("loggingEnabled", True)

        self.verboseLogging = self.pluginPrefs.get(
            "verboseLogging", True)

        self.heartbeatLogging = self.pluginPrefs.get(
            "heartbeatLogging", False)

        self.deviceEventLogging = self.pluginPrefs.get(
            "deviceEventLogging", True)

        self.automationDecisionLogging = self.pluginPrefs.get(
            "automationDecisionLogging", True)

        self.authorityDecisionLogging = self.pluginPrefs.get(
            "authorityDecisionLogging", True)

        self.errorLogging = self.pluginPrefs.get(
            "errorLogging", True)
        
        self.securifyPlugin = indigo.server.getPlugin("com.searchcz.securify")
        self.securifyCooperationEnabled = self.pluginPrefs.get("securifyCooperationEnabled", False)

 
        self.automationLog(f"Globally Authorized Timeouts={self.globalRoomDormancyCutoffEnabled}")
        self.automationLog(f"Globally Authorized Default={self.globalRoomDormancyDefault}")
        self.automationLog(f"Globally Occupancy Automations={self.globalOccupancyAutomationEnabled}")
        self.automationLog(f"Globally Phased Lighting={self.globalPhasedLightingEnabled}")

    def initializeHouseMode(self):
        x = False
        if self.securifyCooperationEnabled:
            x = self.requestHouseMode(self)
        if not x:
            self.setHouseMode(self.pluginPrefs.get("houseMode"))

 
    def toggleDormancyCutoff(self, action):
        self.globalRoomDormancyCutoffEnabled = not ( self.pluginPrefs.get("roomDormancyCutoffEnabled", False) )
        self.pluginPrefs["roomDormancyCutoffEnabled"] = self.globalRoomDormancyCutoffEnabled
        self.recomputeAllRooms()
        self.publishToAllObservers()

    def toggleOccupancyAutomation(self, action):
        self.globalOccupancyAutomationEnabled = not ( self.pluginPrefs.get("occupancyAutomationEnabled", False) )
        self.pluginPrefs["occupancyAutomationEnabled"] = self.globalOccupancyAutomationEnabled
        self.recomputeAllRooms()
        self.publishToAllObservers()  

#CZEWSKI delete this manager stuff

    def initializemanager(self, device):

#        if device.typeId == "Manager":
#            indigo.device.replaceDeviceTypeId("roomifyManager")

        return

#        self.occupancyAutomationEnabled = device.pluginProps.get(
#            "occupancyAutomationEnabled", True)

#        self.roomDormancyCutoffEnabled = device.pluginProps.get(
#            "roomDormancyCutoffEnabled", True)

#        device.updateStateOnServer(
#            "occupancyAutomationEnabled",
#            self.occupancyAutomationEnabled)

#        device.updateStateOnServer(
#            "roomDormancyCutoffEnabled",
#            self.roomDormancyCutoffEnabled)

#        self.deviceLog(
#            f"{device.name} runtime manager initialized")


    # ---------------------------------------------------------
    # 
    # ROOMIFY SHARED/OVERLAPPED METHODS NEXT
    #     
    # ---------------------------------------------------------
    def isOn(self, dev):

        if dev.deviceTypeId == "roomifyRoom":
            return self.roomIsOn(dev.id)
        else:
            return self.deviceIsOn(dev)


    def roomIsOn(self, roomId):
        rc = self.roomCache[roomId]
        room_onState = ( rc.get("totalBrightness", 0) > 0 )
        return room_onState


    def deviceIsOn(self, device):

        return device.states.get("onOffState", False)



    def depricatedRoomIsOnTests(self, dev):
        try:


            # Most reliable Indigo state


            if dev.states.get("onOffState", False):
                return True

            # Dimmer devices that may not expose onOffState properly
            if dev.states.get("brightness", 0) > 0:
                return True

            # Fallback attributes for odd/custom devices
            if getattr(dev, "onState", False):
                return True

            if getattr(dev, "brightnessLevel", 0) > 0:
                return True

        except Exception as err:
            self.logger.debug(
                f"isOn failed for device "
                f"'{getattr(dev, 'name', 'Unknown')}': {err}"
            )

        return False

    
    # re: enabliong automation     
    def activateRoomAutomations(self, action):

        self.roomCache[action.deviceId]["roomOccupancyAutomationActive"] = True

        device = indigo.devices[action.deviceId]


        device.updateStateOnServer(
            "roomOccupancyAutomationActive",
            True)

        self.evaluateAutomationState(device)

        self.automationLog(
            f"{device.name} room occupancy automations resumed")
        
    def deactivateRoomAutomations(self, action):

        self.roomCache[action.deviceId]["roomOccupancyAutomationActive"] = False

        device = indigo.devices[action.deviceId]

        device.updateStateOnServer(
            "roomOccupancyAutomationActive",
            False)

        self.evaluateAutomationState(device)

        self.automationLog(
            f"{device.name} room occupancy automations suspended")
        
    def toggleRoomAutomations(self, action):
        device = indigo.devices[action.deviceId]
        self.automationLog(f"Toggling room occupancy automations for device: {device.name}")

        current = device.states.get(
            "roomOccupancyAutomationActive",
            True)

        newValue = not current

        self.roomCache[action.deviceId]["roomOccupancyAutomationActive"] = newValue


        device.updateStateOnServer(
            "roomOccupancyAutomationActive",
            newValue)

        #self.occupancyAutomationEnabled = False

        self.evaluateAutomationState(device)

        self.automationLog(
            f"{device.name} room occupancy automations toggled to {newValue}")
        
    # re: enabliong timeouts     
    def enableTimeouts(self, action):

        device = indigo.devices[action.deviceId]

        device.updateStateOnServer(
            "roomDormancyCutoffActive",
            True)


        self.evaluateAutomationState(device)

        self.automationLog(
            f"{device.name} timeouts applied")
        
    def disableTimeouts(self, action):

        device = indigo.devices[action.deviceId]

        device.updateStateOnServer(
            "roomDormancyCutoffActive",
            False)

  
        self.evaluateAutomationState(device)

        self.automationLog(
            f"{device.name} timeouts disabled")
        
    def toggleTimeouts(self, action):

        device = indigo.devices[action.deviceId]
        self.automationLog(f"Toggling timeouts for device: {device.name}")


        current = device.states.get(
            "roomDormancyCutoffActive",
            True)

        newValue = not current

        device.updateStateOnServer(
            "roomDormancyCutoffActive",
            newValue)


        self.evaluateAutomationState(device)

        self.automationLog(
            f"{device.name} roomDormancyCutoffActive toggled to {newValue}")

    def grantAutomationAuthority(self, action):

        rc = self.roomCache[device.id]
        rc["automationsAuthorized"] = True

        device = indigo.devices[action.deviceId]

        device.updateStateOnServer(
            "automationsAuthorized",
            True)


        self.evaluateAutomationState(device)

        self.authorityLog(
            f"{device.name} automation authority granted")
        
        self.evaluateAutomationState(action)

    def revokeAAU(self, device):
        self.logDecision(device,"Revoking automation authority for device {room.name}")
        rc = self.roomCache[device.id]
        rc["automationsAuthorized"] = False

        device.updateStateOnServer(
            "automationsAuthorized",
            False)

        self.evaluateAutomationState(device)

        self.authorityLog(
            f"{device.name} automation authority revoked")
        


        
    def revokeAutomationAuthority(self, action):

        device = indigo.devices[action.deviceId]

        self.revokeAAU(device)
#        self.evaluateAutomationState(action)



    def advanceAutomationStatusX(self, action):
        rc = self.roomCache[action.deviceId]

        aaPrior = rc.get("automationsAuthorized")
        roaaPrior = rc.get("roomAutomationActive")

        aa = aaPrior
        roaa = roaaPrior    

        device = indigo.devices[action.deviceId]
        self.authorityLog(f"Advancing automation status for device: {device.name}")

        current = rc.get(
            "automationState",
            0)
        
        next = int(current) + 1

        if next == 3:
            next = int(0)

        if next == 0:
            roaa = True
            aa = False
            self.recordTransferOfAuthority(device, aaPrior, aa, "INTENTION: User Set to Standby")
        elif next == 1:
            roaa = True
            aa = True
            self.recordTransferOfAuthority(device, aaPrior, aa, "INTENTION: User Set to Active")
        elif next == 2:
            roaa = False
            aa = False
            self.recordTransferOfAuthority(device, aaPrior, aa, "INTENTION: User Set to Inactive")
            
        rc["roomOccupancyAutomationActive"] = roaa
        rc["automationsAuthorized"] = aa

        device.updateStatesOnServer([
            {"key": "roomOccupancyAutomationActive", "value": roaa},
            {"key": "automationsAuthorized", "value": aa},
        ])

        self.evaluateAutomationState(device)

    def toggleAutomationAuthority(self, action):

        rc = self.roomCache[action.deviceId]

        device = indigo.devices[action.deviceId]
        self.authorityLog(f"Toggling automation authority for device: {device.name}")

        current = device.states.get(
            "automationsAuthorized",
            True)

        newValue = not current
        rc["automationsAuthorized"] = newValue

        device.updateStateOnServer(
            "automationsAuthorized",
            newValue)

        if newValue:
            self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), False, "INTENTION: User Toggled into Standby")
        else:
            self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), True, "INTENTION: User Toggled into Active")
        

        self.evaluateAutomationState(device)

        self.deviceLog(
            f"{device.name} automation authority toggled to {newValue}")
        
        self.evaluateAutomationState(device)

    

    def closedPrefsConfigUi(self, valuesDict, userCancelled):

        if not userCancelled:
            self.logger.info("Plugin preferences updated")            

            self.loadPluginPrefs()

            createObserver = self.pluginPrefs.get("createObserver", False)

            rawId = self.pluginPrefs.get("observerId")

            observerId = int(rawId or 0)

            self.debugLog(f"createObserver={createObserver}, observerId={observerId}")

            if createObserver and observerId == 0:

                observerName = self.pluginPrefs.get("observerName", "Roomify Observer")
                self.debugLog(f"Creating Observer {observerName}")
                newDevice = indigo.device.create(indigo.kProtocol.Plugin, address=None, name=observerName, deviceTypeId="roomifyObserver", props=None, folder=None)
                self.debugLog(f"New Obser4ver Device ID:{newDevice.id}")
                self.pluginPrefs["observerId"] = newDevice.id

            self.recomputeAllRooms()
            self.publishToAllObservers()

#            self.logger.info("Plugin preferences reloaded")            

    def debugLog(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if self.loggingEnabled and self.verboseLogging:
            self.logger.info("@" + formatted + ": " + message)


    def heartbeatLog(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.heartbeatLogging:
            self.logger.info("@" + formatted + ": " + message)


    def deviceLog(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.deviceEventLogging:
            self.logger.info("@" + formatted + ": " + message)


    def authorityLog(self,message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.authorityDecisionLogging:
            self.logger.info("AUTHORITY DECISION @" + formatted + ": " + message)

    def automationLog(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.automationDecisionLogging:
            self.logger.info("@" + formatted + ": " + message)


    def errorLog(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.errorLogging:
            self.logger.info("@" + formatted + ": " + message)

    def deviceStartComm(self, device):
        device.stateListOrDisplayStateIdChanged()
        self.debugLog(
            f"[Roomify DEBUG] starting device: {device.name}")

        device.stateListOrDisplayStateIdChanged()

        if device.deviceTypeId in [ "Room", "roomifyRoom" ]:
            self.initializeRoom(device)
        
    def deviceDeleted(self, dev):
        self.logger.info(
           f"[Roomify DEBUG] DEVICE DELETED: {dev.id} {dev.name}"
        )
        if dev.id in self.roomCache:
            self.logger.info(
                f"[Roomify DEBUG] removing deleted room from cache: {dev.name}"
            )
            del self.roomCache[dev.id]



    def logDecision(self, device, message):

        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))
        self.automationLog(f"AUTHORITY DECISION@{formatted}: {device.name}: {message}")


    # ---------------------------------------------------------
    # 
    # ROOMIFY ROOM METHODS NEXT
    #     
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # 1: ACTION: ALL ABOUT OCCUPANCY STATE
    # ---------------------------------------------------------
    
    def ignoreNextRoomChange(self, room, reason="unknown", onState=None, brightness=None):

        self.automationLog(f"Ignoring next room state change for room: {room.name}")

        self.suppressDev(room.id, "roomify iniitated", None, None)

        controlled_ids = room.pluginProps.get("controlledDevices") or []
        controlled_ids = [int(x) for x in controlled_ids]

#       NECESSARY before issuing any kind f change from Roomify
        for dev_id in controlled_ids:
            self.suppressDev(dev_id, reason, onState, brightness)

    def suppressDev(self, devId, reason="unknown", onState=None, brightness=None):
        #i dont think supression is part of the game anymore?
        return
        #seems this gets called per device

        self.deviceLog(f"Suppressing device update detection for device id: {devId} for {self.globalRoomAutomationCalmingPeriod} seconds.")
        self.deviceLog(f"Recording onState={onState}, intended brightness={brightness}")

        #- how many seconds are you allowing for the automated transition ? thats now + x
        #CZEWSKI
        now = time.time()
        self.recentlyControlled[devId] = {
            "expires": now + self.globalRoomAutomationCalmingPeriod,
            "deviceId": devId,
            "source": "Roomify",
            "reason": reason,
            "intendedOnState": onState,
            "intendedBrightness": brightness,
            "cmdId": str(uuid.uuid4())
        }

        record = self.recentlyControlled[devId]
#        self.dumpDict("Suppression Record Created",record)

    def dumpDict(self, title, d):

        if not (self.verboseLogging):
            return
        
        indigo.server.log(f"=== {title} ===")

        for key, value in d.items():
            indigo.server.log(f"{key}: {value}")

        indigo.server.log("================")


    def isDivergent(self, device, room_on, room_brightness):
        # Deprecated.
        # Conversation tracing provides a more complete model of device behavior.
        # Temporarily disabled while evaluating the trace-based architecture.
        return False
        device_on = self.isOn(device)

        if self.isDimmable(device):
            device_brightness = device.states.get("brightnessLevel")
            if (abs(room_brightness - device_brightness) > 2 ) or (room_on != device_on):
                return True
            else:
                return False
        else:
            return room_on != device_on
        

    def logDisruption(self, device):
        record = self.recentlyControlled.get(device.id)
#        self.dumpDict("Recently Controlled", record)

        if device.deviceTypeId in [ "roomifyObserver","roomifyRoom"]:
            return

        # No Roomify intent exists
        # therefore cannot be disrupted
        if not record:
            return True

        intendedOn = record.get("intendedOnState")
        expires = record.get("expires")

        actualOn = device.states.get("onOffState", False)
        now = time.time()
        

        disrupted = False

        if self.isDimmable(device):
            intendedBrightness = record.get("intendedBrightness")
            actualBrightness = device.states.get("brightnessLevel", 0)
            if abs (actualBrightness - intendedBrightness) > 2:
                self.authorityLog (f"{device.name} : [{device.id}]Intended brightness={intendedBrightness} / actual={actualBrightness}")
                disrupted = True

        if  actualOn != intendedOn:
            disrupted = True
            self.authorityLog (f"{device.name} : [{device.id}]Intended On={intendedOn} / actual={actualOn   }")

        #LATENCY ?

        return disrupted


    def isDisrupted(self, device):
        return False

        record = self.recentlyControlled.get(device.id)
#        self.dumpDict("Recently Controlled", record)

        if device.deviceTypeId in [ "roomifyObserver","roomifyRoom"]:
            return

        # No Roomify intent exists
        # therefore cannot be disrupted
        if not record:
            return True

        intendedOn = record.get("intendedOnState")
        expires = record.get("expires")

        actualOn = device.states.get("onOffState", False)
        now = time.time()
        

        disrupted = False

        if self.isDimmable(device):
            intendedBrightness = record.get("intendedBrightness")
            actualBrightness = device.states.get("brightnessLevel", 0)
            if abs (actualBrightness - intendedBrightness) > 2:
                self.authorityLog (f"DISRUPTION: {device.name} [{device.id}]Intended on={intendedOn} brightness={intendedBrightness}")
                disrupted = True

        if  actualOn != intendedOn:
            disrupted = True

        # Disruption ?
        if disrupted:
            self.authorityLog (f"DISRUPTION: Device {device.name} [{device.id}] in an apparent disruptive state")

        return disrupted

    def isSuppressed(self, devId):
        return False
        #temporary supression of supression
        ctx = self.recentlyControlled.get(devId)
        if ctx and time.time() < ctx["expires"]:
            #self.sumpDict(ctx)
            return True



    def extendSuppression(self, devId, additionalSeconds=None):

        if devId not in self.recentlyControlled:
            return False

        if additionalSeconds is None:
            additionalSeconds = self.globalRoomAutomationCalmingPeriod

        additionalSeconds = float(additionalSeconds)

        self.recentlyControlled[devId]["expires"] = time.time() + additionalSeconds

        self.debugLog(
            f"Extended suppression for device {devId} until "
            f"{self.recentlyControlled[devId]['expires']}"
        )

        return True

    def initializeRoomBrightnessState(self, key, device):
        #IN USE
        # 1. Validate device type
        if device.deviceTypeId not in ["Room", "roomifyRoom" ]:
            self.debugLog("Ignored: not a Room  device (%s)" % device.name)
            return False

        value = device.pluginProps.get(f"{key}Brightness", 0)
        self.debugLog(f"Room {device.name} {key}Brightness setting is {value}")

       # 5. Sanitize value
        try:
            value = int(value)
        except:
            self.errorLog("Invalid brightness value: %s" % value)
            return False

        # 6. Clamp (optional but recommended)
        value = max(0, min(100, value))

        # 7. Update runtime state

        try:
            value = int(value)
        except:
            value = 0

        device.updateStateOnServer(f"{key}Brightness", value)
        #self.debugLog(
        #    f"{device.name} {key}Brightness set to {value}"
        #)


    def setRoominitialBrightnessDeprecated(self, device, value):

        rc = self.roomCache[device.id]

        # 1. Validate device type
        if device.deviceTypeId not in [ "Room", "roomifyRoom" ]:
            self.debugLog("Ignored: not a Room  device (%s)" % device.name)
            return False

        # 2. Global automation gate
        if not self.globalOccupancyAutomationEnabled:
            self.automationLog("Global automations disabled")
            return False

        # 3. Local device automation flag (pluginProps)
        #props = device.pluginProps
        #if not props.get("roomOccupancyAutomationActive", "true") == "true":
        #    self.automationLog("Device automations disabled: %s" % device.name)
        #    return False
        if not rc.get("roomOccupancyAutomationActive", True):
            self.automationLog("Device automations disabled: %s" % rc.get["name"])
            return False

        # 4. Authorization check
        #if not props.get("automationsAuthorized", "false") == "true":
        #    self.automationLog("Device automations not authorized: %s" % device.name)
        #    return False

        if not rc.get("automationsAuthorized", True):
            self.automationLog("Device automations not authorized: %s" % device.name)
            return False

        # 5. Sanitize value
        try:
            value = int(value)
        except:
            self.errorLog("Invalid brightness value: %s" % value)
            return False

        # 6. Clamp (optional but recommended)
        value = max(0, min(100, value))

        # 7. Update runtime state
        device.updateStateOnServer("initialBrightness", value)

        self.automationLog(
            f"{device.name} initialBrightness set to {value}"
        )



        return True


    def setinitialBrightnessActionDeprecated(self, pluginAction, device):

        try:
            value = int(pluginAction.props.get("initialBrightness", 0))

            device.updateStateOnServer("initialBrightness", value)

            self.deviceLog(f"{device.name} initialBrightness = {value}")

            return True

        except Exception as e:
            self.errorLog(f"setinitialBrightnessAction failed: {e}")
            return False

    def setBrightnessForDevice(self, device, value):

        value = int(value)
        device.updateStateOnServer("brightness", value)

        self.deviceLog(f"{device.name} brightness = {value}")


    def setBrightness(self, pluginAction, device):

        value = pluginAction.props.get("value", 0)
        self.setBrightnessForDevice(device, value)
        self.deviceLog(f"{device.name} brightness = {value}")


    # code to run every time a device updates (e.g. on/off or brightness change)
    # but be car4eful because 
    # to make sure those changes are reflected in the room device states
    # very important! this plugin MUST add devices into the
    # devicesBeingControlled prior to making any changes to device states, otherwise it will create an infinite loop of updates

    
    def deviceUpdated(self, origDev, newDev):

        # the DEVICE UPDATED might be a sensor. if the sensor is part of a room, then we need to evaluate the room state to determine if we need to change the lighting state. if we do need to change the lighting state, then we need to add the room device into the devicesBeingControlled set prior to making any changes to the room device states, otherwise we will create an infinite loop of updates.
        # self.debugLog(f"deviceUpdated: {newDev.name} (id: {newDev.id})")

        #if newDev.id == 593181165:
        #    self.deviceLog(f"Device update received for {newDev.name} (id: {newDev.id})")
        #    self.deviceLog(f"Prior state (onState: {getattr(origDev, 'onState', 'N/A')}, brightness: {getattr(origDev, 'brightness', 'N/A')})")
        #    self.deviceLog(f"New state (onState: {getattr(newDev, 'onState', 'N/A')}, brightness: {getattr(newDev, 'brightness', 'N/A')})")

        if origDev.pluginProps != newDev.pluginProps:

            self.debugLog(
                f"[Roomify DEBUG] config updated: {newDev.name}")

            if newDev.deviceTypeId in ["Manager", "roomifyManager"]:
                self.initializemanager(newDev)

            elif newDev.deviceTypeId in ["Room","roomifyRoom"]:
                self.initializeRoom(newDev)




        is_indicator = newDev.id in self.indicatorRoomMap
        is_controlled = newDev.id in self.deviceRoomMap
        is_gate = newDev.id in self.gateRoomMap

        is_vacancyAuthority = newDev.id in self.vacancyAuthorityRoomMap

        if not ( is_indicator or is_controlled or is_gate or is_vacancyAuthority ):
            return


        # FIRST FILTER - is this state report any different from the previous state report
        previous = self.lastreport.get(newDev.id, {})

        new_on_report = getattr(newDev, "onState", None)
        old_on_report = getattr(origDev, "onState", None)
        isDimmable = self.isDimmable(newDev)

        if isDimmable:
            new_brightness_report = getattr(newDev, "brightness", 0)
            old_brightness_report = getattr(origDev, "brightness", 0)
        else:
            if new_on_report:
                new_brightness_report = 100
            else:
                new_brightness_report = 0   

            if old_on_report:
                old_brightness_report = 100
            else:
                old_brightness_report = 0            

        if old_brightness_report is None:
            old_brightness_report = 0

        on_change_reported = (new_on_report != old_on_report)


        brightness_changed = False
        if new_brightness_report is not None and old_brightness_report is not None:
            brightness_changed = abs(new_brightness_report - old_brightness_report) > 0

        report_changed = on_change_reported or brightness_changed

        if not report_changed:
#            self.debugLog(f"Ignoring redundant report from {newDev.name} of ON={new_on_report} and brightness={new_brightness_report}")
            if is_controlled:
                self.recordDeviceReportX(newDev, newDev.onState, getattr(newDev, "brightness", None))
#                self.recordDeviceReport(newDev, newDev.onState, getattr(newDev, "brightness", None))
            return  # 🚫 pure duplicate noise, ignore completely
        
        #czewski
        self.deviceLog(f"Processing fresh report from {newDev.name}  of ON={new_on_report} and brightness={new_brightness_report}")

        #to quite the noise of repeated device reports, record this one
        if is_controlled:
            state = self.lastreport.get(newDev.id, {})
            now = time.time()
            lastUpdate = state.get("lastUpdate", now)
            timeDelta = time.time() - lastUpdate

#            self.recordDeviceReport(newDev, newDev.onState, getattr(newDev, "brightness", None))

            # at this poiint we have change reoported by a controlled device
            # maybe roomify caused it. maybe something else caused it
            # but our only business at this point is to update the deived brightnes sin the affected rooms
            affected_rooms = self.deviceRoomMap.get(newDev.id, [])
            for room_id in affected_rooms:

                rc = self.roomCache[room_id]
                deviceCount = rc["deviceCount"]

                oldDerivedBrightness = (
                    rc["totalBrightness"] / deviceCount
                )

                rc["totalBrightness"] -= old_brightness_report
                rc["totalBrightness"] += new_brightness_report

                derivedBrightness = rc["totalBrightness"] / deviceCount

                publishedBrightness = int(round(derivedBrightness))

                room = indigo.devices[room_id]
                room.updateStateOnServer("brightness", publishedBrightness)
                room.updateStateOnServer("brightnessLevel", publishedBrightness)
                #self.automationLog(f"Brightness in {room.name} changing from {oldDerivedBrightness} to {publishedBrightness}")

                #classify and cache this report into the rooomCache
                expectedBrightness = rc["roomifyIntent1"]

#                aa = str(rc["automationsAuthorized"])
#                deviceAlignedWithCurrentIntent = self.isAligned(rc["roomifyIntent1"],new_brightness_report,isDimmable)
#                deviceAlignedWithPriorIntent = self.isAligned(rc["roomifyIntent2"],new_brightness_report,isDimmable)
#                deviceAlignedWithPenultimateIntent = self.isAligned(rc["roomifyIntent3"],new_brightness_report,isDimmable)
                                                                                
                deviceReports = rc["deviceReports"]
                dr = deviceReports.get(newDev.id)

                if dr is None:
                    rc["devicesReporting"] += 1
                    dr = {}
                    dr["retryCount"] = 0
                    deviceReports[newDev.id] = dr

                alignment = None
                i = rc["roomifyIntent1"]
                if i is not None:
                    if self.isAligned(i,new_brightness_report,isDimmable):
                        alignment = "intended"

                if alignment == None:
                    i = rc["roomifyIntent2"]
                    if i is not None:
                        if self.isAligned(i,new_brightness_report,isDimmable):
                            alignment = "prior"

                if alignment == None:
                    i = rc["roomifyIntent3"]
                    if i is not None:
                        if self.isAligned(i,new_brightness_report,isDimmable):
                            alignment = "penultimate"

                if alignment == None:
                    alignment = "novel"

                authorityImpact = ""
                devAlignment = alignment

#                self.logger.info(f"Device {newDev.name} reported brightness={new_brightness_report} alignment={alignment} timeDelta={timeDelta}")

                dr["alignment"] = alignment
                dr["timeDelta"] = timeDelta

                i = rc["roomifyIntent1"]

                #reclaim and surrendeer here?
                if self.globalAuthorityAutoStandbyRecovery:
                    self.authorityLog(f"aa={rc['automationsAuthorized']} intent={i} {newDev.name} brightnes={new_brightness_report} dimmable={isDimmable} alignment={alignment}")
                    #deferred room reaches Roomify intended brightness = reclaim authority
                    if rc["automationsAuthorized"] == False and ( rc["totalBrightness"] == rc["alignmentTarget"] ):
                        self.authorityLog(f"Room '{room.name}' matches Roomify expectations: resuming automation authority.")
                        self.recordTransferOfAuthority(room, rc.get("automationsAuthorized"), True, "DISRUPTION ENDED : Room entered alignment state")
                        rc["automationsAuthorized"] = True
                        authorityImpact = "Reclaimed"
                        room.updateStateOnServer("automationsAuthorized", True) 
                    elif rc["automationsAuthorized"] == True and ( alignment != "intended"): 
                        #device is not in the state roomify intended
                        #we (may) need to ascertain the response window for the reporting device
                        cache = self.traceCache[newDev.id]

                        responseWindow = 15
                        if cache["initialLatency"] != None:
                            responseWindow = (cache["latencyTotal"] / cache["latencyCount"]) * self.K
                        else:
                            responseWindow = 15

                        #device does not match intent, so defer the room

                        self.authorityLog(f"Device {newDev.name} does not match Roomify intent. Deferring room {rc["name"]}")
                        self.recordTransferOfAuthority(room, rc.get("automationsAuthorized"), False, f"{newDev.name} disrupted {rc["name"]}")
                        rc["automationsAuthorized"] = False
                        authorityImpact = "Deferred"
                        room.updateStateOnServer("automationsAuthorized", False) 

                        # but if non-compliance is suspected, flag the room for authority review
                        if ( alignment != "novel" ) and ( timeDelta < responseWindow ):

                            self.authorityLog(
                                f"Authority review requested for '{room.name}': "
                                f"device={newDev.name}, alignment={alignment}, "
                                f"timeDelta={timeDelta:.2f}s, responseWindow={responseWindow:.2f}s, "
                                f"initialLatency={cache['initialLatency']}, "
                                f"automationsAuthorized={rc['automationsAuthorized']}"
                            )

                            rc["authorityReviewPending"] = True
                            nextTime = time.time()+90
                            nextName = "Authority Review"
                            self.scheduleRoomEvaluation(room, nextTime, nextName, "Potential Non-Compliance")

                            self.authorityLog(f"Room '{room.name}' flagged for authority review due to non-compliance")
                            
                if rc["totalBrightness"] == 0:
                    self.roomJustTurnedOff(room)

        #if is_gate:
        #    self.debugLog(f"Device {newDev.name} is a gate device, evaluating gate state")
        #    self.evaluateAutomationState(newDev)
        #    return

#CZEWSKI - NO NEED TO SUPPRESS EVALUATION OF DEVICE STATE CHANGES ANYMORE
# BECAUSE WE HAVE A RECORD OF ROOMIFYS INTENT AND CAN DETECT DIVERGENCE FROM THAT 
        if self.isSuppressed(newDev.id):
#            # suppress it again ... this extends the window of presumption that the state change is due to roomify
            self.authorityLog(f"Ignoring suppressed report from {newDev.name}")
#            self.extendSuppression(newDev.id, 5)
            return

#        if getattr(self, "suppressEvaluationDepth", 0) > 0:
#            return
        
        try:
            changed = False
            changedAspect = ""


            # ---- ON/OFF check (safe) ----
            if old_on_report != new_on_report:
                changed = True
                changedAspect = changedAspect + "onState "


            if old_brightness_report != new_brightness_report:
                delta_brightness = (abs((old_brightness_report or 0) -  (new_brightness_report or 0)))
                if delta_brightness > 1:
                    changed = True
                    changedAspect = changedAspect + "brightnessLevel from " + str(old_brightness_report) + " to " + str(new_brightness_report)


            if is_gate:
                affected_rooms = self.gateRoomMap.get(newDev.id, [])

                for room_id in affected_rooms:
                    self.checkGates(indigo.devices[room_id])

            if is_vacancyAuthority:
                vacancyDevice = indigo.devices[newDev.id]
                if not self.isOn(vacancyDevice):
                    self.debugLog(f"Vacancy authority {vacancyDevice.name} is reporting OFF state, evaluating vacancy authority implications")

                    affected_rooms = self.vacancyAuthorityRoomMap.get(newDev.id, [])

                    for room_id in affected_rooms:
                        self.debugLog
                        #set occupancy CZEWSKI
                        room = indigo.devices[room_id]
                        self.setOccupancy(room, False)
#                        self.checkVacancyAuthority(indigo.devices[room_id])


            if is_controlled:
                self.recordDeviceReport(newDev, newDev.onState, getattr(newDev, "brightness", None), devAlignment, authorityImpact)
                changed = False
                #changedAspect = ""
                #disrupted = self.isDisrupted(newDev)

                #if disrupted:
                #    self.recordDeviceDisrupt( newDev, new_on_report, new_brightness_report)

            # ---- Route to rooms via index ----
            affected_rooms = self.deviceRoomMap.get(newDev.id, [])


            for room_id in affected_rooms:
                # a controlled dervice changed in a room of interest to roomify
                # presumably from an external actor
                room = indigo.devices[room_id]
                # CZEWSKI - maybe you suppress room automations here ?
                # CZEWSKI - maybe this next state isn't runtime alterable ?
                self.authorityLog(f"Unexpected device update detected in room {room.name} ") 
                self.authorityLog(f"{newDev.name} (id: {newDev.id}) / Change in {changedAspect}") 
                self.logDisruption(newDev)

#EXPECTATION?

                # maybe dont assume its a disruption?
                # TO UNDERSTAND DISRUPTION
#                if  self.isDisrupted(room):
#                    #isDisrupted always returns false though
#                    self.recordTransferOfAuthority(room, room.states.get("automationsAuthorized"), False, "DISRUPTION: Causee by " + newDev.name)
#                    room.updateStateOnServer(
#                        "automationsAuthorized",
#                       False)

                #self.evaluateAutomationState(room)

                if new_on_report:
                    #room will almost certainly land at "on-ish" so lets get in front of that state change inidcator
                    room.updateStateOnServer("onState", True)
                    self.deviceLog(f"{room.name} {room.deviceTypeId} onState getting set to True in repsponse to {newDev.name}")

                self.evaluateRoomLighting(room,f"{newDev.name} changed")

                evalTime = time.time() + self.globalRoomAutomationCalmingPeriod

                self.scheduleRoomEvaluation(room, evalTime, newDev.name, "Disruption")

            if self.isOn(newDev) and self.globalOccupancyAutomationEnabled:
                self.debugLog(f"{newDev.name} reporting on state")
                #LATENCY TRACE on sensors? 
                if is_indicator:
                    self.recordSensorReport( newDev, True, 0)
                sensed_rooms = self.indicatorRoomMap.get(newDev.id, [])
                for room_id in sensed_rooms:
                    room = indigo.devices[room_id]
                    self.automationLog(f"Presence indicated in {room.name}") 
                    self.setOccupancy(room, True)

               

        except Exception as e:
            self.errorLog(f"[Roomify ERROR] schedule: {e}")        


    def isAligned(self, target, newBrightness, isDimmable):
        if target == None or newBrightness == None :
            return True
        if not isDimmable:
            if target > 0:
                target = 100
            if newBrightness > 0:
                newBrightness = 100

        return ( target == newBrightness )

    def isAlignedX(self, roomId, slot, newBrightness, isDimmable):
        rc = self.roomCache[roomId]
        key = "roomifyIntent" + str(slot)
        target = rc[key]

        if target == None:
            if slot == "1":
                return True
            else:
                return False

        if newBrightness == target:
            return True

        if isDimmable:
            return False

        if ( target > 0 and newBrightness > 0 ) :
            return True

        if target + newBrightness == 0:
            return True

        return False

    def isDivergentX(self,newBrightness,targetBrightness,isDimmable):
        if isDimmable:
            return ( newBrightness != targetBrightness )

        if newBrightness > 0 and targetBrightness == 0:
            return True

        if newBrightness == 0 and targetBrightness > 0:
            return False

        return True

    def identifyNextRoomObligation(self, room):

        rc = self.roomCache[room.id]

        def normalize_ts(ts):
            if ts is None:
                return None

            if isinstance(ts, str):
                if ts.strip() == "" or ts.lower() == "none":
                    return None
                try:
                    return float(ts)
                except:
                    return None

            try:
                return float(ts)
            except:
                return None

        obligations = {
        "1st Transition": normalize_ts(room.states.get("delayedLightingStarttime")),
        "Outro": normalize_ts(room.states.get("outroLightingStarttime")),
        "Vacancy": normalize_ts(room.states.get("watchdogCutoff")),
        "Disruption": normalize_ts(room.states.get("nextEvaluationTime"))
        }



        nextName, nextTime = min(
            (
            (name, ts)
            for name, ts in obligations.items()
            if (ts is not None) 
            ),
            key=lambda item: item[1],
            default=(None, None)
        )

        #self.debugLog(f"Next {room.name} obligation is {nextName} at {nextTime}")
        #INVESTIGATE - what happens here when bextTime is None. Maybe it should CLEAR the obligations?

        self.scheduleRoomEvaluation(room, nextTime, nextName, "Heartbeat")


    def scheduleRoomEvaluation(self, room, evalTime, eCause, eClass):


        priorObligation = self.nextEvaluationDue

        if evalTime is not None:
            if not isinstance(evalTime, (int, float)):
                self.logger.error(
                    f"scheduleNextRoomEvaluation: invalid nextEvaluationTime for "
                    f"{room.name}: {evalTime!r} "
                    f"({type(evalTime).__name__})"
                )
                evalTime = None
            else:
                evalTime = float(evalTime)

        if self.nextEvaluationDue == None:
            self.nextEvaluationDue = evalTime

        if evalTime:
            if evalTime < self.nextEvaluationDue:
                self.nextEvaluationDue = evalTime   

        rc = self.roomCache[room.id]
        humanTime = ""
        if evalTime:
            humanTime = datetime.datetime.fromtimestamp(evalTime).strftime("%H:%M:%S")


        rc["nextEvaluationTime"] = evalTime
        rc["nextEvaluationInitiator"] = room.name
        rc["nextEvaluationClass"] = eClass
        #rc["authorityReviewPending"] = True

        self.authorityLog(f"Scheduling evaluation for {room.name} at {humanTime} due to {eCause} class {eClass}"  )


        room.updateStatesOnServer([
            {"key": "nextEvaluationTime", "value": evalTime},
            {"key": "nextEvaluationTimeUI", "value": humanTime},
            {"key": "nextEvaluationInitiator", "value": room.name},
            {"key": "nextEvaluationClass", "value": eClass},
        ])

        if priorObligation != self.nextEvaluationDue:
            self.publishToAllObservers()

    def deviceStartComm(self, dev):
        # 1. Force Indigo to reread the XML definition for this device instance
        dev.stateListOrDisplayStateIdChanged()

        # 2. Push the new key to the server right away
        # dev.updateStateOnServer(key="myNewStateKey", value="Initial Value")


    def getRoomRuntime(self, room_id):
        if room_id not in self.roomRuntime:
            self.roomRuntime[room_id] = {
                "auditBurden": 0,
                "divergenceCount": 0,
                "attemptsRemaining": 0,
                "auditPending": False,
                "lastAuditAt": 0,
            }
        return self.roomRuntime[room_id]

    def initializeRoom(self, device):

 #       onState = device.pluginProps.get("onState", False)
 #       occupied = device.pluginProps.get("occupied", False)

#        device.replacePluginPropsOnServer({
#            "roomifyVersion": "2",
#            "mode": "dimmer"
#        })

#        if device.deviceTypeId == "Room":
#            indigo.device.replaceDeviceTypeId("roomifyRoom")
        self.getRoomRuntime(device.id)

        self.cacheRoom(device)    

        device.updateStateOnServer("automationGateStatus", True)
        roomOccupancyAutomationActive = device.pluginProps.get(
            "roomOccupancyAutomationActive", True)

        self.debugLog(f"Room Occupancy Atomations Active: {roomOccupancyAutomationActive}")

        device.updateStateOnServer("roomOccupancyAutomationActive",roomOccupancyAutomationActive)

        initialBrightness = device.pluginProps.get(
            "initialBrightness", 80)
        
        #CZEWSKI
        #If a room changes, all theses mapping are subject to change, so we need to rebuild all the indexes that rely on those mappings
        #self.buildDeviceRoomIndex()
        #self.buildIndicatorRoomIndex()
        #self.buildVacancyAuthorityRoomIndex()
        #self.buildGateRoomIndex()

        #lets create rooms as being authorized and vacant buy default. that 
        #meaning open to autoation


        self.checkGates(device)
        
        self.evaluateAutomationState(device)

        device.updateStateOnServer(
            "autoOffBrightness",
            device.pluginProps.get("autoOffBrightness"))

        self.initializeRoomBrightnessState("initial", device)
        self.initializeRoomBrightnessState("delayed", device)
        self.initializeRoomBrightnessState("outro", device)

        device.updateStateOnServer("automationState", device.states.get("automationState", 0))

        roomOccupancyAutomationActive = device.pluginProps.get(
            "roomOccupancyAutomationActive", True)

        self.debugLog(f"Room Occupancy Atomations Active: {roomOccupancyAutomationActive}")

        device.updateStateOnServer("roomOccupancyAutomationActive",roomOccupancyAutomationActive)

        roomDormancyCutoffActive = device.pluginProps.get(
            "roomDormancyCutoffActive", True)

        self.debugLog(f"Room Dormancy Cutoff Active: {roomDormancyCutoffActive}")

        device.updateStateOnServer("roomDormancyCutoffActive",roomDormancyCutoffActive)

        #maybe not though?
        self.recomputeRoom(device)

        self.deviceLog(f"Initialized room: {device.name}")  
 

    def clearRoomTimeout(self,room):
         
        room.updateStateOnServer("watchdogCutoff", None)
        room.updateStateOnServer("watchdogCutoffDisplay", None)  
        room.updateStateOnServer("lightingPhase", "off")     

    def setRoomTimeout(self, room):

        cyclesRemaining = room.states.get("cutoffCyclesRemaining")
        if cyclesRemaining:
            return

        if not self.globalRoomDormancyCutoffEnabled:
            return

        roomDormancyCutoffActive = room.pluginProps.get("roomDormancyCutoffActive",False)
        if not roomDormancyCutoffActive:
            return


        currentCutoff = room.states.get("watchdogCutoff")
        if (currentCutoff) and (currentCutoff != ""):
            #dont update the watchdog
            return

        roomDormancyCutoffMinutes = room.pluginProps.get("roomDormancyCutoff")

        if ( roomDormancyCutoffMinutes == "" ) or ( ( roomDormancyCutoffMinutes == None ) ):
            timeout_minutes = float(self.globalRoomDormancyDefault)
        else:
            timeout_minutes = float(roomDormancyCutoffMinutes)

        self.automationLog(f"Setting timeout for room: {room.name} at {timeout_minutes} minutes")

        expiry = time.time() + (timeout_minutes * 60)

        displayTime = datetime.datetime.fromtimestamp(
            expiry).strftime("%I:%M:%S %p")
        
        room.updateStateOnServer("cutoffCyclesRemaining", None)
        room.updateStateOnServer("watchdogCutoff", expiry)
        room.updateStateOnServer("watchdogCutoffDisplay", displayTime)


    def evaluateRoomLighting(self, room, cause):

        # I expect this routine to run only when an EXTERNAL ACTOR changes device that is part of the collected devices for a given room
        # even though the room state might not be changing ... this still should change the expiry timing
        # no idea WHY I would end up here when a collected sensor cahnges

        rc = self.roomCache[room.id]

        self.deviceLog(f"Evaluating lighting for room: {room.name}")


        controlled_ids = [int(x) for x in room.pluginProps.get("controlledDevices", [])]

        any_on = False
        max_brightness = 0

        brightnessPotential = 0
        brightnessEncountered = 0

        alreadyOn = self.isOn(room)
        alreadyAuthorized = rc.get("automationsAuthorized", True)

        any_on = (self.roomCache[room.id]["totalBrightness"] > 0)

#        for dev_id in controlled_ids:
#
#            dev = indigo.devices[dev_id]
#            if dev.onState:
#                any_on = True

            #lets track how beight the room is yes?
#            brightnessPotential += 100
#            if self.isDimmable(dev):
#                b = int(dev.states.get("brightnessLevel",0))
#                brightnessEncountered += b
#            else:
#                if dev.onState:
#                    brightnessEncountered += 100

#        brightnessPercentage = int(100*(brightnessEncountered/brightnessPotential))
#        self.deviceLog(f"Perceived brightness in {room.name} calculated at {brightnessEncountered} of {brightnessPotential} aka {brightnessPercentage}")
#        room.updateStateOnServer("brightness",brightnessPercentage)

        if any_on:
            # set a fresh watchdog timestamp.
            self.automationLog(f"Confirming watchdog cutoff for room '{room.name}'")
            self.setRoomTimeout(room)
            #NEW CODE to reclaim (and surrendeer?) authorization a little more aggressively
            #if self.globalAuthorityAutoStandbyRecovery: 
            #    if alreadyAuthorized == False and rc["totalBrightness"] == rc["alignmentTarget"]:
            #        self.authorityLog(f"Room '{room.name}' matches Roomify expectations: resuming automation authority.")
            #        self.recordTransferOfAuthority(room, rc.get("automationsAuthorized"), True, "DISRUPTION: Room left expected state")
            #        rc["automationsAuthorized"] = True
            #        room.updateStateOnServer("automationsAuthorized", True) 
            #    elif alreadyAuthorized == True and rc["totalBrightness"] != rc["alignmentTarget"]:
            #        self.authorityLog(f"Room '{room.name}' != Roomify expectations: deferring automation authority.")
            #        self.recordTransferOfAuthority(room, rc.get("automationsAuthorized"), False, "DISRUPTION ENDED: Room returned to expected state")
            #        rc["automationsAuthorized"] = False


            #if alreadyAuthorized:
            #    self.recordTransferOfAuthority(room, room.states.get("automationsAuthorized"), False, f"DISRUPTION: {cause} outside of Roomify intent")
            #    if  self.globalAuthorityAutoStandbyRecovery:
            #        self.authorityLog(f"{room.name} surrendering automation authority per '{cause}'")
            #        self.revokeAAU(room)
            #    else:
            #        self.authorityLog(f"{room.name} {cause} ignored as auto standby is not enabled")
        else:
            self.deviceLog(f"Clearing watchdog cutoff for room '{room.name}'")
            self.clearRoomTimeout(room)
            if rc.get("occupied", False):
                self.deviceLog(f"Adjusting occupancy decay for room '{room.name}'")
                self.roomJustTurnedOff(room)

            # only reinstate automation authority if the room is unoccupied
#            if alreadyAuthorized == False:
#                if not rc.get("occupied", False):
#                    if  self.globalAuthorityAutoStandbyRecovery:
#                        self.authorityLog(f"Room '{room.name}' is unoccupied & off: resuming automation authority.")
#                        self.recordTransferOfAuthority(room, rc.get("automationsAuthorized"), True, "DISRUPTION ENDED: Vacant room settled into an OFF state")
#                        rc["automationsAuthorized"] = True
#                        room.updateStateOnServer("automationsAuthorized", True) 
#                    else:
#                        self.authorityLog(f"Room '{room.name}' is unoccupied & off [BUT] resuming automation authority is not enble.")
#                else:
#                    if self.globalAuthorityAutoStandbyRecovery:
#                        self.authorityLog(f"Room '{room.name}' is occupied and off: retaining automation authority")
 
        self.evaluateAutomationState(room)


        # Only update if changed (important to avoid spam)
        if (
            room.onState != any_on 
        ):

            self.deviceLog(f"Room '{room.name}' state change: on={any_on}")
            self.suppressDev(room.id)
#            self.debugLog(f"Added '{room.id}' to devicesBeingControlled: {self.devicesBeingControlled}")


            if any_on:
                room.updateStateOnServer("onState", True)
                room.updateStateOnServer("onOffState", True)
            else:
                room.updateStateOnServer("onState", False)
                room.updateStateOnServer("onOffState", False)

            self.debugLog(
                f"Roomify {room.name} lighting eval → on={any_on}"
            )



#   DEVICES ARE CONTROLLED. WILL ALSO NEED A SENSOR ROOM INDEX TO KNOW WHICH ROOMS TO EVALUATE WHEN A SENSOR CHANGES
    def buildDeviceRoomIndex(self):

        self.deviceRoomMap = {}

        for room in indigo.devices.iter("self.roomifyRoom"):

            controlled = room.pluginProps.get("controlledDevices") or []
            controlled = [int(x) for x in controlled]

            for dev_id in controlled:

                if dev_id not in self.deviceRoomMap:
                    self.debugLog(f"Mapping controlled device {dev_id} to room {room.name}")
                    self.deviceRoomMap[dev_id] = []
                    self.buildDeviceStartupTrace(dev_id)

                self.deviceRoomMap[dev_id].append(room.id)



    def buildGateRoomIndex(self):

        self.gateRoomMap = {}

        for room in indigo.devices.iter("self.roomifyRoom"):

            gates = room.pluginProps.get("automationGates") or []

            #gates = [int(x) for x in gates]

            for dev_id in gates:
                if dev_id != "none":
                    dev_id = int(dev_id)
                    if dev_id not in self.gateRoomMap:
                        self.debugLog(f"Mapping automation gate {dev_id} to room {room.name}")
                        self.gateRoomMap[dev_id] = []

                    self.gateRoomMap[dev_id].append(room.id)

#   INDICATORS INFORM CONTROL. WILL ALSO NEED A SENSOR ROOM INDEX TO KNOW WHICH ROOMS TO EVALUATE WHEN A SENSOR CHANGES
    def buildVacancyAuthorityRoomIndex(self):

        self.vacancyAuthorityRoomMap = {}
        self.debugLog("Building vacancy authority index...")

        for room in indigo.devices.iter("self.roomifyRoom"):

            dev_id = room.pluginProps.get("vacancyAuthority")

            self.debugLog(
                f"Checking room {room.name} for vacancy authority device... found {dev_id}"
            )

            if dev_id not in ("none", "", None):

                dev_id = int(dev_id)

                if dev_id not in self.vacancyAuthorityRoomMap:
                    self.vacancyAuthorityRoomMap[dev_id] = []

                self.vacancyAuthorityRoomMap[dev_id].append(room.id)

                self.debugLog(
                    f"Mapping vacancy authority {dev_id} to room {room.name}"
                )

        self.debugLog(
            f"Built vacancy authority index: {self.vacancyAuthorityRoomMap}"
        )

    def buildIndicatorRoomIndex(self):

        self.indicatorRoomMap = {}

        for room in indigo.devices.iter("self.roomifyRoom"):

            sensed = room.pluginProps.get("occupancyIndicators") or []

#            sensed = [int(x) for x in sensed]

            for dev_id in sensed:

                if dev_id != "none":
                    dev_id = int(dev_id)
                    if dev_id not in self.indicatorRoomMap:
                        self.debugLog(f"Mapping occupancy indicator {dev_id} to room {room.name}")
                        self.indicatorRoomMap[dev_id] = []

                    self.indicatorRoomMap[dev_id].append(room.id)


    def resolveRequestedState(self, action, dev):
        """
        Returns:
            True  -> intent is ON
            False -> intent is OFF
            None  -> unsupported / unknown
        """

        if action.deviceAction in (
            indigo.kDeviceAction.TurnOn,
            indigo.kDeviceAction.Toggle and not dev.onState
        ):
            return True

        if action.deviceAction in (
            indigo.kDeviceAction.TurnOff,
            indigo.kDeviceAction.Toggle and dev.onState
        ):
            return False

        if action.deviceAction == indigo.kDeviceAction.Toggle:
            return not dev.onState
        
        if action.deviceAction == indigo.kDeviceAction.SetBrightness:
            if action.actionValue == 0:
                # brightness of zero requested = turn off ?
                return False
            else:
                return True           

        return None

    def actionControlDevice(self, action, device):
        # add code to account for brightness

        # LATENCY - this is the bit where we see Indigo asserting device control
        #           which may or may not be part of a Roomidy initiated sequence
        #           the timestamp for this belopmgs oin a special place ? t1 I think


        try:
            rc = self.roomCache[device.id]
            requestedState = self.resolveRequestedState(action, device)
            # ---- TURN ON ----
            if requestedState == True:
                self.authorityLog(f"ON requested: {device.name} at brightness {action.actionValue}")
                targetBrightness = action.actionValue 
                if targetBrightness == 0:
                    targetBrightness= device.states.get("initialBrightness")

                #for latency tracking
                #self.recordDeviceCommand( device, True, targetBrightness)

                #self.ignoreNextRoomChange(device, "ON requested", True, action.actionValue)
                self.turnRoomOn(device, targetBrightness)

                if self.globalAuthorityAutoStandbyRecovery:
                    rc["automationsAuthorized"] = False
                    self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), False, "DISRUPTION: Room ON Command Processed")
                    device.updateStateOnServer("automationsAuthorized", False)
                    self.evaluateAutomationState(device)
                return

            # ---- TURN OFF ----
            if requestedState == False:
                #self.recordDeviceCommand( device, False, 0)
                self.authorityLog(f"OFF requested: {device.name}")
                self.turnRoomOff(device)
                if self.globalAuthorityAutoStandbyRecovery:
                    self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), True, "DISRUPTION ENDED: Room OFF Command Processed")
#                    self.roomJustTurnedOff(device)
#                    rc["automationsAuthorized"] = True
#                    device.updateStateOnServer("automationsAuthorized", True)
                 
#                    self.evaluateAutomationState(device)

                return
 
        except Exception as e:
            self.errorLog(f"[Roomify ERROR] actionControlDevice: {e}")

           
    def isDimmable(self, dev):

        # Indigo-native state check (most reliable)
        if "brightnessLevel" in dev.states:
            return True

        # fallback: Hue / known dimmer models
        if "Hue" in dev.model:
            return True

        return False

    def applyRoomStateToDevices(self, room):
        #this appears ti=o be dead code
        room_is_on = room.states.get("onState", False)
        room_brightness = room.states.get("brightness", 0)
        #self.ignoreNextRoomChange(room, "Roomify-Initiated Change", room_is_on, room_brightness)
        self.automationLog(f"Executing divergence resolution for {room.name}")
        self.applyTargetStateToDevices(room, room_is_on, room_brightness, 0)

    def applyTargetStateToDevices(self, room, room_is_on, room_brightness, delay ):

        rc = self.roomCache[room.id]

        rc["roomifyIntent3"] = rc["roomifyIntent2"]
        rc["roomifyIntent2"] = rc["roomifyIntent1"]
        rc["roomifyIntent1"] = room_brightness


        #if not self.automationsActionable(room):
        #    self.errorLog(f"Cannot execute request to apply target states in {room.name}. Automations are not currently actionable in this room. ")
        #    return
        self.automationLog("Applying target room state to devices...")
#        self.suppressEvaluationDepth += 1

        if room_brightness == 0:
            #CZEWSKI
            room_is_on = False

        if room_is_on:
            intendedState = "On"
        else:
            intendedState = "Off"
        evaluationNeeded = False

        try:

#            controlled_ids = room.pluginProps.get("controlledDevices") or []
            controlled_ids = rc["controlled"]
            controlled_ids = [int(x) for x in controlled_ids]
            self.automationLog(f"Roomify -> {room.name}/{room_is_on}/{intendedState} ")

            divergence_count = 0
            alignmentTarget = 0
            rc["alignmentTarget"] = None
            rc["deviceReports"] = {}
            rc["devicesReporting"] = 0
            
            for dev_id in controlled_ids:

                dev = indigo.devices[dev_id]
                #this is where we need to record intent so we dont wrongly register a disruption
                #v1 probably relied entirely on *ignore next room chages* thinking
                #v2 needs to rencile the *chage* report with the outcome, which is surely
                #what these two functions are reaching for 

                #DIVERGENCE DEPRECATED
                # might need to drop this back into the mix

                #if not self.isDivergent(dev, room_is_on, room_brightness):
                #    continue


                self.recordRoomifyIntent(dev, room_is_on, room_brightness)
                # stuffs expected outcome into canonical

                self.suppressDev(dev_id, "Applying Room State", room_is_on, room_brightness)
                # stuffs expected outcome into recently controlled

                is_dimmer = self.isDimmable(dev)

                self.debugLog(f" - Applying {room_is_on} at {room_brightness}% to {dev.name} (id: {dev_id}) ... dimmable={is_dimmer} ... room_brightness={room_brightness}")
                # ---- ON / OFF ----
                if room_is_on:
                    if is_dimmer:
                        alignmentTarget += room_brightness
                        #CZEWSKI
#                       self.debugLog(f" - Applying {room_is_on} at {room_brightness}% to {dev.name} (id: {dev_id}) ... dimmable={is_dimmer} ... room_brightness={room_brightness}")
                        #self.sleep(0.3)
                        indigo.dimmer.setBrightness(dev_id, int(room_brightness), int(delay))
#                        if not self.isOn(dev):
##                            indigo.device.turnOn(dev_id) #to confirm on state for devices that dont reliably report brightness changes as on state changes                    
#                            indigo.dimmer.setBrightness(dev_id, int(room_brightness), int(delay))
#                        else:
#                            indigo.dimmer.setBrightness(dev_id, int(room_brightness), delay)
                    else:
                        alignmentTarget += 100
                        indigo.device.turnOn(dev_id)

                    # 2026.07.07 - trying not to treat every change as a divergence  
                    #              1) no longer comsidering the possibility of divergence on the tail end of an off command
                    #              2) giving the light a change to report compliance with the request
                    #
                    # I might also need something on the event side to recognize when a controlled device is reporting 
                    # allignment with romify intent (rather than just polling for it later at some arbitrary moment)
                    #self.sleep(0.25)
                    if self.isDivergent(dev, room_is_on, room_brightness):
                        divergence_count += 1
                else:
                    if is_dimmer:
                        indigo.dimmer.setBrightness(dev_id, 0)
                    else:
                        indigo.device.turnOff(dev_id)

                #DECONGESTANT - give the device a chance to report its new state before moving on to the next device
                #self.sleep(0.1)

            #savethetarget
            rc["alignmentTarget"] = alignmentTarget

            #DIVERGENCE HANDLING is probably deprecated

            rt = self.getRoomRuntime(room.id)
            rt["auditBurden"] = divergence_count

 #           room.updateStateOnServer("auditBurden", divergence_count)
 #           room.updateStateOnServer("divergenceCount", divergence_count)

            #OLD DIVERGENCE CODE - COMMENTED OUT 8/16/2026
            #self.automationLog(f"{divergence_count} devices needed to be updated to achieve the intended state for {room.name}")
            #if divergence_count > 0:
            #    auditAttemptsRemaining = rt["auditAttemptsRemaining"]
            #    if auditAttemptsRemaining > 0:
            #        auditAttemptsRemaining -= 1
            #        rt["auditPending"] = True
            #        rt["auditAttemptsRemaining"] = auditAttemptsRemaining
              
                    #old code ... i used to let heartbeat handle this. i think i might try recursion on a 1 second delay ?
                    #self.scheduleRoomEvaluation(room, time.time()+self.globalRoomAutomationCalmingPeriod, room.name, "Divergence Resolution")


            #else:
            #    rt["auditPending"] = False
 #               room.updateStateOnServer("auditPending", False)



        except Exception as e:
            self.errorLog(f"[Roomify ERROR] applyTargetStateToDevices: {e}")

        self.sleep(1.0)

    # ---------------------------------------------------------
    # 
    # ROOMIFY ROOM METHODS NEXT
    #     
    # ---------------------------------------------------------

    def evaluateAllAutomationStates(self):

        for room in indigo.devices.iter("self.roomifyRoom"):
            self.evaluateAutomationState(room)


    def evaluateAutomationState(self, room):

        #we can drive this one from roomCache ... updated 20206.07.21

        rc = self.roomCache[room.id]
        if not rc:
            return

        self.debugLog(f"Evaluating automation state for {rc["name"]}")

#        if room.deviceTypeId not in [ "Room", "roomifyRoom" ]:
#            return

#        automations_enabled = room.states.get("roomOccupancyAutomationActive", True)
#        automations_authorized = room.states.get("automationsAuthorized", True)
#        gated = room.states.get("automationGateStatus")

        automations_enabled = rc.get("roomOccupancyAutomationActive", True)
        automations_authorized = rc.get("automationsAuthorized", True)
        gated = rc.get("automationGateStatus", True)

#        if (gated is None) or (gated == "") or (gated == "none"):
#            self.debugLog(f"No gate status for {r["name"]}, treating as ungated")
#            gated = True

        automation_stateUI = ""
        automation_state = 0
        if (not self.globalOccupancyAutomationEnabled) or not gated:
            self.automationLog(f"Automations are not enebled")
            automation_state = 3
            automation_stateUI = "Prohibited"
        else:
            if automations_enabled == False:
                self.automationLog(f"Automations are suspended for room '{room.name}'")
                automation_state = 2
                automation_stateUI = "Suspended"
            else:
                if automations_authorized == False:
                    self.automationLog(f"Automations are not authorized for room '{room.name}'")
                    automation_state = 0
                    automation_stateUI = "Standby"
                else:
                    self.automationLog(f"Automations are enabled and authorized for room '{room.name}'")
                    automation_state = 1
                    automation_stateUI = "Active"

        #roomCache please 
        rc["automationState"] = automation_state

        room.updateStatesOnServer([
            {"key": "automationState", "value": automation_state},
            {"key": "automationStateUI", "value": automation_stateUI},
        ])

    def checkGates(self, room):
        self.debugLog(f"Checking gates for {room.name}")
        gateStatus = self.gatesSatisfied(room)
        self.roomCache[room.id]["automationGateStatus"] = gateStatus
        room.updateStateOnServer("automationGateStatus", gateStatus)
        self.evaluateAutomationState(room)

    def gatesSatisfied(self, room):

#        controlled_ids = room.pluginProps.get("controlledDevices") or []
#        controlled_ids = [int(x) for x in controlled_ids]

#        sensed = room.pluginProps.get("occupancyIndicators") or []
#        sensed = [int(x) for x in sensed]

#        for dev_id in sensed:

        gated = True

        gates = room.pluginProps.get("automationGates") or []
        if (not gates) or (gates == "") or (gates == "none"):
            return True

#        self.dumpDict(f"=========={room.name} GATES ==============", gates)

#        gates = [int(x) for x in gates]

        for dev_id in gates:
            if dev_id != "none":    
                dev_id = int(dev_id)
                self.debugLog(f"Checking gate device {dev_id} for room {room.name}")
                if not self.isOn(indigo.devices[dev_id]):
                    gated = False
                    break   

        return gated

        

    def occupancySustained(self, room):

        self.debugLog(f"Possibly sustaining occupancy in  {room.name}")

        occupancy_authority_id = room.pluginProps.get("occupancyAuthority")

        if occupancy_authority_id and ( not occupancy_authority_id == "none" ):
            occupancy_authority = indigo.devices[int(occupancy_authority_id)]
            self.debugLog(f"Checking {occupancy_authority.name} for extension state")
            if self.isOn(occupancy_authority):
                self.automationLog(f"Extending automation occupancy expiration for room '{room.name}' due to occupancy authority '{occupancy_authority.name}' being ON")
                self.setOccupancy(room,True)
                return True
            else:
                return False


    def considerReauthorization(self,roomId):

        #heartbeat invokes this method to bring rooms out of suspended authrization when appropriate
        #but should it?
        rc = self.roomCache[roomId]

        if rc.get("automationsAuthorized"):
            #no need to re-authorize a room thaty is already authorized
            return
        
        if rc.get("occupied"):
            # ROOM IS NOT AUTHORIZED BUT IT IS OCCUPIED
            # NO NEED TO RECONSIDER AGAIN UNTIL OCCUPANCY CHANGES?
            #we don't assert authority in occupied spaces. 
            return
        
        on = rc.get("totalBrightness") > 0
#        self.debugLog(f"isOn returned {on} for Room {room.name} ")
        if on:
            #we don't assert authority in rooms that have been left on with apparent intent
#            self.logDecision(room, f"{room.name} is *on* and not subject to reAuthorization.")
#           but maybe we need to check onState again soon ?
#            self.scheduleRoomEvaluation(room, time.time()+30, room.states.get("nextEvaluationInitiator"), "Disruption+")
            return
#        else:
#            self.debugLog(f"{room.name} with onState = {room.states.get("onState")} is considered OFF by isOn")

        authorityChangeInitiator = rc.get("authorityChangeInitiator")
        if authorityChangeInitiator.startswith("INTENT"):
            return

        #we know this room to be unauthorized, vacant and off. so lets re-authorize it
        room = indigo.devices[roomId]
        self.reAuthorize(room)
        self.clearNextObligation(room)

    def clearNextObligation(self, room):
        rc = self.roomCache[room.id]
        rc["nextEvaluationTime"] = None
        rc["nextEvaluationInitiator"] = None
        rc["nextEvaluationClass"] = None
        room.updateStatesOnServer([
            {"key": "nextEvaluationTime", "value": None},
            {"key": "nextEvaluationTimeUI", "value": None},
            {"key": "nextEvaluationInitiator", "value": None},
            {"key": "nextEvaluationClass", "value": None},
        ])

    def reAuthorize(self,room):
        rc = self.roomCache[room.id]
        rc["automationsAuthorized"] = True
        room.updateStateOnServer("automationsAuthorized", True)
        self.evaluateAutomationState(room)
        self.logDecision(room,"Re-authorizing Automations")

    def initiateCutoff(self, room):
        # get current brightness
        # get target (off) brightness
        self.heartbeatLog(f"Initiating cutoff of room {room.name}")
        currentBrightness = room.states.get("brightness")
        autoOffBrightness = room.states.get("autoOffBrightness")
        if autoOffBrightness:
            autoOffBrightness = int(autoOffBrightness)
        delta = currentBrightness - autoOffBrightness
        increment = int(round(delta / 10))
        room.updateStateOnServer("cutoffCyclesRemaining", 10)
        room.updateStateOnServer("cutoffCyclesIncrement", increment)
        self.heartbeatLog(f"Initiating cutoff of room {room.name} over 10 increments of {increment}")



    #heartbeat
    def runConcurrentThread(self):

        self.logger.info("Roomify heartbeat thread started")

        try:
            while True:

                self.heartbeatLog("heartbeat v2")

                now = time.time()

                if self.nextEvaluationDue is not None and now >= self.nextEvaluationDue:
                    self.doHeartbeat(now)

                self.sleep(5)

        except self.StopThread:
            self.logger.info("Roomify heartbeat thread stopped")

    def doHeartbeat(self, now):
        if not self.configStable:
            if self.configChangedDeviceId:
                self.reInitRoom(self.configChangedDeviceId)
            else:
                self.loadPluginPrefs()

#                for room in indigo.devices.iter(self.pluginId):


        if self.nextEvaluationDue is not None and now < self.nextEvaluationDue:
            return

        for roomId, rc in self.roomCache.items():

#                    if room.deviceTypeId != "roomifyRoom":
#                        continue
            
#                    self.considerReauthorization(roomId)

            nextEval = rc.get("nextEvaluationTime")
            nextEval = float(nextEval) if nextEval else None

            if nextEval is None:
                continue

            if self.nextEvaluationDue is None:
                self.nextEvaluationDue = nextEval
            elif self.nextEvaluationDue > nextEval:
                self.nextEvaluationDue = nextEval

            #self.authorityLog(f"Heartbeat processing room {rc.get('name')} nextEval={nextEval} now={now} nextEvaluationDue={self.nextEvaluationDue}")

            if nextEval > now:
                continue

            arp = ((rc.get("automationsAuthorized") == False) and rc.get("totalBrightness") == 0) or rc.get("authorityReviewPending")
            if arp:
                self.authorityReview(roomId)
                rc["authorityReviewPending"] = False

            room = indigo.devices[roomId]

            self.identifyNextRoomObligation(room)

            # TIMEOUT BLOCK
#                        if room.states.get("timeoutsEnabled", True) and self.roomDormancyCutoffEnabled:

#                    self.heartbeatLog(f"Heartbeat processing room {room.name} Ena bled={self.globalRoomDormancyCutoffEnabled} ACtive={room.states.get("roomDormancyCutoffActive", False)}")

            if self.globalRoomDormancyCutoffEnabled and room.states.get("roomDormancyCutoffActive", False):
            
                # --- Get expiry time ---
                cutoff = room.states.get("watchdogCutoff")

                #self.heartbeatLog(f"Heartbeat processing room {room.name}")

                #self.debugLog(f"{room.name} cutoff set at {cutoff}")

                if cutoff:

                    cutoff = int(cutoff)

                    if now >= cutoff:
                        self.automationLog(f"Timeout expired for room '{room.name}'")
                        #experimental
                        self.cacheRoom(room)
                        self.initiateCutoff(room)
                        self.clearRoomTimeout(room)
                        cutoff = 0
                        nextTime = now
                        self.nextEvaluationDue = now
                        nextName = "Dormancy Cutoff"
                        self.scheduleRoomEvaluation(room, nextTime, nextName, "Cutoff")


                cyclesRemaining = room.states.get("cutoffCyclesRemaining")

                if cyclesRemaining:
                    cyclesRemaining = int(cyclesRemaining)
                else:
                    cyclesRemaining = 0


#                self.heartbeatLog(
#                    f"cyclesRemaining={room.states.get('cutoffCyclesRemaining')}, "
#                    f"increment={room.states.get('cutoffCyclesIncrement')}"
#)
        
                if cyclesRemaining > 0:
                    #cutoff process has already started so continue it?
                    cyclesRemaining -= 1
                    room.updateStateOnServer("cutoffCyclesRemaining", str(cyclesRemaining))
                    currentBrightness = room.states.get("brightness")
                    increment = room.states.get("cutoffCyclesIncrement")
                    if not increment:
                        self.heartbeatLog(f"Unknown dimming increment for room {room.name}")
                        self.directRoom(room, False, 0, 0)
                    else:
                        increment = int(increment)
                        nextBrightness = currentBrightness - increment
                        if cyclesRemaining > 0:
                            self.heartbeatLog(f"Dormancy Cutoff Dimming {room.name} to {nextBrightness}")
                            self.directRoom(room, True, nextBrightness, 0)
                            nextTime = now
                            self.nextEvaluationDue = now
                            nextName = "Dormancy Cutoff"
                            self.scheduleRoomEvaluation(room, nextTime, nextName, "Cutoff2")
                        else:
                            self.directRoom(room, False, 0, 0)



#lets lighten the heartbeat and skip past rooms not subhect to automation
#after reauthorizing if appropriate

            #if not self.isOn(room):
            #    #everything an OFF or DORMANCY room needs has been handled
            #    continue

#                    if self.occupancySustained(room):
#                        self.identifyNextRoomObligation(room)
#                        continue

            next_evaluation_time = rc.get("nextEvaluationTime")
            next_evaluation_time = float(next_evaluation_time) if next_evaluation_time else None

            if not next_evaluation_time:
                continue

            if next_evaluation_time > now:
                continue


            try:
                # --- Only care about your Roomify devices ---
                if room.deviceTypeId not in ["Room", "roomifyRoom"]:
#                            self.debugLog(f"Roomify intends {dev.name} to be set to {onState} @ brightness {brightness} ")

#                            self.debugLog(f"{room.name} with device type {room.deviceTypeId} is being bypassed in heartbeat")
                    continue

                # --- New Code to Coalesce Device Events into Room State 

                # DIVEGENCE RESOLUTION BLOCK
                rt = self.getRoomRuntime(room.id)

                if self.globalPhasedLightingEnabled:
                    t = room.states.get("delayedLightingStarttime")
                    transitionTime = float(t) if t else None
                else:
                    transitionTime = None

                if self.globalPhasedLightingEnabled:
                    t = room.states.get("outroLightingStarttime")
                    outroTime = float(t) if t else None
                    #outroTime = float(room.states.get("outroLightingStarttime", 0)) 
                else:
                    outroTime = None


                if transitionTime and (now >= transitionTime):
                    if not self.occupancySustained(room):
                        self.automationLog(f"'{room.name} phase change invoked: initial -> delayed")
                        #targetBrightness =  room.pluginProps.get("delayedBrightness", 60)
                        room.updateStateOnServer("delayedLightingStarttime", None)
                        room.updateStateOnServer("delayedLightingStarttimeUI", None)
                        self.autoRoomBrightness(room, "delayed")
                        transitionTime = None


                if outroTime and (now >= outroTime):
                    if not self.occupancySustained(room):
                        self.automationLog(f"'{room.name} phase change invoked: delayed -> outro")
                        #targetBrightness = room.pluginProps.get("outroBrightness")
                        room.updateStateOnServer("outroLightingStarttime", None)
                        room.updateStateOnServer("outroLightingStarttimeUI", None)
                        self.autoRoomBrightness(room, "outro")
                        outroTime = None

                if self.globalOccupancyAutomationEnabled:
                    expiry = room.states.get("occupancyCutoff")
                    expiry = float(expiry) if expiry else None

#                        self.debugLog(f"Transition Time:{transitionTime} /  OutroTime:{outroTime} / Expiry: {expiry}")


                    if expiry:
                        # an occupancyCutoff is in effect. lets see if it has expired

                        remainingMinutes = int((expiry - now)/60)
                        room.updateStateOnServer("minutesRemaining",remainingMinutes)

                        if now >= expiry:
                            room.updateStateOnServer("minutesRemaining",None)
                            room.updateStateOnServer("lightingPhase", "off")
                            room.updateStateOnServer("nextEvaluationTime",None)
                            rc["nextEvaluationTime"] = None

                            self.automationLog(f"Automation period expired for room '{room.name}'")
                            self.setOccupancy(room,False)                                
                            expiry = None


            except Exception as e:
                self.logger.error(f"Heartbeat error ({room.name}): {e}")

            if next_evaluation_time:
                self.identifyNextRoomObligation(room)

        self.confirmNextScheduledObligation()
        #figure out what teh next evaluation is based on whichever event is anticipated next
        #next_evaluation_time = 0
        #nextReason = ""

        #if transitionTime != 0:
        #    next_evaluation_time = transitionTime
        #    nextReason = "1st Delay" 
        #else:
        #    if outroTime != 0:
        #        next_evaluation_time = outroTime
        #        nextReason = "Outro"
        #    else:
        #        if expiry != 0:
        #            next_evaluation_time = expiry
        #            nextReason = "Occuancy Ending"

        #if ( next_evaluation_time = 0 and cutoff != 0) OR (cutoff < next_evaluation_time):
        #    next_evaluation_time = cutoff
        #    nextReason = "Cutoff"
        #    
        #self.scheduleRoomEvaluation(room,next_evaluation_time,nextReason,"Heartbeat")





    def updateSecurityStatus(self, action):

        try:
            deviceId = int(action.props.get("deviceId"))

            alertScore = action.props.get("alertScore")
            alertClassification = action.props.get("alertClassification")
            alertClassificationUI = action.props.get("alertClassificationUI")

            dev = indigo.devices[deviceId]

            dev.updateStatesOnServer([
                {"key": "alertScore", "value": alertScore},
                {"key": "alertClassification", "value": alertClassification},
                {"key": "alertClassificationUI", "value": alertClassificationUI},
            ])

            self.debugLog(
                f"Security state updated for {dev.name}: "
                f"score={alertScore}, class={alertClassification}"
            )

        except Exception as e:
            self.errorLog(f"updateSecurityStatus failed: {e}")

    def revokeRooms(self, devId):
        dev = indigo.devices[devId]
        affected_rooms = self.deviceRoomMap.get(devId, [])

        for room_id in affected_rooms:
            rc = self.roomCache[room_id]
            room = indigo.devices[room_id]
            self.recordTransferOfAuthority(room, rc.get("automationsAuthorized"), False, "DISRUPTION: Caused by " + dev.name)

            self.revokeAAU(room)


###############################################################################################################################
#                                                                                                                             #
#  CACHE SECTION: Moving away from reopeated references to indigo.devices by tracking room and device states.                 #
#                                                                                                                             #
#                 lastreport tracks device state for controlled devices                                                       #                                                                                                            #
#                 - onState (True/False)
#                 - brightness (0-100)
#                 - lastUpdate (epoch)
#                 - source (?)
#
#                 canonical tracks roomify intent per room - why ?                                                            #                                                                                                            #
#                 - onState (True/False)
#                 - brightness (0-100)
#                 - lastUpdate (epoch)
#                 - source (?)
#
#
###############################################################################################################################

    def buildRoomCache(self):


        for room in indigo.devices.iter("self.roomifyRoom"):

            self.cacheRoom(room)

    def cacheRoom(self,room):
        controlled = room.pluginProps.get("controlledDevices") or []
        controlled = [int(x) for x in controlled]
        totalBrightness = 0
        now = time.time()

        for dev_id in controlled:

            device = indigo.devices[dev_id]
            if self.isOn(device):
                if self.isDimmable(device):
                    device_brightness = device.states.get("brightnessLevel")
                else:
                    device_brightness = 100
                totalBrightness += device_brightness

        net = room.states.get("nextEvaluationTime")

        if net == "":
            net = None

        if net is not None:
            if not isinstance(net, (int, float)):
                self.logger.error(
                    f"Invalid nextEvaluationTime for {room.name}: "
                    f"{net!r} ({type(net).__name__})"
                )
                net = None
            else:
                net = float(net)

#        self.logger.error(
#            f"ROOM CACHE BUILD: {room.name} "
#            f"nextEvaluationTime={net!r}, "
#            f"typer={type(net).__name__}"
#        )



        # cache the result in roomCache
        self.roomCache[room.id] = {
            "name": room.name,
            "controlled": controlled, 
            "deviceCount": len(controlled),
            "totalBrightness": totalBrightness,
            "roomifyIntent1": None, #latest
            "roomifyIntent2": None, #prior
            "roomifyIntent3": None, #penultimate
            "alignmentTarget": None,
            "authorityReviewPending": False,
            "lastUpdated": now,
            "deviceReports": {},
            "devicesReporting": 0,
            "automationGateStatus": room.states.get("automationGateStatus", True),
            "automationsAuthorized": room.states.get("automationsAuthorized", True),
            "roomOccupancyAutomationActive": room.states.get("roomOccupancyAutomationActive", True),
            "automationState": room.states.get("automationState", 0),
            "occupied": room.states.get("occupied"),
            "authorityChangeInitiator": room.states.get("authorityChangeInitiator"),
            "nextEvaluationTime": net,
            "nextEvaluationInitiator": room.states.get("nextEvaluationInitiator"),
            "nextEvaluationClass": room.states.get("nextEvaluationClass")
            }

#        self.logger.info(f"Cached roomify room {room.name}")

        derivedBrightness = int(round(totalBrightness / len(controlled) ))
        room.updateStatesOnServer([
            {"key": "brightness", "value": derivedBrightness},
            {"key": "brightnessLevel", "value": derivedBrightness},
        ])

    def dumpRoomCache(self, roomId):

        rc = self.roomCache.get(roomId)

        if rc is None:
            self.logger.info(f"Room cache not found for room id {roomId}")
            return

        self.logger.info(f"========== ROOM CACHE: {rc.get('name', roomId)} ==========")

        for key in sorted(rc.keys()):
            self.logger.info(f"{key:32} : {rc[key]}")

        self.logger.info("=" * 60)

###########################################################################################



    def authorityReview(self, roomId):

        rc = self.roomCache.get(roomId)
        if not rc:
            return

        self.authorityLog(f"Authority review invoked for {rc['name']}")

        #OFF rooms are to be re-authorized regardless of their occupancy status
        #this maybe a place to reset the state of their motuion sensors
        #so that thet are ready to report occupancy when the room is re-occupied
        if rc["automationsAuthorized"] == False and rc["totalBrightness"] == 0:
            self.authorityLog(f"Room '{rc['name']}' is unauthorized and off. Re-authorizing automations.")
            #room is unoccupied and off ... we can re-authorize automations
            self.reAuthorize(indigo.devices[roomId])
        # reinstate automation authority if the room is unoccupied


        rc["authorityReviewPending"] = False
        room = indigo.devices[roomId]
        deviceCount = rc["deviceCount"]
#        if ( rc["devicesReporting"] == deviceCount ) and ( rc["totalBrightness"] != rc["alignmentTarget"] ):
        if ( rc["devicesReporting"] > ( deviceCount/2 ) ) and ( rc["totalBrightness"] != rc["alignmentTarget"] ):
            # majority of devices have reported at least once and the room is not in alignent
            # this could be an opportunity to check for minority reports that might be corrected ?
            # room mihgt be out of alignment yet still authorized
            # if noncompliant reports were treated as if poor device behavior rather than bad intent
            self.automationLog(f"{rc['devicesReporting']} of {deviceCount} {rc['name']} devices reporting {rc['totalBrightness']} of {rc['alignmentTarget']} brightness"  )

            counts = {
                "novel": 0,
                "intended": 0,
                "prior": 0,
                "penultimate": 0
            }

            for dr in rc["deviceReports"].values():
                alignment = dr.get("alignment")
                if alignment in counts:
                    counts[alignment] += 1

            novelCount = counts["novel"]
            intendedCount = counts["intended"]
            priorCount = counts["prior"]
            penultimateCount = counts["penultimate"]
            deviceCount = rc["deviceCount"]

            reportCount = rc["devicesReporting"]

            candidateCount = priorCount + penultimateCount

            majorityCompliant = (intendedCount > (reportCount / 2))

#            majorityCompliant = (intendedCount >= candidateCount)

            self.automationLog(f"devices={deviceCount}  compiant={intendedCount}  novel={novelCount}  prior={priorCount}  penultimate={penultimateCount}")

            #possibly remind misbehaving devices of roomify expectations
#            if (majorityCompliant) and ( candidateCount < 3 ) and (novelCount == 0):
            if (majorityCompliant) and (novelCount == 0):
                #there are a couple of noncompliant device ... lets remind them what to do
                self.automationLog(f">> ROUGUE DEVICE HANDLING BEGINS <<<")

                rogueDeviceId = None
                rogueReport = None
                intent = rc["roomifyIntent1"]

                for devId, dr in rc["deviceReports"].items():
                    if dr["alignment"] in [ "prior", "penultimate" ]:
                        rogueDeviceId = devId
                        rogueDev = indigo.devices[devId]
                        self.automationLog(f"Special handling needed for {dr['alignment']} device {rogueDev.name}")


                        retries = dr["retryCount"]
                        if retries == None:
                            retries = 1
                        else:
                            retries += 1

                        dr["retryCount"] = retries
                        if dr["retryCount"] > 3:
                            continue
                        elif self.globalRemediationEnabled:

                            #ROGUE DEVICE WITH REMEDIATION ENABLED

                            rogueDev = indigo.devices[devId]
                            self.automationLog(f"Reminding {dr['alignment']} device {rogueDev.name} of Roomfy intended brightness {intent}")

                            if self.isDimmable(rogueDev):
                                #ERROR
                                indigo.dimmer.setBrightness(int(devId), intent)
                            else:
                                if intent > 0:
                                    indigo.device.turnOn(devId)
                                else:
                                    indigo.device.turnOff(devId)


            if rc.get("automationsAuthorized") == False:
                if  self.globalAuthorityAutoStandbyRecovery:
                    self.authorityLog(f"Room '{room.name}' is minority non-compliant. Resuming automation authority.")
                    self.recordTransferOfAuthority(room, rc.get("automationsAuthorized"), True, "DEFERRAL ENDED: majority compliant with no novel devices")
                    rc["automationsAuthorized"] = True
                    room.updateStateOnServer("automationsAuthorized", True) 

    def roomJustTurnedOff(self, room):
        #reanimate it
        self.clearOccupancyExpiry(room)
        self.clearNextObligation(room)
        expiry = time.time() + (120)
        displayTime = datetime.datetime.fromtimestamp(
            expiry).strftime("%I:%M:%S %p")

        room.updateStatesOnServer([
            {"key": "occupancyCutoff", "value": expiry},
            {"key": "occupancyCutoffUI", "value": displayTime},
            {"key": "delayedLightingStarttime", "value": None},
            {"key": "outroLightingStarttime", "value": None},
            {"key": "delayedLightingStarttimeUI", "value": None},
            {"key": "outroLightingStarttimeUI", "value": None},
        ])

        rc = self.roomCache[room.id]

        if not rc.get("automationsAuthorized", False):
            #SCHEDULE a re-evaluation of the room in 10 seconds
            if self.globalRoomAutomationCalmingPeriod == None:
                nextTime = time.time()+15
            else:
                nextTime = time.time()+self.globalRoomAutomationCalmingPeriod
            nextName = "Re-evaluate Room"
            self.scheduleRoomEvaluation(room, nextTime, nextName, "OFF")
            rc["authorityReviewPending"] = True


    def confirmNextScheduledObligation(self):
        next_due = min(
            (
                room.get("nextEvaluationTime")
                for room in self.roomCache.values()
                if room.get("nextEvaluationTime") is not None
            ),
            default=None
        )

        if next_due is not None:
            if next_due != self.nextEvaluationDue:
                self.heartbeatLog(f"Next scheduled heartbeat obligations due at {datetime.datetime.fromtimestamp(next_due).strftime('%I:%M:%S %p')}")
                self.nextEvaluationDue = next_due


    def roomTurnedOffDeprecated(self, room):
        rc = self.roomCache.get(room.id)
        if not rc:
            return

        expiry = time.time() + (120)
        displayTime = datetime.datetime.fromtimestamp(
            expiry).strftime("%I:%M:%S %p")

        room.updateStatesOnServer([
            {"key": "occupancyCutoff", "value": expiry},
            {"key": "occupancyCutoffUI", "value": displayTime},
            {"key": "delayedLightingStarttime", "value": None},
            {"key": "outroLightingStarttime", "value": None},
            {"key": "delayedLightingStarttimeUI", "value": None},
            {"key": "outroLightingStarttimeUI", "value": None},
        ])

        #NEXTEVALUATIONTIME

        self.scheduleRoomEvaluation(room, expiry, "Obseervation", "Turned Off")


    def requestRoomStatus(self, roomId):
        room = indigo.devices[roomId]

        self.debugLog(
            f"[Roomify DEBUG] requesting status for {room.name}"
        )

        for deviceId in self.roomCache[roomId]["controlled"]:
            try:
                device = indigo.devices[deviceId]

#                self.debugLog(
#                    f"[Roomify DEBUG] status request → "
#                    f"{device.name} ({device.id})"
#                )
                before = getattr(device, "brightness", None)
                indigo.device.statusRequest(device.id)
                after = getattr(device, "brightness", None)

                self.logger.info(f"[Roomify DEBUG] status request → {device.name} ({device.id}): before:{before} → after:{after}")

            except Exception as e:
                self.logger.error(
                    f"[Roomify DEBUG] status request failed for "
                    f"{deviceId}: {e}"
                )

    def refreshDeviceStatus(deviceId):
            device = indigo.devices[deviceId]

            before = getattr(device, "brightness", None)
            indigo.device.statusRequest(device.id)
            after = getattr(device, "brightness", None)

            if before != after:
                self.logger.info(f"[Roomify DEBUG] Stale Report Corrected → {device.name} ({device.id}): before:{before} → after:{after}")
