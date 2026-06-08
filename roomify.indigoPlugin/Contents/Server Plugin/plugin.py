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

#latest changes:
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

        device.updateStateOnServer("roomOccupancyAutomationActive",newValue)

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

        self.recordTransferOfAuthority(device, oldValue,newValue, "Indugo Callback")

        device.updateStateOnServer("automationsAuthorized",newValue)

    def roomOccupancyX(self, action, device):

        mode = action.pluginTypeId  # e.g. "setNight"

        oldValue = device.states.get("occupied")

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
        now = time.time()
        humanTime = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        self.authorityLog(f"{room.name} automations authorized state from {priorState} to {newState} due to {cause}")
        room.updateStateOnServer("authorityChangePriorState",priorState)
        room.updateStateOnServer("authorityChangeNewState",newState)
        room.updateStateOnServer("authorityChangeInitiator",cause)
        room.updateStateOnServer("authorityChangeTimestamp",humanTime)
        room.updateStateOnServer("authorityChangeEpoch",now)

        

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

        roomLow = parse(room.states.get("autoBrightnessLowLimit"), defaultLow)
        roomHigh = parse(room.states.get("autoBrightnessHighLimit"), defaultHigh)

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

    def recordDeviceReport(self, dev, onState, brightness):
        state = self.lastreport.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        if brightness is not None:
            state["brightness"] = brightness

        state["lastUpdate"] = time.time()
        state["source"] = "Roomify"

        self.lastreport[dev.id] = state


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
    def setHouseModeX(self, action):

        mode = action.pluginTypeId  # e.g. "setNight"
        newMode = mode.removeprefix("set").upper()
        oldMode = self.pluginPrefs.get("houseMode", None)

        if oldMode == newMode:
            self.automationLog(f"HouseMode already {newMode}, ignoring")
            return

        self.automationLog(f"HouseMode change: {oldMode} → {newMode}")
        self.pluginPrefs["houseMode"] = newMode
        self.houseMode = newMode


        # trigger side effects
        self.publishToAllObservers()

        self.recomputeAllRooms()


    def publishToAllObservers(self):
        now = time.time()
        humanTime = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        observers = indigo.devices.iter("self.roomifyObserver")
        for observer in observers:
            self.publishToObserver(observer,humanTime)

    def publishToObserver(self, observer, now):
        observer.updateStateOnServer("houseMode", self.houseMode)

        observer.updateStateOnServer("roomDormancyCutoffEnabled", self.globalRoomDormancyCutoffEnabled)
        observer.updateStateOnServer("occupancyAutomationEnabled", self.globalOccupancyAutomationEnabled)

        observer.updateStateOnServer("roomAutomationCalmingPeriod", self.globalRoomAutomationCalmingPeriod)
        observer.updateStateOnServer("houseModesEnabled", self.globalHouseModesEnabled)

        observer.updateStateOnServer("lastPublishTimestamp", now)

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
            "MORNING": 0.66,
            "DAY": 1.0,
            "EVENING": 0.66,
            "NIGHT": 0.33,
            "AWAY": 1.0,
            "QUIET": 0.4,
            "CLEANING": 2.0,
            "BEDTIME": .20,
            "SLEEP": .00
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

        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)

        return (True, valuesDict)



#   AUTOMATION BLOCK

    def autoRoomBrightness(self, room, key, default=0):

        currentPhase = room.states.get("LightingPhase") 
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

#
        targetBrightness = self.getBoundedTargetBrightness(room, targetBrightness)


        self.autoBrightness(room, targetBrightness)

        
    def autoBrightness(self, room, targetBrightness):
        if self.automationsActionable(room):
            self.turnRoomOn(room, targetBrightness)


    def directRoom(self, room, onState, targetBrightness):
        #self.ignoreNextRoomChange(room, "Roomify-Initiated Change", onState, targetBrightness)
        room.updateStateOnServer("onState", onState)
        room.updateStateOnServer("onOffState", onState)
        room.updateStateOnServer("brightness", targetBrightness)
        room.updateStateOnServer("brightnessLevel", targetBrightness)
        rt = self.getRoomRuntime(room.id)
        rt["auditBurden"] = 0
        rt["auditAttemptsRemaining"] = 4
        rt["auditPending"] = False
        #room.updateStateOnServer("auditBurden", 0)
        #room.updateStateOnServer("auditAttemptsRemaining", 4)
        #room.updateStateOnServer("auditPending", False)

        self.applyTargetStateToDevices(room, onState, targetBrightness)

    def turnRoomOn(self, room, targetBrightness):
        self.automationLog(f"Turning ON room: {room.name} to brightness {targetBrightness}")
        self.directRoom(room, True, targetBrightness)
        self.automationLog(f"Setting watchdog cutoff for room '{room.name}'")
        self.setRoomTimeout(room)
        

    def turnRoomOff(self, room):
        self.automationLog(f"Turning OFF room: {room.name}")

        #maybe off doesn't really mean off ? 
        autoOffBrightness = room.states.get("autoOffBrightness")
        if autoOffBrightness:
            autoOffBrightness = int(autoOffBrightness)
        if autoOffBrightness > 0:
            self.automationLog(f"Auto-off brightness of {autoOffBrightness} detected for room {room.name}, dimming instead of turning off")
            self.turnRoomOn(room, int(autoOffBrightness))
        else:
            self.directRoom(room, False, 0)
            room.updateStateOnServer("lightingPhase", None)
            room.updateStateOnServer("watchdogCutoff", None)
            room.updateStateOnServer("watchdogCutoffDisplay", None)
            #2026-6-6 lets make sure off is off
            #indigo.device.turnOff(room.id)
            self.automationLog(f"Clearing watchdog cutoff for room '{room.name}'")
            self.clearRoomTimeout(room)

    def automationsActionable(self, room):
        gated = True

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
        device = indigo.devices[action.deviceId]
        self.automationLog(f"Toggling occupancy for device: {device.name}")

        current = device.states.get(
            "occupied",
            0)
        
        next = not current
        self.setOccupancy(device, next)

    def setOccupancy(self, room, newState):
        # this one is invoked by occupancy sensations, occuoancy cutoff expiration, or manual intervention
        # IMPORTANT - THIS IS THE PRIMARY INITIATOR OF AUTOMATED LIGHTING CHANGES

        oldState = room.states.get(
            "occupied",
            0)
        stateChange = ( newState != oldState)

        if stateChange:
            self.automationLog(f"Occupancy state for {room.name} changing from {oldState} to {newState}")
            if newState == True:
                # occupancy turned on
                self.setOccupancyExpiry(room)
                if self.automationsActionable(room):
#                    targetBrightness = room.pluginProps.get("initialBrightness") 
#                    self.turnRoomOn(room, targetBrightness)
                    self.autoRoomBrightness(room,"initial")
            else:
                # occupancy turned off
                self.clearOccupancyExpiry(room)
                self.clearNextObligation(room)
                if self.automationsActionable(room):
                    self.turnRoomOff(room)
                else:
                    if not self.isOn(room):
                        room.updateStateOnServer("automationsAuthorized",True)
                        self.evaluateAutomationState(room)

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
            self.scheduleRoomEvaluaiton(room, transitionTime, room.name, "Disruption")

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
        
        
        room.updateStateOnServer("occupied",True)
        room.updateStateOnServer("occupancyCutoff", expiry)
        room.updateStateOnServer("occupancyCutoffUI", displayTime)
        room.updateStateOnServer("delayedLightingStarttime", transitionTime)
        room.updateStateOnServer("outroLightingStarttime", outroTime)
        room.updateStateOnServer("delayedLightingStarttimeUI", transitionTimeUI)
        room.updateStateOnServer("outroLightingStarttimeUI", outroTimeUI)

        

    def clearOccupancyExpiry(self, room):
        room.updateStateOnServer("occupied",False)
        room.updateStateOnServer("occupancyCutoff", None)
        room.updateStateOnServer("occupancyCutoffUI", None)
        room.updateStateOnServer("delayedLightingStarttime", None)
        room.updateStateOnServer("outroLightingStarttime", None)
        room.updateStateOnServer("delayedLightingStarttimeUI", None)
        room.updateStateOnServer("outroLightingStarttimeUI", None)


    # ---------------------------------------------------------
    # 
    # ROOMIFY PLUGIN & MANAGER METHODS UP FRONT
    #     
    # ---------------------------------------------------------


    # runs when plugin loads. good for initializing variables, loading prefs, etc. but not for doing anything with devices since they might not be loaded yet (that's deviceStartComm)
    def startup(self):

        self.roomRuntime = {}
        self.buildRoomTypeDefaults()
        self.recentlyControlled = {}
        self.canonical = {}
        self.lastreport = {}
        self.loadPluginPrefs()

        self.debugLog("[DEBUG]Roomify plugin starting")

        self.houseMode = self.pluginPrefs.get("houseMode", "DAY")
        self.publishToAllObservers()
        
        indigo.devices.subscribeToChanges()
        self.suppressEvaluationDepth = 0
        self.devicesBeingControlled = set()
        self.buildDeviceRoomIndex()
        self.buildIndicatorRoomIndex()
        self.buildVacancyAuthorityRoomIndex()
        self.buildGateRoomIndex()

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

        self.automationLog(f"Globally Authorized Timeouts={self.globalRoomDormancyCutoffEnabled}")
        self.automationLog(f"Globally Authorized Default={self.globalRoomDormancyDefault}")
        self.automationLog(f"Globally Occupancy Automations={self.globalOccupancyAutomationEnabled}")
        self.automationLog(f"Globally Phased Lighting={self.globalPhasedLightingEnabled}")

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
            return self.roomIsOn(dev)
        else:
            return self.deviceIsOn(dev)


    def roomIsOn(self, room):

        room_onState = room.states.get("onState")
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

        device = indigo.devices[action.deviceId]

        device.updateStateOnServer(
            "roomOccupancyAutomationActive",
            True)

        self.evaluateAutomationState(device)

        self.automationLog(
            f"{device.name} room occupancy automations resumed")
        
    def deactivateRoomAutomations(self, action):

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

        device = indigo.devices[action.deviceId]

        device.updateStateOnServer(
            "automationsAuthorized",
            True)


        self.evaluateAutomationState(device)

        self.authorityLog(
            f"{device.name} automation authority granted")
        
        self.evaluateAutomationState(action)

    def revokeAAU(self, device):
        #self.logDecision(device,"Revoking automation authority for device {room.name}")
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
        device = indigo.devices[action.deviceId]
        self.authorityLog(f"Advancing automation status for device: {device.name}")

        current = device.states.get(
            "automationState",
            0)
        
        next = int(current) + 1

        if next == 3:
            next = int(0)

        if next == 0:
            device.updateStateOnServer(
                "roomOccupancyAutomationActive",
                True)
            device.updateStateOnServer(
                "automationsAuthorized",
                False)
            self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), False, "User Set to Standby")

        elif next == 1:
            device.updateStateOnServer(
                "roomOccupancyAutomationActive",
                True)
            device.updateStateOnServer(
                "automationsAuthorized",
                True)
            self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), False, "User Set to Active")
        elif next == 2:
            device.updateStateOnServer(
                "roomOccupancyAutomationActive",
                False)
            device.updateStateOnServer(
                "automationsAuthorized",
                True)
            self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), False, "User Set to Inactive")
            
    
        self.evaluateAutomationState(device)

    def toggleAutomationAuthority(self, action):
        device = indigo.devices[action.deviceId]
        self.authorityLog(f"Toggling automation authority for device: {device.name}")

        current = device.states.get(
            "automationsAuthorized",
            True)

        newValue = not current

        device.updateStateOnServer(
            "automationsAuthorized",
            newValue)

        if newValue:
            self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), False, "User Requested Standby")
        else:
            self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), True, "User Requested Activation")
        

        self.evaluateAutomationState(device)

        self.deviceLog(
            f"{device.name} automation authority toggled to {newValue}")
        
        self.evaluateAutomationState(device)

    

    def closedPrefsConfigUi(self, valuesDict, userCancelled):

        if not userCancelled:
            self.logger.info("Plugin preferences updated")            

            self.loadPluginPrefs()


            createObserver = self.pluginPrefs.get("createObserver", False)
            self.observerId = self.pluginPrefs.get("obsserverName")

            if createObserver and self.observerId == "":

                observerName = self.pluginPrefs.get("obsserverName", "Roomify Observer")
                newDevice = indigo.device.create(indigo.kProtocol.Plugin, address=None, name=observerName, deviceTypeId="roomifyObserver", props=None, folder=None)
                self.pluginPrefs["observerId"] = newDevice.id

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
        
    def deviceUpdated(self, origDev, newDev):

        if origDev.pluginProps != newDev.pluginProps:

            self.debugLog(
                f"[Roomify DEBUG] config updated: {newDev.name}")

            if newDev.deviceTypeId in ["Manager", "roomifyManager"]:
                self.initializemanager(newDev)

            elif newDev.deviceTypeId in ["Room","roomifyRoom"]:
                self.initializeRoom(newDev)



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

        return disrupted


    def isDisrupted(self, device):

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

        # 1. Validate device type
        if device.deviceTypeId not in [ "Room", "roomifyRoom" ]:
            self.debugLog("Ignored: not a Room  device (%s)" % device.name)
            return False

        # 2. Global automation gate
        if not self.globalOccupancyAutomationEnabled:
            self.automationLog("Global automations disabled")
            return False

        # 3. Local device automation flag (pluginProps)
        props = device.pluginProps
        if not props.get("roomOccupancyAutomationActive", "true") == "true":
            self.automationLog("Device automations disabled: %s" % device.name)
            return False

        # 4. Authorization check
        if not props.get("automationsAuthorized", "false") == "true":
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

        # but actually apply this change ? maybe conditionally, but i cant think through that right now.
        # PERHAPS ONLY IF THE ROOM IS ON AND AUTHORIZATIONS are currently auth
        #if device.states.get("onState", True) and self.occupancyAutomationEnabled(device):
        #    self.applyTargetStateToDevices(room, True )


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


        is_indicator = newDev.id in self.indicatorRoomMap
        is_controlled = newDev.id in self.deviceRoomMap
        is_gate = newDev.id in self.gateRoomMap

        is_vacancyAuthority = newDev.id in self.vacancyAuthorityRoomMap

        if not ( is_indicator or is_controlled or is_gate or is_vacancyAuthority ):
            return



        # FIRST FILTER - is this state report any different from the previous state report
        previous = self.lastreport.get(newDev.id, {})

        new_on_report = getattr(newDev, "onState", None)
        old_on_report = previous.get("onState")

        new_brightness_report = getattr(newDev, "brightness", None)
        if new_brightness_report == None:
            new_brightness_report = getattr(newDev, "brightness", None)
        old_brightness_report = previous.get("brightness")

        on_change_reported = (new_on_report != old_on_report)

        if old_brightness_report is None:
            old_brightness_report = 0

        brightness_changed = False
        if new_brightness_report is not None and old_brightness_report is not None:
            brightness_changed = abs(new_brightness_report - old_brightness_report) > 2

        report_changed = on_change_reported or brightness_changed

        if not report_changed:
#            self.debugLog(f"Ignoring redundant report from {newDev.name} of ON={new_on_report} and brightness={new_brightness_report}")
            return  # 🚫 pure duplicate noise, ignore completely
        
        #czewski
        self.deviceLog(f"Processing fresh report from {newDev.name}  of ON={new_on_report} and brightness={new_brightness_report}")

        #to quite the noise of repeated device reports, record this one
        self.recordDeviceReport(newDev, newDev.onState, getattr(newDev, "brightness", None))


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
            if hasattr(newDev, "onState"):
               if getattr(origDev, "onState", None) != newDev.onState:
                    changed = True
                    changedAspect = changedAspect + "onState "


            # ---- Brightness check (safe Indigo dimmers) ----
            if hasattr(newDev, "brightnessLevel"):
                old_brightness = getattr(origDev, "brightnessLevel", None)
                new_brightness = newDev.brightnessLevel
                delta_brightness = (abs((old_brightness or 0) -  (new_brightness or 0)))
                if delta_brightness > 1:
                    changed = True
                    changedAspect = changedAspect + "brightnessLevel from " + str(old_brightness) + " to " + str(new_brightness)

            # ---- Brightness check (safe Indigo dimmers) ----
            if hasattr(newDev, "brightness"):
                new_brightness = newDev.brightness
                old_brightness = getattr(origDev, "brightness", None)
                delta_brightness = (abs((old_brightness or 0) - (new_brightness or 0)))
                if delta_brightness > 1:
                    changed = True
                    changedAspect = changedAspect + "brightness from " + str(old_brightness) + " to " + str(new_brightness)

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

                changed = False
                #changedAspect = ""
                disrupted = self.isDisrupted(newDev)
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
                if  self.isDisrupted(room):
                    self.recordTransferOfAuthority(room, room.states.get("automationsAuthorized"), False, newDev.name)
                    room.updateStateOnServer(
                        "automationsAuthorized",
                        False)

                #self.evaluateAutomationState(room)

                if new_on_report:
                    #room will almost certainly land at "on-ish" so lets get in front of that state change inidcator
                    room.updateStateOnServer("onState", True)
                    self.errorLog(f"{room.name} {room.deviceTypeId} onState getting set to True in repsponse to {newDev.name}")
                self.evaluateRoomLighting(room,f"{newDev.name} changed")
                evalTime = time.time() + self.globalRoomAutomationCalmingPeriod

                self.scheduleRoomEvaluaiton(room, evalTime, newDev.name, "Disruption")

            if self.isOn(newDev) and self.globalOccupancyAutomationEnabled:
                self.debugLog(f"{newDev.name} reporting on state")
                sensed_rooms = self.indicatorRoomMap.get(newDev.id, [])
                for room_id in sensed_rooms:
                    room = indigo.devices[room_id]
                    self.automationLog(f"Presence indicated in {room.name}") 
                    self.setOccupancy(room, True)

               

        except Exception as e:
            self.errorLog(f"[Roomify ERROR] deviceUpdated: {e}")        

    def identifyNextRoomObligation(self, room):


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

        self.scheduleRoomEvaluaiton(room, nextTime, nextName, "Heartbeat")


    def scheduleRoomEvaluaiton(self, room, evalTime, eCause, eClass):
        humanTime = ""
        if evalTime:
            humanTime = datetime.datetime.fromtimestamp(evalTime).strftime("%H:%M:%S")

        room.updateStateOnServer("nextEvaluationTime",evalTime)
        room.updateStateOnServer("nextEvaluationTimeUI",humanTime)
        room.updateStateOnServer("nextEvaluationInitiator",room.name)
        room.updateStateOnServer("nextEvaluationClass",eClass)


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

        device.updateStateOnServer("automationGateStatus", True)
        roomOccupancyAutomationActive = device.pluginProps.get(
            "roomOccupancyAutomationActive", True)

        initialBrightness = device.pluginProps.get(
            "initialBrightness", 80)
        
        #CZEWSKI
        #If a room changes, all theses mapping are subject to change, so we need to rebuild all the indexes that rely on those mappings
        #self.buildDeviceRoomIndex()
        #self.buildIndicatorRoomIndex()
        #self.buildVacancyAuthorityRoomIndex()
        #self.buildGateRoomIndex()

        self.checkGates(device)
        
        self.evaluateAutomationState(device)

        device.updateStateOnServer(
            "autoOffBrightness",
            device.pluginProps.get("autoOffBrightness"))

        self.initializeRoomBrightnessState("initial", device)
        self.initializeRoomBrightnessState("delayed", device)
        self.initializeRoomBrightnessState("outro", device)

        device.updateStateOnServer("automationState", device.states.get("automationState", 0))

        #maybe not though?
        # self.recomputeRoom(device)

        self.deviceLog(f"Initialized room: {device.name}")      
 

    def clearRoomTimeout(self,room):
         
#        room.updateStateOnServer("lightingPhase", "")
        room.updateStateOnServer("watchdogCutoff", None)
        room.updateStateOnServer("watchdogCutoffDisplay", None)  
        room.updateStateOnServer("lightingPhase", None)     

    def setRoomTimeout(self, room):

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
        
        room.updateStateOnServer("watchdogCutoff", expiry)
        room.updateStateOnServer("watchdogCutoffDisplay", displayTime)


    def evaluateRoomLighting(self, room, cause):

        # I expect this routine to run only when an EXTERNAL ACTOR changes device that is part of the collected devices for a given room
        # even though the room state might not be changing ... this still should change the expiry timing
        # no idea WHY I would end up here when a collected sensor cahnges

        self.deviceLog(f"Evaluating lighting for room: {room.name}")


        controlled_ids = [int(x) for x in room.pluginProps.get("controlledDevices", [])]

        any_on = False
        max_brightness = 0

        brightnessPotential = 0
        brightnessEncountered = 0

        alreadyOn = self.isOn(room)
        alreadyAuthorized = room.states.get("automationsAuthorized")

        for dev_id in controlled_ids:

            dev = indigo.devices[dev_id]
            if dev.onState:
                any_on = True

            #lets track how beight the room is yes?
            brightnessPotential += 100
            if self.isDimmable(dev):
                b = int(dev.states.get("brightnessLevel",0))
                brightnessEncountered += b
            else:
                if dev.onState:
                    brightnessEncountered += 100

        brightnessPercentage = int(100*(brightnessEncountered/brightnessPotential))
        self.deviceLog(f"Perceived brightness in {room.name} calculated at {brightnessEncountered} of {brightnessPotential} aka {brightnessPercentage}")
        room.updateStateOnServer("brightness",brightnessPercentage)

        if any_on:
            # set a fresh watchdog timestamp.
            self.automationLog(f"Confirming watchdog cutoff for room '{room.name}'")
            self.setRoomTimeout(room)
            if alreadyAuthorized:
                self.recordTransferOfAuthority(room, room.states.get("automationsAuthorized"), False, f"{cause} outside of Roomify intent")
                if  self.globalAuthorityAutoStandbyRecovery:
                    self.authorityLog(f"{room.name} surrendering automation authority per '{cause}'")
                    self.revokeAAU(room)
                else:
                    self.authorityLog(f"{room.name} {cause} ignored as auto standby is not enabled")
        else:
            self.deviceLog(f"Clearing watchdog cutoff for room '{room.name}'")
            self.clearRoomTimeout(room)
            # only reinstate automation authority if the room is unoccupied
            if alreadyAuthorized == False:
                if not room.states.get("occupied", False):
                    if  self.globalAuthorityAutoStandbyRecovery:
                        self.authorityLog(f"Room '{room.name}' is unoccupied & off: resuming automation authority.")
                        self.recordTransferOfAuthority(room, room.states.get("automationsAuthorized"), True, "Vacant room settled into an OFF state")
                        room.updateStateOnServer("automationsAuthorized", True) 
                    else:
                        self.authorityLog(f"Room '{room.name}' is unoccupied & off [BUT] resuming automation authority is not enble.")
                else:
                    if self.globalAuthorityAutoStandbyRecovery:
                        self.authorityLog(f"Room '{room.name}' is occupied and off: retaining automation authority")
 
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
        try:

            requestedState = self.resolveRequestedState(action, device)
            # ---- TURN ON ----
            if requestedState == True:
                self.authorityLog(f"ON requested: {device.name} at brightness {action.actionValue}")
                targetBrightness = action.actionValue 
                if targetBrightness == 0:
                    targetBrightness= device.states.get("initialBrightness")
                #self.ignoreNextRoomChange(device, "ON requested", True, action.actionValue)
                self.turnRoomOn(device, targetBrightness)
#                device.updateStateOnServer("onOffState", True)
#                device.updateStateOnServer("onState", True)
#                self.setRoomTimeout()
    
#                self.applyTargetStateToDevices(device, True, device.states.get("initialBrightness") or 50)
#                self.automationLog(f"Device turned ON via action: {device.name} ... setting automationsAuthorized to False to prevent feedback loop")
                if self.globalAuthorityAutoStandbyRecovery:
                    self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), False, "Room ON Command Processed")
                    device.updateStateOnServer("automationsAuthorized", False)
                    self.evaluateAutomationState(device)
                return

            # ---- TURN OFF ----
            if requestedState == False:
                self.authorityLog(f"OFF requested: {device.name}")
                self.turnRoomOff(device)
                if self.globalAuthorityAutoStandbyRecovery:
                    self.recordTransferOfAuthority(device, device.states.get("automationsAuthorized"), True, "Room OFF Command Processed")

                    device.updateStateOnServer("automationsAuthorized", True)
                 
                    self.evaluateAutomationState(device)

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
        room_is_on = room.states.get("onState", False)
        room_brightness = room.states.get("brightness", 0)
        #self.ignoreNextRoomChange(room, "Roomify-Initiated Change", room_is_on, room_brightness)
        self.automationLog(f"Executing divergence resolution for {room.name}")
        self.applyTargetStateToDevices(room, room_is_on, room_brightness)

    def applyTargetStateToDevices(self, room, room_is_on, room_brightness ):
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

            controlled_ids = room.pluginProps.get("controlledDevices") or []
            controlled_ids = [int(x) for x in controlled_ids]
            self.automationLog(f"Roomify -> {room.name}/{room_is_on}/{intendedState} ")

            divergence_count = 0
            
            for dev_id in controlled_ids:

                dev = indigo.devices[dev_id]
                #this is where we need to record intent so we dont wrongly register a disruption
                #v1 probably relied entirely on *ignore next room chages* thinking
                #v2 needs to rencile the *chage* report with the outcome, which is surely
                #what these two functions are reaching for 

                if not self.isDivergent(dev, room_is_on, room_brightness):
                    continue

                divergence_count += 1

                self.recordRoomifyIntent(dev, room_is_on, room_brightness)
                # stuffs expected outcome into canonical

                self.suppressDev(dev_id, "Applying Room State", room_is_on, room_brightness)
                # stuffs expected outcome into recently controlled

                is_dimmer = self.isDimmable(dev)

                self.debugLog(f" - Applying {room_is_on} at {room_brightness}% to {dev.name} (id: {dev_id}) ... dimmable={is_dimmer} ... room_brightness={room_brightness}")
                # ---- ON / OFF ----
                if room_is_on:
                    if is_dimmer:
                        #CZEWSKI
#                       self.debugLog(f" - Applying {room_is_on} at {room_brightness}% to {dev.name} (id: {dev_id}) ... dimmable={is_dimmer} ... room_brightness={room_brightness}")
                        #self.sleep(0.3)
                        if not self.isOn(dev):
                            indigo.device.turnOn(dev_id) #to confirm on state for devices that dont reliably report brightness changes as on state changes                    
                            indigo.dimmer.setBrightness(dev_id, int(room_brightness))
                        else:
                            indigo.dimmer.setBrightness(dev_id, int(room_brightness))
                    else:
                        indigo.device.turnOn(dev_id)
                else:
                    indigo.device.turnOff(dev_id)
                continue
#                self.sleep(0.25)

            #DIVERGENCE HANDLING

            rt = self.getRoomRuntime(room.id)
            rt["auditBurden"] = divergence_count

 #           room.updateStateOnServer("auditBurden", divergence_count)
 #           room.updateStateOnServer("divergenceCount", divergence_count)

            self.automationLog(f"{divergence_count} devices needed to be updated to achieve the intended state for {room.name}")
            if divergence_count > 0:
                auditAttemptsRemaining = rt["auditAttemptsRemaining"]
                if auditAttemptsRemaining > 0:
                    auditAttemptsRemaining -= 1
                    rt["auditPending"] = True
                    rt["auditAttemptsRemaining"] = auditAttemptsRemaining
#                    room.updateStateOnServer("auditPending", True)
#                    room.updateStateOnServer("auditAttemptsRemaining", auditAttemptsRemaining)
                    self.scheduleRoomEvaluaiton(room, time.time()+self.globalRoomAutomationCalmingPeriod, room.name, "Divergence Resolution")
            else:
                rt["auditPending"] = False
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

        self.debugLog(f"Evaluating automation state for {room.name}")

        if room.deviceTypeId not in [ "Room", "roomifyRoom" ]:
            return

        automations_enabled = room.states.get("roomOccupancyAutomationActive", True)
        automations_authorized = room.states.get("automationsAuthorized", True)
        gated = room.states.get("automationGateStatus")

        if (gated is None) or (gated == "") or (gated == "none"):
            self.debugLog(f"No gate status for {room.name}, treating as ungated")
            gated = True

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

        room.updateStateOnServer("automationState", automation_state)
        room.updateStateOnServer("automationStateUI", automation_stateUI)
            

    def checkGates(self, room):
        self.debugLog(f"Checking gates for {room.name}")
        gateStatus = self.isGated(room)
        room.updateStateOnServer("automationGateStatus", gateStatus)
        self.evaluateAutomationState(room)

    def isGated(self, room):

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


    def considerReauthorization(self,room):

        #heartbeat invokes this method to bring rooms out of suspended authrization when appropriate

        if room.states.get("automationsAuthorized"):
            #no need to re-authorize a room thaty is already authorized
            return
        
        if room.states.get("occupied"):
            # ROOM IS NOT AUTHORIZED BUT IT IS OCCUPIED
            # NO NEED TO RECONSIDER AGAIN UNTIL OCCUPANCY CHANGES?
            #we don't assert authority in occupied spaces. 
            return
        
        on = self.isOn(room)
#        self.debugLog(f"isOn returned {on} for Room {room.name} ")
        if on:
            #we don't assert authority in rooms that have been left on with apparent intent
#            self.logDecision(room, f"{room.name} is *on* and not subject to reAuthorization.")
#           but maybe we need to check onState again soon ?
#            self.scheduleRoomEvaluaiton(room, time.time()+30, room.states.get("nextEvaluationInitiator"), "Disruption+")
            return
#        else:
#            self.debugLog(f"{room.name} with onState = {room.states.get("onState")} is considered OFF by isOn")

        #we know this room to be unauthorized, vacant and off. so lets re-authorize it
        self.reAuthorize(room)
        self.clearNextObligation(room)

    def clearNextObligation(self, room):
        room.updateStateOnServer("nextEvaluationTime", None)
        room.updateStateOnServer("nextEvaluationTimeUI", None)
        room.updateStateOnServer("nextEvaluationInitiator", None)
        room.updateStateOnServer("nextEvaluationClass", None)


    def reAuthorize(self,room):
        room.updateStateOnServer("automationsAuthorized", True)
        self.evaluateAutomationState(room)
        self.logDecision(room,"Re-authorizing Automations")

    #heartbeat
    def runConcurrentThread(self):

        self.logger.info("Roomify heartbeat thread started")

        try:
            while True:

                now = time.time()

                if not self.configStable:
                    if self.configChangedDeviceId:
                        self.reInitRoom(self.configChangedDeviceId)
                    else:
                        self.loadPluginPrefs()

                for room in indigo.devices.iter(self.pluginId):

                    if room.deviceTypeId != "roomifyRoom":
                        continue
                    
                    self.considerReauthorization(room)
                    self.identifyNextRoomObligation(room)
#dormancy cutoff comes first

                    # TIMEOUT BLOCK
#                        if room.states.get("timeoutsEnabled", True) and self.roomDormancyCutoffEnabled:
                    if self.globalRoomDormancyCutoffEnabled and room.states.get("roonDormancyCutoffActive", False):
                    
                        # --- Get expiry time ---
                        cutoff = room.states.get("watchdogCutoff")

                        if cutoff:

                            cutoff = float(cutoff)

                            if now >= cutoff:
                                self.automationLog(f"Timeout expired for room '{room.name}'")
                                self.turnRoomOff(room)
                                cutoff = 0

#lets lighten the heartbeat and skip past rooms not subhect to automation
#after reauthorizing if appropriate

                    #if not self.isOn(room):
                    #    #everything an OFF or DORMANCY room needs has been handled
                    #    continue

#                    if self.occupancySustained(room):
#                        self.identifyNextRoomObligation(room)
#                        continue

                    next_evaluation_time = room.states.get("nextEvaluationTime")

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
                        if rt["auditPending"]:
#                        if room.states.get("auditPending", True):
                            self.applyRoomStateToDevices(room)

 

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
                                transitionTime = 0


                        if outroTime and (now >= outroTime):
                            if not self.occupancySustained(room):
                                self.automationLog(f"'{room.name} phase change invoked: delayed -> outro")
                                #targetBrightness = room.pluginProps.get("outroBrightness")
                                room.updateStateOnServer("outroLightingStarttime", None)
                                room.updateStateOnServer("outroLightingStarttimeUI", None)
                                self.autoRoomBrightness(room, "outro")
                                outroTime = 0

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
                                    room.updateStateOnServer("lightingPhase", None)
                                    room.updateStateOnServer("nextEvaluationTime",None)

                                    self.automationLog(f"Automation period expired for room '{room.name}'")
                                    self.setOccupancy(room,False)                                
                                    expiry = None


                    except Exception as e:
                        self.logger.error(f"Heartbeat error ({room.name}): {e}")

                    if next_evaluation_time:
                        self.identifyNextRoomObligation(room)

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
                #self.scheduleRoomEvaluaiton(room,next_evaluation_time,nextReason,"Heartbeat")

                # --- Sleep interval (tune this) ---
                self.sleep(5)  # check every minute

        except self.StopThread:
            self.logger.info("Roomify heartbeat thread stopped")

