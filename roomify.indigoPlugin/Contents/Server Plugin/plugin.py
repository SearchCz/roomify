"""
Securify Plugin

Copyright (c) 2026 Daniel Czewski

This software is licensed under the Securify Community License v1.0.
See LICENSE.md for full terms.

Redistribution and modification must preserve this notice.
"""

#changes in observer state(s) invole deviceUpdated
#actions in reponse to those changes are brokered there

from unittest import case

import indigo
import threading
import time
import datetime
import uuid
import random
from packaging.version import Version

MIN_ROOMIFY_SECURITY_VERSION = Version("1.3.0")

class Plugin(indigo.PluginBase):

    def toBool(self, value):
        if isinstance(value, bool):
            return value
        return str(value).lower() in ["true", "yes", "on", "1"]


    def getCompromisedCheckpoints(self, classification):
        self.logResponse(f"...compiling a list of checkpoints classified as {classification}")

        compromisedCheckpoints = []

        for checkpointId, checkpoint in self.checkpoints.items():

            # Skip the summary record
            if int(checkpointId) == 0:
                continue

            classy = checkpoint.get("alertClassificationUI", "")
            self.logResponse(f"{checkpoint.get('name')} classified as {classy}")

            if classy == classification:
                compromisedCheckpoints.append(checkpoint)

        return compromisedCheckpoints


    def getExposureBody(self, classification, alertScore, compromisedCheckpoints):
        lines = []

        lines.append(f"Exposure Index: {alertScore}")
        lines.append(f"Classification: {classification.title()}")
        lines.append("")
        lines.append("Compromised checkpoints:")

        if not compromisedCheckpoints:
            lines.append("- None reported.")
        else:
            for checkpoint in compromisedCheckpoints:
                lines.append(f"- {checkpoint.get("name")}")

        return "\n".join(lines)    

    def ordinal(self,n):

        if 10 <= n % 100 <= 20:

            suffix = "th"

        else:

            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

        return f"{n}{suffix}"


    def getExposureBlurb(self, observerName, classification, alertScore, iteration, max):
        """
        Returns a human-friendly exposure notification.

        observerName    Name of the Observer (e.g. "Night Watch")
        classification  allclear, normal, noteworthy, significant, serious, critical
        alertScore      Optional Exposure Index score (0-100)
        """

        preamble = ""

        if iteration == 0:
            preamble = ""
        else:
            if iteration == max:
                preamble = self.ordinal(iteration) + " and Final Reminder: "
            else:
                preamble = self.ordinal(iteration) + " Reminder: "

        suffix = ""
        if classification == "normal.":
            suffix = "All checkpoints are withjing tolerance!"
        if classification == "noteworthy":
            suffix = "Consider reviewing checkpoints!"
        if classification == "significatnt":
            suffix = "Attention is recommended!"
        if classification == "serious":
            suffix = "Prompt attention is advised!"
        if classification == "critical":
            suffix = "Immediate attention is required!"

        return f"{preamble} Securify Condition is now {classification}. {suffix}"        



    def getExposureMessage(self, observerName, classification, alertScore, iteration, max):
        """
        Returns a human-friendly exposure notification.

        observerName    Name of the Observer (e.g. "Night Watch")
        classification  allclear, normal, noteworthy, significant, serious, critical
        alertScore      Optional Exposure Index score (0-100)
        """

        preamble = ""

        if iteration == 0:
            preamble = ""
        else:
            if iteration == max:
                preamble = self.ordinal(iteration) + "and Final Reminder: "
            else:
                preamble = self.ordinal(iteration) + " Reminder: "




        exposureMessages = {
            "allclear": (
                ["reports", "indicates", "confirms"],
                "all monitored security concerns have been resolved."
            ),

            "normal": (
                ["reports", "indicates", "suggests"],
                "home security conditions are within normal expectations."
            ),

            "noteworthy": (
                ["noticed", "suggests", "indicates"],
                "a security condition deserves your attention."
            ),

            "significant": (
                ["reports", "indicates", "has identified"],
                "meaningful security concerns."
            ),

            "serious": (
                ["indicates", "warns", "reports"],
                "the home's security posture requires prompt attention."
            ),

            "critical": (
                ["warns", "recommends", "indicates"],
                "immediate attention to the home's security is recommended."
            )
        }

        verbs, message = exposureMessages.get(
            classification,
            (["reports"], "an unknown security condition.")
        )

        verb = random.choice(verbs)

        if alertScore is None:
            return f"{observerName} {verb} {message}"

        return f"{preamble} {observerName} {verb} {message} (Exposure: {classification})"


    def getExposureClassification(self, alertScore):
        alertScore = max(0, min(int(alertScore), 100))

        if alertScore == 0:
            return 0
        elif alertScore <= 20:
            return 1
        elif alertScore <= 40:
            return 2
        elif alertScore <= 60:
            return 3
        elif alertScore <= 80:
            return 4
        else:
            return 5    


    def getExposureClassificationUI(self, alertScore):
        alertScore = max(0, min(int(alertScore), 100))

        if alertScore == 0:
            return "allclear"
        elif alertScore <= 20:
            return "normal"
        elif alertScore <= 40:
            return "noteworthy"
        elif alertScore <= 60:
            return "significant"
        elif alertScore <= 80:
            return "serious"
        else:
            return "critical"    

    def getEmailDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        items = [("0", "Select Email+ SMTP Server")]

        for dev in indigo.devices:
            #com.indigodomo.email
            #if dev.pluginId == "com.indigodomo.email" and dev.deviceTypeId == "smtpServer":
            if dev.pluginId == "com.indigodomo.email":
                items.append((str(dev.id), dev.name))

        items.sort(key=lambda x: x[1].lower() if x[0] != "0" else "")
        return items    

    def getActionGroupList(self, filter="", valuesDict=None, typeId="", targetId=0):
        action_groups = []

        for ag in indigo.actionGroups:
            action_groups.append((str(ag.id), ag.name))

        action_groups.sort(key=lambda x: x[1].lower())
        return action_groups

    def getInformifyList(self, filter="", valuesDict=None, typeId="", targetId=0):
        items = []

        for dev in indigo.devices:
            items.append((str(dev.id), dev.name))
            items.sort(key=lambda x: x[1].lower() if x[0] != "0" else "")

        return items    

    def getVariableList(self, filter="", valuesDict=None, typeId="", targetId=0):
        variableList = []

        for var in indigo.variables:
            variableList.append((str(var.id), var.name))

        variableList.sort(key=lambda x: x[1].lower())
        return variableList

    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):

        if pluginProps is None:
            pluginProps = indigo.Dict()

        roomifyEnabled = self.pluginPrefs.get("roomifyCooperationEnabled", False)
        pluginProps["roomifyCooperationEnabled"] = "true" if roomifyEnabled else "false"

        return (pluginProps, indigo.Dict())
    
    def checkpointTypes(self, filter="", valuesDict=None, typeId="", targetId=0):

        menu = [ ( "DOOR", "Door (+Lock)" ),
                 ( "MOTION", "Motion Detector" ),
                 ( "FAULT", "Fault Sensor" )
        ]

        if self.roomifyCooperationEnabled:
            self.logIntegration("Roomify cooperation is in force")
            menu.append (("OCCUPANCY", "Roomify Occupancy" ))

        return menu

    def roomDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        
        menu = [("none", "(none)")]
        for dev in indigo.devices:
            if dev.deviceTypeId == "roomifyRoom":
                menu.append((str(dev.id), dev.name))

        menu.append(("none","(none)"))
        return menu


    def deviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        
        menu = [("none", "(none)")]
        for dev in indigo.devices:
            menu.append((str(dev.id), dev.name))

        menu.append(("none","(none)"))
        return menu

    def evaluateAllX(self, action):
        self.recomputeAllCheckpoints()

    def suggestHouseMode(self, newMode):
        #this is the entry point for securify to suggest that other plugins adopt a new housemode
        if self.suspendCrossTalk:
            self.logIntegration("Messaging suspended. Not suggesting house mode.")
            self.suspendCrossTalk = False
            return
        if self.roomifyPlugin and self.roomifyPlugin.isEnabled():
            x = "set" + newMode.capitalize() + "Suggested"
            self.logIntegration(f"Suggesting house mode {newMode} to Roomify. Action {x}")
            try:
                self.roomifyPlugin.executeAction(x)
            except Exception as e:
                self.logIntegration(f"Failed to suggest house mode {newMode} to Roomify: {e}","warning") 
        else:
            self.logIntegration("Roomify plugin not available or not enabled. Cannot suggest house mode.","warning")

    def considerHouseModeX(self, action):
        #this is the entry point for roomify to suggest we adopt a new housemode
        #since the roomify plugin is not a dependency, we will only do this if 
        #securify allows this cooperation 
        if self.roomifyCooperationEnabled:
            newMode = action.pluginTypeId.removeprefix("set").removesuffix("Suggested").upper()
            self.suspendCrossTalk = True
            self.logIntegration(f"Accepting suggested house mode {newMode}")
            self.setHouseMode(newMode)
        self.suspendCrossTalk = False


    def shareHouseModeX(self, action):
        #this is how we responde to requests for our current houseMode
        return self.houseMode

    def requestHouseMode(self, action):
        if self.roomifyPlugin and self.roomifyPlugin.isEnabled():
            newMode = self.roomifyPlugin.executeAction("shareHouseMode")
            self.logIntegration(f"Recieved house mode {newMode} from Roomify")
            self.suspendCrossTalk = True
            self.setHouseMode(newMode)
            self.suspendCrossTalk = False
            return True
        else:
            self.logIntegration("Roomify plugin not available or not enabled. Cannot obtain house mode.","warning")
            return False
        

    def setHouseModeX(self, action):

        mode = action.pluginTypeId  # e.g. "setNight"
        newMode = mode.removeprefix("set").upper()
        self.setHouseMode(newMode)

    def focusTargetList(self, filter="", valuesDict=None, typeId="", targetId=0):

        menu = [ "-","----------------" ]
        menu.append(("0", "*** Cumulative Home Exposure ***"))
        for dev in indigo.devices.iter("self.securifyCheckpoint"):
            menu.append((str(dev.id), dev.name))
#       menu.append(("none","(none)"))
        return menu


    def evaluateChange(self,targetId,oldScore,newScore,newClassification):

        if oldScore == newScore:
            return
        
        rawDelta = oldScore - newScore
        delta = int(newScore/20) - int(oldScore/20)


        if (oldScore == 0 or newScore == 0):
            delta = rawDelta

        checkpointName = self.checkpoints[targetId].get("name", f"Checkpoint {targetId}")

        self.logObserver(
        f"Activating observers focused on {checkpointName} classification {newClassification} or alert score changing from {oldScore} to {newScore}"
        )
 
        if delta == 0:
            return
        
        for observerId, observer in self.observers.items():
            if not observer.get("enabled"):
                continue

            if observer.get("target") != targetId:
                continue

            #CZEWSKI
            activated = False
            activator = observer.get("activator")

            if activator == "increase" and delta > 1:
                activated = True
            elif activator == "decrease" and delta < 1:
                activated = True
            elif activator == "anychange" and delta != 0:
                activated = True
            elif activator == newClassification:
                activated = True



            if activated:
                self.logObserver(f"Checkpoint {checkpointName} {activator} --> Observer {observer.get("name")} activating")
            else:
                self.logObserver(f"Checkpoint {checkpointName} {activator} --> Observer {observer.get("name")} de-activating")

    def publishToAllObserversDeprecated(self):
        now = time.time()
        humanTime = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        observers = indigo.devices.iter("self.securifyObserver")
        for observer in observers:
            self.logObserver(f"Publishing to observer {observer.name}")
            self.publishToObserver(observer,humanTime)

    def publishToObserverDeprecated(self, observer, now):
        observer.updateStatesOnServer([
            {"key": "watchfulness", "value": self.watchfulness},
            {"key": "houseMode", "value": self.houseMode},
            {"key": "lastPublishTimestamp", "value": now},
            {"key": "vulnerabilityCount", "value": self.vulnerabilityCount},
            {"key": "breachCount", "value": self.breachCount},
            {"key": "vulnerabilityMax", "value": self.vulnerabilityMax},
            {"key": "breachMax", "value": self.alertMax},
            {"key": "alertClassification", "value": self.alertClassification},
        ])

        if self.alertClassificationUI == observer.pluginProps.get("exposureFocus"):
            #CZEWSKI - TURN IT ON
            self.logObserver(f"--> ACTIVATION CONDITIONS MET FOR {observer.name}")

            if not self.isOn(observer):
                self.logObserver(f"Activating observer {observer.name}")
                indigo.device.turnOn(observer.id) 
                #self.observers(observer)
        else:
            #CZEWSKI - TURN IT OFF
            indigo.device.turnOff(observer.id)
            self.logObserver(f"De-activating observer {observer.name}")

    def observerResponses(self, observer, iteration, max):

        self.logResponse(f"Observer {observer.name} running response {iteration} of {max}")

        responseAuthorized = self.getResponseAuthorization(observer)

        self.observers[observer.id]["responseAuthorized"] = responseAuthorized

        observer.updateStateOnServer("responseAuthorized", responseAuthorized)

        if not responseAuthorized:
            self.logResponse(f"Observer {observer.name} is not authorized to respond. Skipping response.")
            return

        focusTarget = int(observer.pluginProps.get("focusTarget",0))

        summary = self.checkpoints[focusTarget]

        #this might be a problem, as de dont know whcik checkpoint this observer is responding to
        #i take that back ... the observer knows its focus


        blurb = self.getExposureBlurb(
            observer.name,
            summary.get("alertClassificationUI", ""),
            summary.get("alertMax", 0),
            iteration,
            max)


        notification = self.getExposureMessage(
            observer.name,
            summary.get("alertClassificationUI", ""),
            summary.get("alertMax", 0),
            iteration,
            max)

        compromisedCheckpoints = self.getCompromisedCheckpoints(summary.get("alertClassificationUI", ""))
        body = self.getExposureBody(
            summary.get("alertClassificationUI", ""),
            summary.get("alertScore", 0),
            compromisedCheckpoints)

        if observer.pluginProps.get("log"):
            self.logIt(notification)

        if observer.pluginProps.get("announce"):
            indigo.server.speak(notification)

        if observer.pluginProps.get("action"):
            ag = observer.pluginProps.get("actionGroup")
            if ag and ag != "none" and ag != 0 and ag != "0":
                ag = int(ag)
                indigo.actionGroup.execute(ag)


        if observer.pluginProps.get("pushover"):
            pushoverDevice = observer.pluginProps.get("pushoverDevice")
            pushoverPriority = observer.pluginProps.get("pushoverPriority")
            pushoverSound = observer.pluginProps.get("pushoverSound")
            #pushoverPriority = int(pushoverPriority)

            #compromisedCheckpoints = self.getCompromisedCheckpoints(self.alertClassificationUI)
            self.push(
                blurb, body, pushoverSound, pushoverPriority, pushoverDevice)


        if observer.pluginProps.get("email"):
            #CZEWSKI
            emailTo = observer.pluginProps.get("emailTo")
            emailCC = observer.pluginProps.get("emailCC")
            emailBCC = observer.pluginProps.get("emailBCC")
            emailDevice = observer.pluginProps.get("emailDevice")
            #SEND THAT EMAIL
            # Target the built-in Email+ plugin ID

            self.sendEmailNotification(emailDevice, emailTo, emailCC, notification, body)

        if observer.pluginProps.get("storage"):
            storageSource = observer.pluginProps.get("storageSource","blurb")
            storageDestination = int(observer.pluginProps.get("storageDestination"))
            if storageSource == "compact":
                indigo.variable.updateValue(storageDestination, blurb)
            elif storageSource == "medium":
                indigo.variable.updateValue(storageDestination, notification)
            elif storageSource == "full":
                compromisedCheckpoints = self.getCompromisedCheckpoints(summary.get("alertClassificationUI", ""))
                body = self.getExposureBody(
                summary.get("alertClassificationUI", ""),
                summary.get("alertMax", 0),
                compromisedCheckpoints)
                indigo.variable.updateValue(storageDestination, notification + body)
            
#            indigo.server.speak(notification)

        if observer.pluginProps.get("repeat"):
            self.logResponse(f"Establishing repeat schedule for observer {observer.name}")
            self.scheduleNextResponse(observer.id)


    def sendEmailNotification(self, emailDevice, emailTo, emailCC, notification, body):
        email_plugin = indigo.server.getPlugin("com.indigodomo.email")

        if not email_plugin:
            self.logResponse("Email+ plugin not found.","error")
            return

        self.logResponse(f"eamil attempt to {emailTo} cc {emailCC}  via {emailDevice}")

        try:
            props = {
                "emailTo": emailTo,
                "emailCC": emailCC,
                "emailSubject": notification,
                "emailMessage": body
            }

            email_plugin.executeAction(
                "sendEmail",
                deviceId=int(emailDevice),
                props=props
            )

        except Exception as e:
            self.logResponse(f"Unable to send Email+ notification: {e}","error")


    def checkpointList(self, filter="", valuesDict=None, typeId="", targetId=0):

        options = []

        for dev in indigo.devices.iter(self.pluginId.securifyCheckpoint):
            if dev.deviceTypeId in [ "securifyCheckpoint"]:
                options.append((dev.id, dev.name))

        return options


    def validateDeviceConfigUi(self, valuesDict, typeId, devId):

        if typeId == "securifyObserver":
            return(True, valuesDict)

        errorDict = indigo.Dict()



        for field in [
            "checkpointType"
        ]:

            try:
                value = valuesDict[field]

                if value == "SELECT" :
                    raise ValueError()

            except:
                errorDict[field] = "Specify Checkpoint Device Type."


        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)

        return (True, valuesDict)

    def validatePrefsConfigUi(self, valuesDict):
        errorsDict = indigo.Dict()

        if errorsDict:
            return False, valuesDict, errorsDict

        return True, valuesDict


    # runs when plugin loads. good for initializing variables, loading prefs, etc. but not for doing anything with devices since they might not be loaded yet (that's deviceStartComm)
    def startup(self):
        self.suspendCrossTalk = False
        self.observers = {}
        self.checkpoinmts = {}
        self.lastreport = {}
        self.vulnerabilityCount = 0
        self.breachCount = 0
        self.vulnerabilityMax = 0
        self.alertMax = 0
        self.priorAlertMax = 0
        self.priorAlertClassificationUI = "initial"
        self.priorAlertClassification = 0
        self.alertClassificationUI = ""
        self.configStable = True  
        self.logIt("SECURIFY plugin starting")
        self.loadPluginPrefs()
        self.watchfulness = self.getWatchfulness()
        self.initializeObserverDict()
        self.initializeCheckpointDict()
        self.buildIndicatorCheckpointIndex()
        self.evaluateAllCheckpoints()
        self.updateHouseCheckpoint()


#        self.houseMode = self.pluginPrefs.get("houseMode", "DAY")
        
        indigo.devices.subscribeToChanges()

#        self.buildIndicatorRoomIndex()

    def getWatchfulness(self):
        watchfulness = self.pluginPrefs.get("watchfulness", "HOUSE")
        cause = "user setting"

        if watchfulness == "HOUSE":
            pref = self.houseMode.lower() + "Watchfulness"
            watchfulness = self.pluginPrefs.get(pref,"50")
            cause = "house mode -> " + pref + "setting"

        self.logOther(f"Setting watchulness to {cause} of {watchfulness}")
        return int(watchfulness)
    

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        if userCancelled:
            return

        dev = indigo.devices[devId]

        if typeId == "securifyCheckpoint":
            self.initializeCheckpoint(dev)
            self.reEvaluateCheckpoint(dev)
            self.updateHouseCheckpoint()

        elif typeId == "securifyObserver":
            self.initializeObserver(dev)
            self.reEvaluateAllCheckpoints

        # Get the updated device
#        if typeId == "securifyCheckpoint":
#            self.configStable = False
#            self.configChangedDeviceId = devId


    def closedConfigUi(self, valuesDict, userCancelled, typeId, devId):
        if userCancelled:
            return
        
        self.buildIndicatorCheckpointIndex()

        if typeId in [ "securifyCheckpoint" ]:
            device = indigo.devices[devId]
            self.initializeCheckpoint(device)
###CZEWSKI###


    # invoked by startup(self) at plugin initialization, 
    # and also meant ot be invoked  by closedPrefsConfigUi(self, valuesDict, userCancelled) when the user saves changes to the plugin configuration. good for loading prefs into variables that can be used throughout the plugin.
    def loadPluginPrefs(self):
        self.configStable = True
        self.suspendCrossTalk = False
        self.configChangedDeviceId = None

        self.loggingEnabled = self.pluginPrefs.get("loggingEnabled", True)
        self.logCheckpoints = self.pluginPrefs.get("logCheckpoints", True)
        self.logObservers = self.pluginPrefs.get("logObservers", True)
        self.logResponses = self.pluginPrefs.get("logResponses", True)
        self.logHeartbeats = self.pluginPrefs.get("logHeartbeats", True)
        self.logErrors = self.pluginPrefs.get("logErrors", True)
        self.logIntegrations = self.pluginPrefs.get("logIntegrations", True)
        self.logOthers = self.pluginPrefs.get("logOthers", True)

        self.houseMode = self.pluginPrefs.get(
            "houseMode")

        self.watchfulness = self.pluginPrefs.get(
            "watchfulness")

        self.roomifyPlugin = indigo.server.getPlugin("com.searchcz.roomify")
        self.roomifyCooperationEnabled = self.pluginPrefs.get("roomifyCooperationEnabled", False)
        self.logIntegration(f"Roomify Cooperation = {self.roomifyCooperationEnabled}")
        self.roomifyCooperationInForce = False
        if self.roomifyCooperationEnabled:
            self.roomifyCooperationInForce = self.requestHouseMode(self)

        if self.roomifyCooperationInForce:
            self.logIntegration(f"Roomify cooperation enabled.")
        else:
            self.logIntegration(f"Roomify plugin not available or not enabled. Cannot cooperate on house mode.","warning")
            self.setHouseMode(self.pluginPrefs.get("houseMode"))

    def setRoomifySecurityStates(self, roomId, alertScore, alertClassification, alertClassificationUI):

        if not self.roomifyPlugin or not self.roomifyPlugin.isEnabled():
            return

        try:
            roomify_version = Version(self.roomifyPlugin.pluginVersion)

            if roomify_version < MIN_ROOMIFY_SECURITY_VERSION:
                return

            self.roomifyPlugin.executeAction(
                "updateSecurityStatus",
                props={
                    "deviceId": int(roomId),
                    "alertScore": alertScore,
                    "alertClassification": alertClassification,
                    "alertClassificationUI": alertClassificationUI
                }
            )

        except Exception as e:
            self.logIntegration(
                f"Roomify security update skipped (likely unsupported Roomify version or missing action): {e}","error"
            )        

    def fetchRoomifyHouseMode(self):

        try:
            
            if self.roomifyPlugin.isEnabled():
                # The plugin is installed and running
                self.logIntegration("Successfully linked to com.searchcz.roomify")
            else:
                self.logIntegration("com.searchcz.roomify is installed but not enabled.","warning")
        except Exception as e:
            indigo.logIntegration(f"Failed to find com.searchcz.roomify: {str(e)}", "error")


        if self.roomifyPlugin and self.roomifyPlugin.isEnabled():
            #get the houseMode?
            self.roomifyCooperationInForce = True
            newHouseMode = self.getRoomifyHouseMode()
            self.logIntegration(f"Roomify reporting house mode of {newHouseMode}")
            self.setHouseMode(newHouseMode)
        else:
            self.roomifyCooperationInForce = False
            self.setHouseMode(self.pluginPrefs.get("houseMode"))

    def getRoomifyHouseMode(self):
        for dev in indigo.devices.iter("com.searchcz.roomify.roomifyObserver"):
            newMode = dev.states.get("houseMode")
            self.logIntegration(f"Obaerv:{dev.name} mode:{newMode}")
            return newMode
            break


    def isOn(self, dev):
        return self.deviceIsOn(dev)


    def deviceIsOn(self, device):
        return device.states.get("onOffState", False)



    def closedPrefsConfigUi(self, valuesDict, userCancelled):

        if not userCancelled:
            self.logOther("Plugin preferences updated")            

            self.loadPluginPrefs()

            createObserver = self.pluginPrefs.get("createObserver", False)

            rawId = self.pluginPrefs.get("observerId")

            observerId = int(rawId or 0)

            self.logOther(f"createObserver={createObserver}, observerId={observerId}")

            if createObserver and observerId == 0:

                observerName = self.pluginPrefs.get("observerName", "Securify Observer")
                self.logObserver(f"Creating Observer {observerName}")
                newDevice = indigo.device.create(indigo.kProtocol.Plugin, address=None, name=observerName, deviceTypeId="securifyObserver", props=None, folder=None)
                self.logObserver(f"New Obser4ver Device ID:{newDevice.id}")
                self.pluginPrefs["observerId"] = newDevice.id

            self.watchfulness = self.getWatchfulness()
            self.recomputeAllCheckpoints()

    def debugLoX(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if self.loggingEnabled and self.verboseLogging:
            self.logger.info("@" + formatted + ": " + message)


    def heartbeatLoX(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.heartbeatLogging:
            self.logger.info("@" + formatted + ": " + message)


    def deviceLoX(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.deviceEventLogging:
            self.logger.info("@" + formatted + ": " + message)


    def errorLoX(self, message):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))

        if  self.loggingEnabled and self.errorLogging:
            self.logger.info("@" + formatted + ": " + message)

    def deviceStartComm(self, device):
        device.stateListOrDisplayStateIdChanged()
        self.logCheckpoint(
            f"Starting checkpoint: {device.name}")

        device.stateListOrDisplayStateIdChanged()

        if device.deviceTypeId in [ "securifyCheckpoint" ]:
            self.initializeCheckpoint(device)
        
    def deviceUpdated(self, origDev, newDev):

        if origDev.pluginProps != newDev.pluginProps:

            self.logOther(
                f"[Securify DEBUG] config updated: {newDev.name}")

            if newDev.deviceTypeId in ["securifyCheckpoint"]:
                self.initializeCheckpoint(newDev)

    def dumpDict(self, title, d):

        if not (self.verboseLogging):
            return
        
        indigo.logIt(f"=== {title} ===")

        for key, value in d.items():
            self.logIt(f"{key}: {value}")

        self.logIt("================")

    

    def evaluateAllCheckpoints(self):
        self.logCheckpoint("Evaluating All Checkpoints")
        checkpoints = indigo.devices.iter("self.securifyCheckpoint")
        for checkpoint in checkpoints:
            self.evaluateCheckpoint(checkpoint)        
        self.reEvaluateAllCheckpoints()
        self.updateHouseCheckpoint()


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

    def initializeCheckpoint(self, device):
        self.cacheCheckpoint(device)    
        self.logCheckpoint(f"Initialized checkpoint: {device.name}")  

    def reEvaluateAllCheckpoints(self):
        self.logCheckpoint("RE-Evaluating All Checkpoints")
        self.priorAlertMax = self.alertMax

        self.vulnerabilityCount = 0
        self.breachCount = 0
        self.vulnerabilityMax = 0
        self.alertMax = 0

        checkpoints = indigo.devices.iter("self.securifyCheckpoint")
        for checkpoint in checkpoints:
            self.reEvaluateCheckpoint(checkpoint)

        self.alertClassification = self.getExposureClassification( self.alertMax)
        self.alertClassificationUI = self.getExposureClassificationUI( self.alertMax)
        self.evaluateChange(0,self.priorAlertMax,self.alertMax,self.alertClassificationUI)
        #self.publishToAllObservers()

    def recordAlertScore(self, checkpoint, alertScore):
        priorAlertScore = checkpoint.states.get("alertScore",0)
        if priorAlertScore == alertScore:
            return

        priorClassification = checkpoint.states.get("alertClass",0)
        classification = self.getExposureClassification(priorAlertScore)

        scoreDelta = alertScore - priorAlertScore
        classDelta = classification - priorClassification


        alertClassification = self.getExposureClassification(alertScore)
        alertClassificationUI = self.getExposureClassificationUI(alertScore)

        checkpoint.updateStatesOnServer([
            {"key": "alertScore", "value": alertScore},
            {"key": "priorAlertScore", "value": priorAlertScore},
            {"key": "alertClassification", "value": alertClassification},
            {"key": "alertClassificationUI", "value": alertClassificationUI},
            {"key": "alertScoreDelta", "value": scoreDelta},
            {"key": "alertClassDelta", "value": classDelta},
        ])
        
        #self.evaluateChange(checkpoint.id,priorAlertScore,alertScore,alertClassification)
        #CZEWSKI - self.evaluateChange might be deprecated

    def reEvaluateCheckpoint(self,checkpoint):
        #self.logCheckpoint(f"Re-Evaluating Checkpoint {checkpoint.name}")
        cache = self.checkpoints[checkpoint.id]

        #polling required for for roomify integration
        name = cache.get("name")
        type = cache.get("checkpointType")
        self.logCheckpoint(f"Re-Evaluating Checkpioint {name} of type {type}")
        if type == "OCCUPANCY":
            self.evaluateCheckpoint(checkpoint)

        oldAlertScore = cache.get("alertScore", 0)

        if self.isOn(checkpoint):
            self.vulnerabilityCount += 1
            #vulnerable so compute and save the alertScore using escelationRate
            escelationRate = checkpoint.pluginProps.get("escalationRate")
            if not escelationRate:
                esc = int(0)
            else:
                esc = int(escelationRate)

            
            vulnerabilityScore = checkpoint.states.get("vulnerabilityScore")

            if not vulnerabilityScore:
                vulnerabilityScore = int(0)
            else:
                vulnerabilityScore = int(vulnerabilityScore)

            if esc == 0:
                alertScore = vulnerabilityScore
                self.recordAlertScore(checkpoint,vulnerabilityScore)
            else:
                self.logCheckpoint(f"* Escelation Factor of {esc} per minute")
                now = time.time()
                vulnerabilityEpoch = checkpoint.states.get("vulnerabilityEpoch")
                minutes = ( int(now) - int(vulnerabilityEpoch) ) / 60
                minutes = int(minutes)
                self.logCheckpoint(f"* times a duration of {minutes} minutes")
                escalation =  int(esc) * int(minutes) 
                self.logCheckpoint(f"= escalation of {escalation}")
                alertScore = int(vulnerabilityScore) + int(escalation)
                alertScore = max(0, min(alertScore, 100))
                self.recordAlertScore(checkpoint,vulnerabilityScore)
 
            if alertScore > 0:
#                indigo.device.turnOn(checkpoint.id)
                checkpoint.updateStateOnServer("brightnessLevel", alertScore)
#               indigo.dimmer.setBrightness(checkpoint.id, alertScore)
            else:
                indigo.device.turnOff(checkpoint.id)

            alertClassification = self.getExposureClassification(alertScore)
            alertClassificationUI = self.getExposureClassificationUI(alertScore)

            checkpoint.updateStateOnServer("alertClassification",alertClassification)
            checkpoint.updateStateOnServer("alertClassificationUI",alertClassificationUI)

            self.logCheckpoint(f"--> Vulnerabnility:{vulnerabilityScore} / Alert:{alertScore}")

            if alertScore > 0:
                self.breachCount += 1
                if alertScore > self.alertMax:
                    self.alertMax = alertScore

            if vulnerabilityScore > self.vulnerabilityMax:
                self.vulnerabilityMax = vulnerabilityScore

            self.cacheCheckpoint(checkpoint)

            if self.roomifyCooperationInForce:
                roomId = checkpoint.pluginProps.get("roomifyRoomId")
                self.logIntegration(f"Roomify Cooperation is in force, checkpoint {checkpoint.name} has roomId {roomId}")
                if roomId and roomId != "none":
                    self.logIntegration("Setting Roomify Security States")
                    self.setRoomifySecurityStates(
                        roomId, 
                        alertScore, 
                        self.getExposureClassification(alertScore),
                        self.getExposureClassificationUI(alertScore))

           
            

    def evaluateCheckpointDeprecated(self,checkpoint):

        checkpointType = checkpoint.pluginProps.get("checkpointType")
        importance = checkpoint.pluginProps.get("importance")

        #I suspect old_score wont be needed anymore
        old_score = int(checkpoint.states.get("vulnerabilityScore",0))

        vulnerable = False

        self.logCheckpoint(f"Evaluating Checkpoint {checkpoint.name}")

        #Step 1 - Is It Vulnerable (exposed)
        if checkpointType == "OCCUPANCY":
            roomId = checkpoint.pluginProps.get("roomifyOccupancyId")
            room = indigo.devices[roomId]
            if room.states.get("occupied"):
                vulnerable = True
        elif checkpointType in ["MOTION","FAULT"]:
            sensorId = checkpoint.pluginProps.get("motionSensor")
            if self.isVulnerable(sensorId):
                vulnerable= True
        elif checkpointType == "DOOR":
            sensorId = checkpoint.pluginProps.get("doorSensor")
            if self.isVulnerable(sensorId):
                vulnerable = True
            sensorId = checkpoint.pluginProps.get("doorLock")
            if self.isVulnerable(sensorId):
                vulnerable = True

        #Step 2 - measure the vulnerability
        if vulnerable:
            new_score = (int(importance) + int(self.watchfulness)) - 99
        else:
            new_score = 0

        self.logCheckpoint(f"Wachfulness [{self.watchfulness}] + Importance [{importance}] = Vulnerbility [{new_score}]")

        #Step 2 - update checkpoint states
        checkpoint.updateStateOnServer("vulnerabilityScore",new_score)
        alertScore = max(0, min(new_score, 100))
        checkpoint.updateStateOnServer("alertScore",alertScore)

        if alertScore > 0:
#            indigo.device.turnOn(checkpoint.id)
            checkpoint.updateStateOnServer("brightnessLevel", alertScore)
#           checkpoint.setBrightness(checkpoint.id, alertScore)
        else:
            indigo.device.turnOff(checkpoint.id)


        if vulnerable:
            epoch = checkpoint.states.get("vulnerabilityEpoch",0)
#            if ( new_score != old_score ) or (epoch == 0):
            if (epoch == 0):
                #new epoch needed for temporal breachiness factoring ?
                now = time.time()
                humanTime = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
                checkpoint.updateStateOnServer("vulnerabilityEpoch",now)
                checkpoint.updateStateOnServer("vulnerabilityDatetime",humanTime)
        else:
            checkpoint.updateStateOnServer("vulnerabilityEpoch","")
            checkpoint.updateStateOnServer("vulnerabilityDatetime","")


        self.cacheCheckpoint(checkpoint)

        if self.roomifyCooperationInForce:
            roomId = checkpoint.pluginProps.get("roomifyRoomId")
            self.logIntegratio(f"Roomify Cooperation is in force, checkpoint {checkpoint.name} has roomId {roomId}")
            if roomId and roomId != "none":
                self.logIntegration("Setting Roomify Security States")
                self.setRoomifySecurityStates(
                    roomId, 
                    alertScore, 
                    self.getExposureClassification(alertScore),
                    self.getExposureClassificationUI(alertScore))


        self.logCheckpoint(f"Setting checkpoint {checkpoint.name} onOffState to {vulnerable}")
#        checkpoint.updateStateOnServer("onOffState",vulnerable)
        #if vulneranble:
        #    indigo.device.turnOn(checkpoint.id)
        #else:
        #    indigo.device.turnOff(checkpoint.id)


    def isVulnerable(self,sensorId):
        if sensorId:
            if sensorId == "none":
                return False
            sensor = indigo.devices[int(sensorId)]
            sensorState = self.isOn(sensor)
            self.logCheckpoint(f"--> {sensor.name}:{sensorId} reports {sensorState}")
            return sensorState
        else:
            return False
                
    def actionControlDevice(self, action, dev):
        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            self.logOther(f"{dev.name}: turn on requested")
            dev.updateStateOnServer("onOffState", True)

        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            self.logOther(f"{dev.name}: turn off requested")
            dev.updateStateOnServer("onOffState", False)

        elif action.deviceAction == indigo.kDeviceAction.Toggle:
            new_value = not dev.onState
            self.logOther(f"{dev.name}: toggle requested -> {new_value}")
            dev.updateStateOnServer("onOffState", new_value)

        elif action.deviceAction == indigo.kDeviceAction.RequestStatus:
            self.logOther(f"{dev.name}: status requested")

        elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
            new_level = action.actionValue  # 0-100

            self.logOther(f"{dev.name}: brightness controls are not available for this device")

            checkpoint = self.ckeckpoints[dev.id]
            newLevel = checkpoint.get("alertScore", 0)

            dev.updateStatesOnServer([
                {"key": "brightnessLevel", "value": new_level},
                {"key": "onOffState", "value": new_level > 0},
            ])

        else:
            self.logOther(f"{dev.name}: unsupported action {action.deviceAction}","error")

    def buildIndicatorCheckpointIndex(self):
        self.indicatorCheckpointIndex = {}
        for checkpoint in indigo.devices.iter("self.securifyCheckpoint"):
            checkpointType = checkpoint.pluginProps.get("checkpointType")

            if checkpointType == "OCCUPANCY":
                roomId = checkpoint.pluginProps.get("roomifyOccupancyId")
                self.logOther(f"Room ID {roomId} mapped as an indicator for checkpoint {checkpoint.name}")
                self.addIndicator(checkpoint, roomId)

            elif checkpointType in [ "MOTION", "FAULT"]:
                sensorId = checkpoint.pluginProps.get("motionSensor")
                self.logOther(f"Sensor ID {sensorId} mapped as an indicator for checkpoint {checkpoint.name}")
                self.addIndicator(checkpoint, sensorId)

            elif checkpointType == "DOOR":
                sensorId = checkpoint.pluginProps.get("doorSensor")
                self.logOther(f"Door {sensorId} mapped as an indicator for checkpoint {checkpoint.name}")
                self.addIndicator(checkpoint, sensorId)
                sensorId = checkpoint.pluginProps.get("doorLock")
                self.logOther(f"Lock ID {sensorId} mapped as an indicator for checkpoint {checkpoint.name}")
                self.addIndicator(checkpoint, sensorId)


    def addIndicator(self,checkpoint,sensorId):

        if (sensorId != "none") and sensorId:
            try:
                sensorId = int(sensorId)
                if sensorId not in self.indicatorCheckpointIndex:
                    self.logOther(f"Mapping vunerability indicator {sensorId} to room {checkpoint.name}")
                    self.indicatorCheckpointIndex[sensorId] = []
                self.indicatorCheckpointIndex[sensorId].append(checkpoint.id)

                self.indicatorCheckpointIndex[sensorId].append(checkpoint.id)

            except:
                self.logOther(f"tripped over checkpoint {checkpoint.name}","error")


    def clearNextObligation(self, checkpoint):
        checkpoint.updateStatesOnServer([
            {"key": "nextEvaluationTime", "value": None},
            {"key": "nextEvaluationTimeUI", "value": None},
            {"key": "nextEvaluationInitiator", "value": None},
            {"key": "nextEvaluationClass", "value": None},
        ])

    def recordDeviceReport(self, dev, onState):
        state = self.lastreport.get(dev.id, {})

        if onState is not None:
            state["onState"] = onState

        state["lastUpdate"] = time.time()
        state["source"] = "Securify"

        self.lastreport[dev.id] = state



    #heartbeat
    def runConcurrentThread(self):

        self.logHeartbeat("Securify heartbeat thread started")

        try:
            while True:

                #now = time.time()

                if not self.configStable:
                    self.configStable = True
                    if self.configChangedDeviceId:
                        checkpoint = indigo.devices[self.configChangedDeviceId]
                        self.evaluateCheckpoint(checkpoint)
                        self.updateHouseCheckpoint()
                    else:
                        self.loadPluginPrefs()

                self.logHeartbeat("Securify Heartbeat")

                self.logHeartbeat("*** ESCALATING VULNERABLE CHECKPOINTS ***")
                self.escalateVulnerableCheckpoints()
                self.logHeartbeat("*** RE-EVALUATING ALL CHECKPOINTS ***")
                self.reEvaluateAllCheckpoints()
                self.logHeartbeat("*** UPDATING HOUSE CHECKPOINT ***")
                self.updateHouseCheckpoint()   
                self.logHeartbeat("*** PROCESSING OBSEVERS FOR HOUSE ***")
                self.processObserversForCheckpoint(0,self.alertMax, self.vulnerabilityMax)
                #is this necessary?
                self.logHeartbeat("*** REPROCESSING ACTIVE OBSERVERS ***")
                self.reprocessActiveObservers()

                self.sleep(60)                 

        except self.StopThread:
            self.logger.info("Securify heartbeat thread stopped")

#------------------------------------------DEBUGGING CODE SNIPPETS BELOW -----------------------------#
    def escalateVulnerableCheckpoints(self):
        for checkpointId, checkpoint in self.checkpoints.items():

            if checkpointId == 0:
                continue

            name = checkpoint.get("name")            
            vulnerabilityScore = checkpoint.get("vulnerabilityScore")
            self.logHeartbeat(f"Considering escalation of checkpoint {name} with vulnerability {vulnerabilityScore}")
            if (vulnerabilityScore == 0) or (vulnerabilityScore == "0"):
                self.logCheckpoint("--> Not vulnerable = not escalated")
                continue

            escalationRate = checkpoint.get("escalationRate")
            if (escalationRate == 0) or (escalationRate == "0"):
                self.logHeartbeat(f"--> Escalation rate 0 not escalated")
                continue

            
            
            #vulnerable checkpoint subject to escalation
            #so reEvaluate it
            dev = indigo.devices[checkpointId]
            self.reEvaluateCheckpoint(dev)
            self.processObserversForCheckpoint(0,self.alertMax, self.vulnerabilityMax)



    def dumpCheckpointCache(self):
        self.logIt("---- Securify Checkpoints Cache ----")

        for checkpointId, checkpoint in self.checkpoints.items():
            self.dumpCheckpoint(checkpoint)

    def dumpCheckpoint(self,checkpoint):
        self.llogCheckpoints = True
        self.logCheckpoint(
            f"name={checkpoint.get('name')} "
            f"vulnerability={checkpoint.get('vulnerabilityScore')} "
            f"escalation={checkpoint.get('escalationRate')} "
            f"score={checkpoint.get('alertScore')} "
            f"scoreDelta={checkpoint.get('alertScoreDelta')} "
            f"class={checkpoint.get('alertClassification')} "
            f"classDelta={checkpoint.get('alertClassDelta')} "
            f"classUI={checkpoint.get('alertClassificationUI')} "
        )
            
    def dumpObserverCache(self):
        self.logObservers = True
        self.logObserver("---- Securify Observers Cache ----")

        for observerId, observer in self.observers.items():
            self.dumpObserver(observer)

    def dumpObserver(self,observer):
        self.logObserver(
            f"name={observer.get('name')} "
            f"enabled={observer.get('enabled')} "
            f"target={observer.get('target')} "
            f"activator={observer.get('activator')} "
            f"active={observer.get('active')} "
            f"repeatCount={observer.get('repeatCount')} "
            f"repeatMax={observer.get('repeatMax')} "
            f"repeatScheduledEpoch={observer.get('repeatScheduledEpoch')} "        
            f"responseGated={observer.get('responseGated')} "
            f"responsePersistenceThreshold={observer.get('responsePersistenceThreshold')} "
            f"responseGateDevice={observer.get('responseGatedDevice')} "
            f"responseAuthorized={observer.get('responseAuthorized')} "
            f"activationEpoch={observer.get('activationEpoch')} "
        )

#-----------------------------------------------------------------------------------------------------#
# Code below this line is undergoing optimization as of Fune 28, 2026

    def authChangeReported(self, origDev, newDev):
        auth_change_reported = False
        if hasattr(newDev,"responseAuthorized"):
            old_auth = origDev.states.get("responseAuthorized")
            new_auth = newDev.states.get("responseAuthorized")
            auth_change_reported = ( old_auth != new_auth )
            self.logHeartbeat(f"Authorization was {old_auth} and is now {new_auth} so change detection says {auth_change_reported}")
        return auth_change_reported

    def repeatChangeReported(self, origDev, newDev):
        repeatChange = False
        if hasattr(newDev,"repeatCount"):
            old = origDev.states.get("repeatCount")
            new = newDev.states.get("repeatCount")
            repeatChange = ( old != new )
        return repeatChange


    def deviceUpdated(self, origDev, newDev):


        isIndicator = newDev.id in self.indicatorCheckpointIndex

        # FIRST FILTER - is this device relevant to Securify
        if not ((isIndicator) or (newDev.deviceTypeId in [ "securifyObserver","securifyCheckpoint"])):
            return


        # SECOND FILTER - is this state report any different from the previous state report
        previous = self.lastreport.get(newDev.id, {})

        new_on_report = getattr(newDev, "onState", None)
        old_on_report = previous.get("onState")
        on_change_reported = (new_on_report != old_on_report)

        new_brightness_report = getattr(newDev, "brightness", None)
        old_brightness_report = getattr(origDev, "brightness", None)

        auth_change_reported = self.authChangeReported(origDev, newDev)
        repeat_reported = self.repeatChangeReported(origDev, newDev)

        brightness_change_reported = (new_brightness_report != old_brightness_report)
        state_change_reported = on_change_reported or brightness_change_reported or auth_change_reported or repeat_reported


        #CZEWSKI - LATEST UPDATED - RESPOND TO BRIGHTNESS CHANGES AT CHECKPOINT

        if not state_change_reported:
            return  # 🚫 no relevant changes
        
        self.logOther(f"...Processing report from {newDev.name}:{newDev.id} of ON={new_on_report}")
        self.recordDeviceReport(newDev, newDev.onState)
        
        if newDev.deviceTypeId == "securifyCheckpoint":
            self.processCheckpointUpdate(origDev, newDev)

        if newDev.deviceTypeId == "securifyObserver":
            self.processObserverUpdate(origDev, newDev)

        elif isIndicator:
            self.processCheckpointSensorUpdate(origDev,newDev)
        

    def processCheckpointUpdate(self, origDev, newDev):
        #checkpoint DEVICE changed (due to sensor reports perhaps)

        self.logCheckpoint(f"...processing checkpoint update for {newDev.name}")

        oldScore = getattr(origDev, "brightness", None)
        newScore = getattr(newDev, "brightness", None)
        checkpointId = newDev.id


        self.recordAlertScore(newDev, newScore )


        newV = int(newDev.states.get("vulnerabilityScore", 0) or 0)

#        vulnerabilityScore = int(newDev.states.get("vulnerabilityScore", 0) or 0)
#        escalationRate = newDev.pluginProps.get("escalationRate")


        self.initializeCheckpoint(newDev)

        #AT THIS POINT ANY OBSERVER FOCUSED ON THIS CHECKPOINT WILL BE SUBJECT TO UPDATE
        self.processObserversForCheckpoint(checkpointId,newScore,newV)

        #SUMMARIZE INDIVIDUAL CHECKPOINT INTO CHECKPOINT 0 
        self.updateHouseCheckpoint()       

        #FINALLY OBSERVER FOCUSED ON CUMULATIVE 0 CHECKPOINT WILL BE SUBJECT TO UPDATE
        self.processObserversForCheckpoint(0,self.alertMax, self.vulnerabilityMax)

        #self.evaluateExposureChange(self.checkpoints[checkpointId])


    def updateHouseCheckpoint(self):

        highestScore = 0
        highestClass = 0
        highestClassUI = "allclear"

        highestCheckpointId = 0
        highestCheckpointName = ""

        #summarize
        for checkpointId, checkpoint in self.checkpoints.items():

            if checkpointId == 0:
                continue

            alertScore = int(checkpoint.get("alertScore", 0) or 0)
            alertClassification = int(checkpoint.get("alertClassification", 0) or 0)
            vulnerabilityScore = int(checkpoint.get("vulnerabilityScore", 0) or 0)



            if alertScore > highestScore:
                highestScore = alertScore
                highestClass = alertClassification
                highestClassUI = checkpoint.get("alertClassificationUI", "allclear")
                highestCheckpointId = checkpointId
                highestCheckpointName = checkpoint.get("name", "")  

        #store
        house = self.checkpoints[0]

        previousScore = int(house.get("alertScore", 0) or 0)
        previousClass = int(house.get("alertClassification", 0) or 0)

        house["alertScoreDelta"] = highestScore - previousScore
        house["alertClassDelta"] = highestClass - previousClass

        house["alertScore"] = highestScore
        house["alertClassification"] = highestClass
        house["alertClassificationUI"] = highestClassUI

        house["highestCheckpointId"] = highestCheckpointId
        house["highestCheckpointName"] = highestCheckpointName              
        

    def processObserversForCheckpoint(self, checkpointId,newScore, newV): 


        checkpoint = self.checkpoints.get(checkpointId)
        self.logObserver(f"...locating observers for checkpoint {checkpoint.get('name')}")


        if not checkpoint:
            return

        for observerId, observer in self.observers.items():

            #self.logObserver(f"...considering observer {observer.get('name')}")

            if not observer.get("enabled", False):
#                self.logObserver("XXX - Observer Not Enabled")
                continue

            if not self.observerCaresAboutCheckpoint(observer, checkpointId):
#                self.logObserver("XXX - Observer Doesn't Care")
                continue

            conditionMet = self.evaluateObserverAgainstCheckpoint(observer, checkpoint)

            if conditionMet:
                self.logObserver(f"Checkpoint {checkpoint.get('name')} updating observer {observer.get("name")}")

                observer["alertScore"] = newScore
                observerDev = indigo.devices[observerId]
                observerDev.updateStateOnServer("breachMax",newScore)
                observerDev.updateStateOnServer("vulnerabilityMax",newScore)


                if not self.isOn(indigo.devices[observerId]):
                    indigo.device.turnOn(observerId)
            else:
                self.logObserver("Observer Conditions Not Met")
                indigo.device.turnOff(observerId)

    def observerCaresAboutCheckpoint(self, observer, checkpointId):
        target = observer.get("target", "0")

#        if target == "*":
#            return True

        try:
            return int(target) == int(checkpointId)
        except Exception:
            return False

    def evaluateObserverAgainstCheckpoint(self, observer, checkpoint):
        activator = observer.get("activator", "")

        self.logObserver(f"... evaluating observer {observer.get("name")} against checkpoint {checkpoint.get("name")} for focus {activator}")
        alertClassificationUI = checkpoint.get("alertClassificationUI", "")
        alertScoreDelta = int(checkpoint.get("alertScoreDelta", 0) or 0)
        alertClassDelta = int(checkpoint.get("alertClassDelta", 0) or 0)

        # Classification state activators
        if activator in ["allclear", "normal", "noteworthy", "significant", "serious", "critical"]:
            return alertClassificationUI == activator

        # Classification change activators
        if activator == "classificationchanges":
            return alertClassDelta != 0

        if activator == "classchange":
            return alertClassDelta != 0

        if activator == "classincrease":
            return alertClassDelta > 0

        if activator == "classdecrease":
            return alertClassDelta < 0

        # Score change activators
        if activator == "scorechanges":
            return alertScoreDelta != 0

        if activator == "scorechange":
            return alertScoreDelta != 0

        if activator == "scoreincrease":
            return alertScoreDelta > 0

        if activator == "scoredecrease":
            return alertScoreDelta < 0

        return False


    def newObserverActivation(self,obsereverId):
        observer = self.observers[obsereverId]
        observer["repeatCount"] = 0

    def processObserverUpdate(self, origDev, newDev):

        isOn = self.isOn(newDev)
        #Observer newly activated ?
        if self.isOn(newDev):
            self.logObserver("---> Observer reports ON")
            if not self.isOn(origDev):
                #device NEWLY on - but - might be gated
                self.logObserver(f"---> Observer {newDev.name} Activated")
                activationEpoch = int(time.time())
                newDev.updateStateOnServer("activationEpoch", activationEpoch)
                self.observers[newDev.id]["activationEpoch"] = activationEpoch
                responseAuthorized = self.getResponseAuthorization(newDev)
                if responseAuthorized:
                    self.newObserverActivation(newDev.id)
                    self.respond(newDev,f"---> Observer {newDev.name} is activated and authorized to respond")
                else:
                    self.logObserver("---> (response is not authorized)")
                newDev.updateStateOnServer("responseAuthorized", responseAuthorized)
                self.observers[newDev  .id]["responseAuthorized"] = responseAuthorized
            else:
                #OLD on, might be NEWLY authorized
                if ( newDev.states.get("responseAuthorized")) and not ( origDev.states.get("responseAuthorized")):
                    self.newObserverActivation()
                    self.respond(newDev,f"---> Active Observer {newDev.name} is now authorized to respond")
                #OLD on, might be REMINDER
                elif self.repeatChangeReported(origDev,newDev):
                    repeatCount = newDev.states.get("repeatCount")
                    repeatMax = newDev.states.get("repeatMax")
                    self.observerResponse(newDev,repeatCount,repeatMax)

        else:
            #observer is off?
            activationEpoch = 0
            self.observers[newDev.id]["activationEpoch"] = activationEpoch
            newDev.updateStateOnServer("activationEpoch", activationEpoch)
            newDev.updateStateOnServer("responseAuthorized", False)

        self.initializeObserver(newDev)

        
    def respond(self,observer,cause):
            cache = self.observers[observer.id]
            self.logResponse("RESPONSE INITIATTED: " + cause)
            repeatCount = cache.get("repeatCount")
            repeatMax = cache.get("repeatMax")
            self.observerResponses(observer,repeatCount,repeatMax)


    def processCheckpointSensorUpdate(self, origDev, newDev):
        
        try:
            checkpointIDs = self.indicatorCheckpointIndex.get(newDev.id, [])

            checkedID = 0

            for checkpointID in checkpointIDs:
                if checkpointID != checkedID:
                    checkpoint = indigo.devices[checkpointID]

                    # a checkpoint sensor has something to say
                    self.logCheckpoint(f"Checkpoint {checkpoint.name} requires evaluation")
                    self.evaluateCheckpoint(checkpoint)
                    checkedID = checkpointID

            self.updateHouseCheckpoint()

        except Exception as e:
            self.logCheckpoint(f"[SECURIFY ERROR] deviceUpdated: {e}","error")        

    def evaluateCheckpoint(self, checkpoint):

        checkpointType = checkpoint.pluginProps.get("checkpointType")
        epoch = checkpoint.states.get("vulnerabilityEpoch")
        importance = checkpoint.pluginProps.get("importance")

        if ( epoch == 0 ) or ( not epoch ):
            epoch = time.time()

        vulnerable = False

        self.logCheckpoint(f"... evaluating checkpoint {checkpoint.name} of type {checkpointType}")

        # Step 1 - Is It Vulnerable / Exposed?
        if checkpointType == "OCCUPANCY":
            roomId = checkpoint.pluginProps.get("roomifyOccupancyId")
            self.logIntegration(f"Checking occupancy of room id {roomId}")

            if not roomId:
                room = None
            else:
                try:
                    roomId = int(roomId)
                    room = indigo.devices[roomId]
                    self.logIntegration(f"Room Name {room.name}")
                    if room.states.get("occupied"):
                        self.logIntegration(f"Occupied = Vulnerable")
                        vulnerable = True
                except Exception:
                    self.logCheckpoint(
                        f"Checkpoint '{checkpoint.name}' references missing Roomify occupancy device id '{roomId}'",
                        "warning"
                    )
                    room = None

        
        if checkpointType in ["MOTION", "FAULT"]:
            sensorId = checkpoint.pluginProps.get("motionSensor")
            if self.isVulnerable(sensorId):
                vulnerable = True

        if checkpointType == "DOOR":
            sensorId = checkpoint.pluginProps.get("doorSensor")
            if self.isVulnerable(sensorId):
                vulnerable = True

            sensorId = checkpoint.pluginProps.get("doorLock")
            if self.isVulnerable(sensorId):
                vulnerable = True

        # Step 2 - Measure the vulnerability
        if vulnerable:
            new_score = (int(importance) + int(self.watchfulness)) - 99
        else:
            new_score = 0

        alertScore = max(0, min(new_score, 100))
        now = ""
        humanTime = ""

        if vulnerable:
            now = epoch
            humanTime = datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

        self.logCheckpoint(
            f"... watchfulness [{self.watchfulness}] + Importance [{importance}] = Vulnerability [{new_score}]"
        )

        #CZEWSKI - GET THE ALERT CLASS UI CORRESPONDING TO ALERT SCORE PLEASE
        alertClassificationUI = self.getExposureClassificationUI(alertScore)
        alertClassification = self.getExposureClassification(alertScore)



        # Step 3 - Update checkpoint states in one execution
        # cache escelation values
        checkpoint.updateStatesOnServer([
            {"key": "vulnerabilityScore", "value": new_score},
            {"key": "alertScore", "value": alertScore},
            {"key": "alertClassification", "value": alertClassification},
            {"key": "alertClassificationUI", "value": alertClassificationUI},
            {"key": "brightnessLevel", "value": alertScore},
            {"key": "onOffState", "value": alertScore > 0},
            {"key": "vulnerabilityEpoch", "value": now},
            {"key": "vulnerabilityDatetime", "value": humanTime},


        ])

        self.cacheCheckpoint(checkpoint)

        self.logIntegration("Roomify cooperation is in force")
        if self.roomifyCooperationInForce:
            roomId = checkpoint.pluginProps.get("roomifyRoomId")
            self.logIntegration(f"Roomify Cooperation is in force, checkpoint {checkpoint.name} has roomId {roomId}")
            if roomId and roomId != "none":
                self.logIntegration("Setting Roomify Security States")
                self.setRoomifySecurityStates(
                    roomId, 
                    alertScore, 
                    self.getExposureClassification(alertScore),
                    self.getExposureClassificationUI(alertScore))


    def initializeCheckpointDict(self):
        self.checkpoints = {}

        self.checkpoints[0] = {
            "id": 0,
            "name": "House",
            "alertScore": 0,
            "alertScoreDelta": 0,
            "alertClassification": 0,
            "alertClassDelta": 0,
            "alertClassificationUI": "unknown",
            "activeCheckpointCount": 0,
            "highestCheckpointId": 0,
            "highestCheckpointName": "", 
            "escalationRate": 0,
            "vulnerabilityScore": 0}

        for checkpoint in indigo.devices.iter("self.securifyCheckpoint"):
            #cache everything needed to determine checkpoint exposure
            #without referring to the device itself
            self.cacheCheckpoint(checkpoint)

    def cacheCheckpoint(self,checkpoint):

        # vulnerability score is hiding in brightness my man !
        brightness = checkpoint.states.get("brightnessLevel")

        self.checkpoints[checkpoint.id] = {
            "id": checkpoint.id,
            "name": checkpoint.name,

            # for roomify linked checkpioints...
            "checkpointType" : checkpoint.pluginProps.get("checkpointType"),
            "roomifyOccupancyId" : checkpoint.pluginProps.get("roomifyOccupancyId"),

            # Evaluation outcomes
            "alertScore": brightness,
            "priorAlertScore": checkpoint.states.get("priorAlertScore"),
            "alertScoreDelta": checkpoint.states.get("alertScoreDelta"),

            "alertClassification": checkpoint.states.get("alertClassification"),
            "alertClassificationUI": checkpoint.states.get("alertClassificationUI"),
            "alertClassDelta": checkpoint.states.get("alertClassDelta"),

            # Escalation inputs
            "importance": checkpoint.pluginProps.get("importance"),
            "escalationRate": checkpoint.pluginProps.get("escalationRate"),
            "vulnerabilityScore": checkpoint.states.get("vulnerabilityScore"),
            "vulnerabilityEpoch": checkpoint.states.get("vulnerabilityEpoch"),
        }

    def getResponseAuthorization(self, observer):
        # No gating configured? Always authorized.
        if not self.toBool(observer.pluginProps.get("responseGated", False)):
            return True

        # Has the persistence threshold been met?
        threshold = int(observer.pluginProps.get("responsePersistenceThreshold", 0) or 0)
        activationEpoch = float(observer.states.get("activationEpoch", 0) or 0)

        if time.time() < (activationEpoch + (threshold * 60)):
            return False

        # Is the optional gate open?
        gateId = observer.pluginProps.get("responseGateDevice", "none")

        if not gateId or gateId == "none":
            return True

        return self.isOn(indigo.devices[int(gateId)])

    def initializeObserverDict(self):
        for observer in indigo.devices.iter("self.securifyObserver"):
            self.initializeObserver(observer)


    def initializeObserver(self, observer):
        existing = self.observers.get(observer.id, {})

        responseAuthorized = self.getResponseAuthorization(observer)

        self.observers[observer.id] = {
            "id": observer.id,
            "name": observer.name,

            "enabled": self.toBool(observer.pluginProps.get("enabled", False)),
            "target": observer.pluginProps.get("focusTarget", "0"),
            "activator": observer.pluginProps.get("focusActivator", "anychange"),

            "active": self.toBool(observer.states.get("onOffState", False)),
            "alertScore": int(observer.states.get("breachMax", 0)),

            # preserve runtime reminder/repeat tracking
            "repeatCount": int(existing.get("repeatCount", 0) or 0),
            "repeatScheduledEpoch": float(existing.get("repeatScheduledEpoch", 0) or 0),

            "repeat": self.toBool(observer.pluginProps.get("repeat", 0) or 0),
            "repeatMax": int(observer.pluginProps.get("repeatMax", 0) or 0),
            "repeatDelay1": int(observer.pluginProps.get("repeatDelay1", 0) or 0),
            "repeatDelayN": int(observer.pluginProps.get("repeatDelayN", 0) or 0),

            "responseGated": self.toBool(observer.pluginProps.get("responseGated", False) or False),
            "responsePersistenceThreshold": int(observer.pluginProps.get("responsePersistenceThreshold", 0) or 0),
            "responseGateDevice": observer.pluginProps.get("responseGateDevice", "none"),
            "responseAuthorized": self.toBool(observer.states.get("responseAuthorized", True)),

            # this name looks suspicious, but preserving your current intent
            "activationEpoch": responseAuthorized,
        }


    def getDirection(self, oldValue, newValue):
        if newValue > oldValue:
            return "increase"
        elif newValue < oldValue:
            return "decrease"
        else:
            return "unchanged"
        
    def observerResponsesDeprecated(self, observer):
        notification =  self.getExposureMessage(observer.name, self.alertClassificationUI, self.alertMax, 0, 1)

        if observer.pluginProps.get("log"):
            self.logIt(notification)

        if observer.pluginProps.get("announce"):
            indigo.server.speak(notification)



        if observer.pluginProps.get("email"):
            compromisedCheckpoints = self.getCompromisedCheckpoints(self.alertClassificationUI)
            body = self.getExposureBody(
                self.alertClassificationUI,
                self.alertMax,
                compromisedCheckpoints)
            emailTo = observer.pluginProps.get("emailTo")
            emailCC = observer.pluginProps.get("emailCC")
            emailBCC = observer.pluginProps.get("emailBCC")
            emailDevice = observer.pluginProps.get("emailDevice")
            #SEND THAT EMAIL
            # Target the built-in Email+ plugin ID

            self.sendEmailNotification(emailDevice, emailTo, emailCC, notification, body)

        if observer.pluginProps.get("storage"):
            storageDestination = int(observer.pluginProps.get("storageDestination"))
            indigo.variable.updateValue(storageDestination, notification)
#            indigo.server.speak(notification)


    def sendEmailNotification(self, emailDevice, emailTo, emailCC, notification, body):
        email_plugin = indigo.server.getPlugin("com.indigodomo.email")

        if not email_plugin:
            self.logResponse("... Email+ plugin not found.")
            return

        self.logResponse(f"... eamil attempt to {emailTo} cc {emailCC}  via {emailDevice}")

        try:
            props = {
                "emailTo": emailTo,
                "emailCC": emailCC,
                "emailSubject": notification,
                "emailMessage": body
            }

            email_plugin.executeAction(
                "sendEmail",
                deviceId=int(emailDevice),
                props=props
            )

        except Exception as e:
            self.logResponse(f"... unable to send Email+ notification: {e}","error")


    def recomputeAllCheckpoints(self):
        for checkpointId, checkpoint in self.checkpoints.items():
            if checkpointId != 0:
                dev = indigo.devices[checkpointId]
                self.evaluateCheckpoint(dev)
        self.updateHouseCheckpoint()

    def setHouseMode(self, newMode):

        self.logOther(f"Securify HouseMode change requested: {newMode} suspendCrossTalk={self.suspendCrossTalk} roomifyCooperationEnabled={self.roomifyCooperationEnabled} roomifyCooperationInForce={self.roomifyCooperationInForce}")
        oldMode = self.houseMode

        if oldMode == newMode:
            self.logOther(f"HouseMode already {newMode}, ignoring")
            return

        self.logOther(f"HouseMode change: {oldMode} → {newMode} suspended crosstalk={self.suspendCrossTalk} roomifyCooperationEnabled={self.roomifyCooperationEnabled} roomifyCooperationInForce={self.roomifyCooperationInForce}")
        self.pluginPrefs["houseMode"] = newMode
        self.houseMode = newMode

        if ( not self.suspendCrossTalk ) and self.roomifyCooperationEnabled:
            self.suggestHouseMode(newMode)

        self.suspendCrossTalk = False
        self.watchfulness = self.getWatchfulness()
        self.logOther(f"Watchfulness set to {self.watchfulness}")

        self.recomputeAllCheckpoints()

    def scheduleNextResponse(self,observerId):
        observer = self.observers[observerId]
        name = observer.get("name")
        repeat = observer.get("repeat")
        repeatCount = observer.get("repeatCount")
        repeatMax = observer.get("repeatMax")
        repeatDelay1 = observer.get("repeatDelay1")
        repeatDelayN = observer.get("repeatDelayN")

        now = time.time()

        self.logHeartbeat(f"Observer:{name} just completed response#  {repeatCount} of {repeatMax}")

        if ( not repeat ) or ( repeatCount == repeatMax ):
            self.logHeartbeat(f"Repeat limit hit for {name}")
            observer["repeatScheduledEopch"] = 0

        if ( repeatCount >= repeatMax ) or (not repeat) :
            self.logHeartbeat(f"Repeat limit hit for {name}")
#            observer["repeatScheduledEpoch"] = newEpoch
            observer["repeatScheduledEpoch"] = 0
            return
        
        repeatCount += 1


        if repeatCount == 1:
            #scheduling 1st repeat
            newEpoch = now + ( 60 * repeatDelay1 )
        else:
            #schedule nth repeat
            newEpoch = now + ( 60 * repeatDelayN )

        humanTime = datetime.datetime.fromtimestamp(newEpoch).strftime("%H:%M:%S")


        self.logHeartbeat(f"Scheduling repeat #{repeatCount} at {humanTime} for {name}")
        observer["repeatScheduledEpoch"] = newEpoch
        observer["repeatCount"] = repeatCount

    def considerReminders(self, observerId, observer):
        now = time.time()

        self.logHeartbeat(f"Considering reminders for {observer.get("name")}")
        if not observer.get("enabled"):
            self.logHeartbeat("--> observer not enabled")
            return
        
        repeatScheduledEpoch = observer.get("repeatScheduledEpoch")
        if ( repeatScheduledEpoch == 0) or ( not repeatScheduledEpoch ):
            self.logHeartbeat("--> observer not scheduled for reminders")
            return
                        
        x = repeatScheduledEpoch - now
        if x > 0:
            self.logHeartbeat(f"--> observer reminder due in {x} seconds")
            return
        
        #reminder is due !
        repeatCount = int(observer.get("repeatCount"))
        repeatMax = int(observer.get("repeatMax"))
        try:
            self.logHeartbeat(f"--> issuing a reminder for observer {observer.get("name")}")
            # self.dumpObserver(observer)
            dev = indigo.devices[int(observerId)]
            if dev:
                #perhaps this should simply increment the repeat count?
                #and let deviceUpdated fire off the observerResponse when needed
                repeatCount += 1
                observer["repeatCount"] = repeatCount
                #dev.states.updateOnServer("repeatCount",repeatCount)
                self.respond(dev,"--> reminder warranted")

        except Exception as e:
            self.logResponse(f"--> unable to issue reminder for observer {observer["name"]} {e}","error")
            observer["repeatScheduledEpoch"] = 0

    def considerAuthorization(self, observerId, observer):
        # perhaps this block should simply authorize the observer
        # and let deviceUpdated figure out whether to act on it,
        # treating attr responsAuthorized like and with responseAuthorized ?
        # as in, set the attr here, let the handler handle resposne ?

#                "responseGated": self.toBool(observer.pluginProps.get("responseGated", False) or False),
#                "responsePersistenceThreshold": int(observer.pluginProps.get("responsePersistenceThreshold", 0) or 0),
#                "responseGateDevice": observer.pluginProps.get("responseGateDevice", "none"),
#                "responseAuthorized": observer.states.get("responseAuthorized", True),
#                "activationEpoch": responseAuthorized,



        observerDev = indigo.devices[observerId]
        self.logHeartbeat(f"Considering authorization for {observer.get("name")}")

        oldAuth = observer.get("responseAuthorized")
        #we shouldnt even be here if the observer is off, but ...
        if ( not self.isOn(observerDev) ):
            self.logHeartbeat("--> (Observer is not on so will not be authorized)")            
            return

        # check if previously unauthrized observer is now authorized to respond
        responseAuthorized = self.getResponseAuthorization(observerDev)

        if oldAuth == responseAuthorized:
            self.logHeartbeat("--> Observer authorization is unchanged")
        else:
            self.logHeartbeat(f"--> Observer authorization changing from {oldAuth} to {responseAuthorized}")
            observer["responseAuthorized"] = responseAuthorized
            observerDev.updateStateOnServer("responseAuthorized", responseAuthorized)
            #device got updated, so deviceUpdated nshould kick in ?
            #bud it didnt, so here we are
            if responseAuthorized:
                self.respond(observerDev,"--> Response Threshold Met - Authority Granted")


    def reprocessActiveObservers(self):
        #THIS BLOCK IS CAUSING TROUBLE NOW
        #part 1 - "contine" is not the win here, 
        #as observers need to be considered for reminders as well
        #so lets doe reminders first?
        now = time.time()
        self.logHeartbeat("*** REPROCESSING ACTIVE OBSERVERS ***")
        for observerId, observer in self.observers.items():
            
            if observer.get("enabled") and observer.get("active"):

                if observer.get("responseGated") and observer.get("enabled"):
                    self.considerAuthorization(observerId,observer)

                if observer.get("repeat") and observer.get("enabled"):
                    self.considerReminders(observerId,observer)



    def push(self, msgTitle,msgBody,msgSound,msgPriority,msgDevice):

        alertPlugin = indigo.server.getPlugin('io.thechad.indigoplugin.pushover')
        if alertPlugin.isEnabled():
            try:
                alertProps = {'msgTitle':msgTitle, 'msgBody':msgBody, 'msgSound':msgSound, 'msgPriority':msgPriority, 'msgDevice':msgDevice, 'msgSupLinkUrl':'', 'msgSupLinkTitle':'','appToken':'ayxvb194vn466qbqj3caemvmrfuaje'} 
                alertPlugin.executeAction("send", props=alertProps)
                self.logResponse(f"Pushover send: {alertProps}")
            except:
              self.logResponse('Message send error', 'error')
        else:
            self.logResponse('Pushover plugin not available','error')

# ----------------------------------------------------------------------------------------------------------- #
#                                                                                                             #
# Logging 2.0                                                                                                 #
#                                                                                                             #
# ----------------------------------------------------------------------------------------------------------- #

    def logIt(self, message, emphasis="info"):
        now = time.time()
        formatted = time.strftime("%H:%M:%S", time.localtime(now))
        if emphasis=="warning":
            self.logger.warning(message + " @ " + formatted)        
        elif emphasis=="error":
            self.logger.error(message + " @ " + formatted)        
        elif emphasis=="debug":
            self.logger.debug(message + " @ " + formatted)        
        elif emphasis=="critical":
            self.logger.critical(message + " @ " + formatted)        
        else:
            self.logger.info(message + " @ " + formatted)        

    def logCheckpoint(self, message, emphasis="info"):
        message = "[Checkpoint] " + message
        if  self.loggingEnabled and self.logCheckpoints:
            self.logIt(message, emphasis)

    def logObserver(self, message, emphasis="info"):
        message = "[Observer] " + message
        if  self.loggingEnabled and self.logObservers:
            self.logIt(message, emphasis)

    def logResponse(self, message, emphasis="info"):
        message = "[Response] " + message
        if  self.loggingEnabled and self.logResponses:
            self.logIt(message, emphasis)

    def logHeartbeat(self, message, emphasis="info"):
        message = "[Heartbeat] " + message
        if  self.loggingEnabled and self.logHeartbeats:
            self.logIt(message, emphasis)

    def logError(self, message, emphasis="info"):
        message = "[Error] " + message
        if  self.loggingEnabled and self.logErrors:
            self.logIt(message, emphasis)

    def logOther(self, message, emphasis="info"):
        message = "[Other] " + message
        if  self.loggingEnabled and self.logOthers:
            self.logIt(message, emphasis)

    def logIntegration(self, message, emphasis="info"):
        message = "[Integration] " + message
        if  self.loggingEnabled and self.logIntegrations:
            self.logIt(message, emphasis)



