#
#       Denon AVR Plugin
#
#       Author:     Dnpwwo, 2016 - 2023
#
#   Mode4 ("Sources") needs to have '|' delimited names of sources that the Denon knows about.  The Selector can be changed afterwards to any  text and the plugin will still map to the actual Denon name.
#
"""
<plugin key="DenonEx" version="4.0.1" name="Denon/Marantz Amplifier" author="dnpwwo,bvr" wikilink="" externallink="http://www.denon.co.uk/uk">
    <description>
Denon (& Marantz) AVR/AVC Plugin.<br/><br/>
&quot;Sources&quot; need to have '|' delimited names of sources that the Denon knows about from the technical manual.<br/>
The Sources Selector(s) can be changed after initial creation to any text and the plugin will still map to the actual Denon name.<br/><br/>
Devices will be created in the Devices Tab only and will need to be manually made active.<br/><br/>
Auto-discovery is known to work on Linux but may not on Windows.
    </description>
    <params>
        <param field="Port" label="Port" width="30px" required="true" default="23"/>
        <param field="Mode1" label="Auto-Detect" width="75px">
            <options>
                <option label="True" value="Discover" default="true"/>
                <option label="False" value="Fixed" />
            </options>
        </param>
        <param field="Address" label="IP Address" width="200px"/>
        <param field="Mode2" label="Discovery Match" width="250px" default="SDKClass=Receiver"/>
        <param field="Mode3" label="Startup Delay" width="50px" required="true">
            <options>
                <option label="2" value="2"/>
                <option label="3" value="3"/>
                <option label="4" value="4" default="true" />
                <option label="5" value="5"/>
                <option label="6" value="6"/>
                <option label="7" value="7"/>
                <option label="10" value="10"/>
            </options>
        </param>
        <param field="Mode4" label="Sources" width="550px" required="true" default="Off|DVD|VDP|TV|CD|DBS|Tuner|Phono|VCR-1|VCR-2|V.Aux|CDR/Tape|AuxNet|AuxIPod"/>
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Python" value="18"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""
import DomoticzEx as Domoticz
import base64
import datetime

denonConn = None
denonName = "Receiver"
oustandingPings = 0
lastHeartbeat = datetime.datetime.now()
lastMessage = -1

deviceMessages = "|PW|ZM|Z2|Z3|"
ignoreMessages = "|SS|SV|SD|MS|PS|CV|SY|TP|"

sourceOptions = {}
selectorMap = {}

class zoneUnit(Domoticz.Unit):
    def __init__(self, Name, DeviceID, Unit, TypeName="", Type=0, Subtype=0, Switchtype=0, Image=0, Options="", Used=0, Description=""):
        super().__init__(Name, DeviceID, Unit, TypeName, Type, Subtype, Switchtype, Image, Options, Used, Description)
        self.Refresh()  # Only DeviceID and Unit will be populated this early in the initialisation process so force a refresh

        if (self.SubType == 73) and (self.SwitchType == 0):
            self.__class__ = switchUnit     # Run time polymorphism Python style
        elif (self.SubType == 73) and (self.SwitchType == 7):
            self.__class__ = volumeUnit
        elif (self.SubType == 62):
            self.__class__ = selectorUnit
        else:
            Domoticz.Error("Default Zone object type used: "+DeviceID+"/"+str(Unit))

    def Update(self, nValue, sValue, Log=False):
        if (self.nValue != nValue) or (self.sValue != sValue):
            Domoticz.Log("Unit '"+self.Parent.DeviceID+"/"+str(self.Unit)+"' onMessage, old: "+str(self.nValue)+","+self.sValue+"', new: "+str(nValue)+",'"+sValue+"'")
            self.nValue = nValue
            self.sValue = sValue
            super().Update(Log=Log)

    def preCommand(self, Command):
        global denonConn,lastHeartbeat

        Command = Command.upper().strip()
        zoneAbbrev = self.Parent.DeviceID[-2:]
        Domoticz.Log("onCommand called for '" + str(self.Name)+ "': in Zone: '"+zoneAbbrev+"', Parameters '" + str(Command) + "'")

        delay = 0
        if (self.Parent.Units[1].nValue == 0):
            # Amp will ignore commands if it is responding to a heartbeat so delay send
            lastHeartbeatDelta = (datetime.datetime.now()-lastHeartbeat).total_seconds()
            if (lastHeartbeatDelta < 0.5):
                delay = 1
                Domoticz.Log("Last heartbeat was "+str(lastHeartbeatDelta)+" seconds ago, delaying command send.")
            denonConn.Send(Message=zoneAbbrev+'ON\r', Delay=delay)
            # Allow time for the amp boot up
            delay += int(Parameters["Mode3"])
            
        return zoneAbbrev,Command,delay

class switchUnit(zoneUnit):   # On/Off switch onCommand Handler

    def onCommand(self, Command, Level, Hue):
        global denonConn
        zoneAbbrev,Command,delay = self.preCommand(Command)
        denonConn.Send(Message=zoneAbbrev+Command+'\r', Delay=delay)

class selectorUnit(zoneUnit): # Selector switch onCommand Handler

    def onCommand(self, Command, Level, Hue):
        global denonConn,selectorMap
        zoneAbbrev,Command,delay = self.preCommand(Command)
        denonConn.Send(Message=(zoneAbbrev if zoneAbbrev != "ZM" else "SI")+selectorMap[Level].upper()+'\r', Delay=delay)

class volumeUnit(zoneUnit):   # Volume switch onCommand Handler

    def onCommand(self, Command, Level, Hue):
        global denonConn
        zoneAbbrev,Command,delay = self.preCommand(Command)
        if (Command == "ON"):
            message = (zoneAbbrev if zoneAbbrev != "ZM" else "") + "MUOFF"
        elif (Command == "OFF"):
            message = (zoneAbbrev if zoneAbbrev != "ZM" else "") + "MUON"
        elif (Command == "SET LEVEL"):
            message = ('MV' if zoneAbbrev == "ZM" else zoneAbbrev) + str(Level)
        Domoticz.Log("onCommand sending: '"+message+"'")
        denonConn.Send(Message= message+'\r', Delay=delay)

class zoneDevice(Domoticz.Device):
    def __init__(self, DeviceID):
        super().__init__(DeviceID)
        zoneAbbrev = self.DeviceID[-2:]
        if (zoneAbbrev == "ZM"):
            self.__class__ = mainZoneDevice     # Run time polymorphism Python style

    def onMessage(self, action, detail):
        global sourceOptions,selectorMap
        Domoticz.Debug("Device '"+self.DeviceID+"' onMessage, detail: '"+detail+"'")

        # Power related?
        if detail in ["STANDBY","OFF","ON"]:
            if not 1 in self.Units:
                zoneUnit(DeviceID=self.DeviceID, Name="Power", Unit=1, TypeName="Switch", Image=5).Create()
            if (detail == "ON"):
                self.Units[1].Update(1, "ON", True)
            else:
                self.Units[1].Update(0, "OFF", True)
        # Source Input?
        elif (sourceOptions['LevelNames'].find(detail) > 0):
            if not 2 in self.Units:
                zoneUnit(DeviceID=self.DeviceID, Name="Source", Unit=2, TypeName="Selector Switch", Switchtype=18, Image=5, Options=sourceOptions).Create()
            for key, value in selectorMap.items():
                if (detail == value):
                    self.Units[2].Update(key if self.Units[1].nValue != 0 else 0, str(key) if self.Units[1].nValue != 0 else "0", True)
        # Volume?
        elif (detail.isdigit()):
            if not 3 in self.Units:
                zoneUnit(DeviceID=self.DeviceID, Name="Volume", Unit=3, Type=244, Subtype=73, Switchtype=7, Image=8).Create()
            self.Units[3].LastLevel = int(detail)
            self.Units[3].Update(0 if (int(detail) <= 0) or (self.Units[1].nValue == 0) else 2, detail)
        elif (detail in ["MUOFF","MUON"]):
            if not 3 in self.Units:
                Domoticz.Unit(DeviceID=self.DeviceID, Name="Volume", Unit=3, Type=244, Subtype=73, Switchtype=7, Image=8).Create()
            self.Units[3].Update(0 if detail == "MUON" or (self.Units[1].nValue == 0) else 2, self.Units[3].sValue)

    def Poll(self):
        message = self.DeviceID[-2:]+"?"
        Domoticz.Debug("Poll sending: '"+message+"'")
        denonConn.Send(Message= message+'\r')

class mainZoneDevice(zoneDevice):

    def Poll(self):
        Domoticz.Debug("Polling Main Zone")
        denonConn.Send(Message = 'ZM?\r', Delay=1)
        denonConn.Send(Message = 'SI?\r', Delay=2)
        denonConn.Send(Message = 'MV?\r', Delay=3)
        denonConn.Send(Message = 'MU?\r', Delay=4)

Domoticz.Register(Device=zoneDevice, Unit=zoneUnit)

def onStart():
    global sourceOptions,selectorMap
    Domoticz.Log("onStart called")
    if Parameters["Mode6"] != "0":
        Domoticz.Debugging(int(Parameters["Mode6"]))
        DumpConfigToLog()

    sourceOptions = {'LevelActions': '|'*Parameters["Mode4"].count('|'),
                     'LevelNames': Parameters["Mode4"],
                     'LevelOffHidden': 'false',
                     'SelectorStyle': '1'}
    dictValue=0
    for item in Parameters["Mode4"].split('|'):
        selectorMap[dictValue] = item
        dictValue = dictValue + 10   

def onConnect(Connection, Status, Description):
    global denonConn
    if (Connection == denonConn):
        if (Status == 0):
            Domoticz.Status("Connected successfully to: "+Connection.Address+":"+Connection.Port)
            for key in Devices:
                Devices[key].TimedOut = 0
            denonConn.Send('PW?\r')
            denonConn.Send('ZM?\r', Delay=1)
            denonConn.Send('Z2?\r', Delay=2)
            denonConn.Send('Z3?\r', Delay=3)
    else:
        if (Description.find("Only one usage of each socket address") > 0):
            Domoticz.Log(Connection.Address+":"+Connection.Port+" is busy, waiting.")
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
        denonConn = None

def onMessage(Connection, Data):
    global denonConn,denonName,oustandingPings,deviceMessages,ignoreMessages
    strData = Data.decode("utf-8", "ignore")
    Domoticz.Debug("onMessage called with Data: '"+str(strData)+"'")
    oustandingPings = 0

    try:
        # Beacon messages to find the amplifier
        if (Connection.Name == "Beacon"):
            dictAMXB = DecodeDDDMessage(strData)
            if (strData.find(Parameters["Mode2"]) >= 0):
                denonConn = None
                denonConn = Domoticz.Connection(Name="Telnet", Transport="TCP/IP", Protocol="Line", Address=Connection.Address, Port=Parameters["Port"])
                denonConn.Connect()
                try:
                    Domoticz.Log(dictAMXB['Make']+", "+dictAMXB['Model']+" Receiver discovered successfully at address: "+Connection.Address)
                    denonName = dictAMXB['Make']+"-"+dictAMXB['Model']
                except KeyError:
                    Domoticz.Log("'Unknown' Receiver discovered successfully at address: "+Connection.Address)
            else:
                try:
                    Domoticz.Log("Discovery message for Class: '"+dictAMXB['SDKClass']+"', Make '"+dictAMXB['Make']+"', Model '"+dictAMXB['Model']+"' seen at address: "+Connection.Address)
                except KeyError:
                    Domoticz.Log("Discovery message '"+str(strData)+"' seen at address: "+Connection.Address)
        # Otherwise handle amplifier
        else:
            strData = strData.strip()
            action = strData[0:2]
            action2= strData[0:4]
            detail = strData[2:]
            
            # Only process messages that we aren't ignoring
            if (ignoreMessages.find(action) < 0):
                # Make sure we have the base devices created if required
                if (deviceMessages.find(action) > 0):
                    if not denonName+":"+action in Devices:
                        zoneUnit(DeviceID=denonName+":"+action, Name="Power", Unit=1, TypeName="Switch", Image=5).Create()
                    # Power and all Z2 and Z3 message will go through here
                    Devices[denonName+":"+action].onMessage(action,detail)
                else:
                    # Other assume these are for the Main Zone
                    if (action == "MU"):
                        Devices[denonName+":ZM"].onMessage("ZM", action+detail)  # Distinguish from power events. Sen MUON, MUOFF
                    else:
                        Devices[denonName+":ZM"].onMessage(action,detail)

    except Exception as inst:
        Domoticz.Error("Exception in onMessage, called with Data: '"+str(strData)+"'")
        Domoticz.Error("Exception detail: '"+str(inst)+"'")
        raise

def onDisconnect(Connection):
    global denonConn
    denonConn = None
    Domoticz.Status("Disconnected from: "+Connection.Address+":"+Connection.Port)
    for key in Devices:
        Devices[key].TimedOut = 1

def onHeartbeat():
    global denonConn,denonName,oustandingPings,lastHeartbeat,lastMessage
    Domoticz.Debug("onHeartbeat called, last response seen "+str(oustandingPings)+" heartbeats ago.")
    if (denonConn == None):
        if Parameters["Mode1"] == "Discover":
            Domoticz.Log("Using auto-discovery mode to detect receiver as specified in parameters.")
            denonConn = Domoticz.Connection(Name="Beacon", Transport="UDP/IP", Address="239.255.250.250", Port=str(9131))
            denonConn.Listen()
        else:
            Domoticz.Log("Connecting to receiver on " + Parameters["Address"] + ":" + Parameters["Port"] + " as specified in parameters.")
            denonConn = Domoticz.Connection(Name="Telnet", Transport="TCP/IP", Protocol="Line", Address=Parameters["Address"], Port=Parameters["Port"])
            denonName = Address=Parameters["Address"]
            denonConn.Connect()
    else:
        if (denonConn.Name == "Telnet") and (denonConn.Connected()):
            lastMessage = lastMessage + 1
            if (lastMessage >= len(Devices)): lastMessage = 0
            for Device in Devices:
                Devices[Device].Poll()
        #    denonConn.Send(pollingDict[lastMessage])
        #    Domoticz.Debug("onHeartbeat: Sending '"+str(pollingDict[lastMessage])+"'.")

        if (oustandingPings > 10):
            Domoticz.Error(denonConn.Name+" has not responded to 10 pings, terminating connection.")
            if (denonConn.Connected()):
                denonConn.Disconnect()
            denonConn = None
            oustandingPings = -1
        oustandingPings = oustandingPings + 1
        lastHeartbeat = datetime.datetime.now()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for DeviceName in Devices:
        Device = Devices[DeviceName]
        Domoticz.Debug("Device ID:       '" + str(Device.DeviceID) + "'")
        Domoticz.Debug("--->Unit Count:      '" + str(len(Device.Units)) + "'")
        for UnitNo in Device.Units:
            Unit = Device.Units[UnitNo]
            Domoticz.Debug("--->Unit:           " + str(UnitNo))
            Domoticz.Debug("--->Unit Name:     '" + Unit.Name + "'")
            Domoticz.Debug("--->Unit nValue:    " + str(Unit.nValue))
            Domoticz.Debug("--->Unit sValue:   '" + Unit.sValue + "'")
            Domoticz.Debug("--->Unit LastLevel: " + str(Unit.LastLevel))
    return

def DecodeDDDMessage(Message):
    # Sample discovery message
    # AMXB<-SDKClass=Receiver><-Make=DENON><-Model=AVR-4306>
    strChunks = Message.strip()
    strChunks = strChunks[4:len(strChunks)-1].replace("<-","")
    dirChunks = dict(item.split("=") for item in strChunks.split(">"))
    return dirChunks
