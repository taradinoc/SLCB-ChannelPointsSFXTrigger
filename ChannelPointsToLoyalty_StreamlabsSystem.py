# -*- coding: utf-8 -*-

#---------------------------
#   Import Libraries
#---------------------------
import clr, codecs, json, os, re, sys, threading, datetime

clr.AddReference("IronPython.Modules.dll")
clr.AddReferenceToFileAndPath(os.path.join(os.path.dirname(os.path.realpath(__file__)) + "\References", "TwitchLib.PubSub.dll"))
from TwitchLib.PubSub import TwitchPubSub

#---------------------------
#   [Required] Script Information
#---------------------------
ScriptName = "Twitch Channel Points To Cloudbot Loyalty"
Website = "https://www.twitch.tv/taradinoc"
Description = "Script to award Cloudbot loyalty points on channel point reward redemptions."
Creator = "EncryptedThoughts + TaradinoC"
Version = "1.0.0.0"

#---------------------------
#   Define Global Variables
#---------------------------
SettingsFile = os.path.join(os.path.dirname(__file__), "settings.json")
ReadMe = os.path.join(os.path.dirname(__file__), "README.txt")
EventReceiver = None
ThreadQueue = []
CurrentThread = None

#---------------------------------------
# Classes
#---------------------------------------
class Settings(object):
    def __init__(self, SettingsFile=None):
        if SettingsFile and os.path.isfile(SettingsFile):
            with codecs.open(SettingsFile, encoding="utf-8-sig", mode="r") as f:
                self.__dict__ = json.load(f, encoding="utf-8")
        else:
            self.EnableDebug = False
            self.Username = ""
            self.TwitchReward1Name = ""
            self.Conversion1Amount = 10
            self.TwitchReward2Name = ""
            self.Conversion2Amount = 10
            self.TwitchReward3Name = ""
            self.Conversion3Amount = 10
            self.TwitchReward4Name = ""
            self.Conversion4Amount = 10
            self.TwitchReward5Name = ""
            self.Conversion5Amount = 10

    def Reload(self, jsondata):
        self.__dict__ = json.loads(jsondata, encoding="utf-8")
        return

    def Save(self, SettingsFile):
        try:
            with codecs.open(SettingsFile, encoding="utf-8-sig", mode="w+") as f:
                json.dump(self.__dict__, f, encoding="utf-8")
            with codecs.open(SettingsFile.replace("json", "js"), encoding="utf-8-sig", mode="w+") as f:
                f.write("var settings = {0};".format(json.dumps(self.__dict__, encoding='utf-8')))
        except:
            Parent.Log(ScriptName, "Failed to save settings to file.")
        return

#---------------------------
#   [Required] Initialize Data (Only called on load)
#---------------------------
def Init():
    global ScriptSettings
    ScriptSettings = Settings(SettingsFile)
    ScriptSettings.Save(SettingsFile)

    ## Init the Streamlabs Event Receiver
    Start()

    return

def Start():
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Starting receiver");

    global EventReceiver
    EventReceiver = TwitchPubSub()
    EventReceiver.OnPubSubServiceConnected += EventReceiverConnected
    EventReceiver.OnListenResponse += EventReceiverListenResponse
    EventReceiver.OnRewardRedeemed += EventReceiverRewardRedeemed    

    EventReceiver.Connect()

def EventReceiverConnected(sender, e):

    #get channel id for username
    headers = { 'Client-ID': 'icyqwwpy744ugu5x4ymyt6jqrnpxso' }
    result = json.loads(Parent.GetRequest("https://api.twitch.tv/helix/users?login=" + ScriptSettings.Username,headers))
    user = json.loads(result["response"])
    id = user["data"][0]["id"]

    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Event receiver connected, sending topics for channel id: " + id);

    EventReceiver.ListenToRewards(id)
    EventReceiver.SendTopics()
    return

def EventReceiverListenResponse(sender, e):
    if ScriptSettings.EnableDebug:
        if e.Successful:
            Parent.Log(ScriptName, "Successfully verified listening to topic: " + e.Topic);
        else:
            Parent.Log(ScriptName, "Failed to listen! Error: " + e.Response.Error);
    return

def EventReceiverRewardRedeemed(sender, e):
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Event triggered")
    if e.RewardTitle == ScriptSettings.TwitchReward1Name:
        ThreadQueue.append(threading.Thread(target=RewardRedeemedWorker,args=(e, ScriptSettings.Conversion1Amount,)))
    if e.RewardTitle == ScriptSettings.TwitchReward2Name:
        ThreadQueue.append(threading.Thread(target=RewardRedeemedWorker,args=(e, ScriptSettings.Conversion2Amount,)))
    if e.RewardTitle == ScriptSettings.TwitchReward3Name:
        ThreadQueue.append(threading.Thread(target=RewardRedeemedWorker,args=(e, ScriptSettings.Conversion3Amount,)))
    if e.RewardTitle == ScriptSettings.TwitchReward4Name:
        ThreadQueue.append(threading.Thread(target=RewardRedeemedWorker,args=(e, ScriptSettings.Conversion4Amount,)))
    if e.RewardTitle == ScriptSettings.TwitchReward5Name:
        ThreadQueue.append(threading.Thread(target=RewardRedeemedWorker,args=(e, ScriptSettings.Conversion5Amount,)))
    return

def RewardRedeemedWorker(e, amount):
    user = e.Login
    status = e.Status
    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "redeeming " + str(amount) + " for " + user + ": " + status)

    if status == "UNFULFILLED":
        Parent.SendStreamMessage("!addpoints %s %d" % (user, amount))
    #global PlayNextAt
    #PlayNextAt = datetime.datetime.now() + datetime.timedelta(0, delay)


#---------------------------
#   [Required] Execute Data / Process messages
#---------------------------
def Execute(data):
    return

#---------------------------
#   [Required] Tick method (Gets called during every iteration even when there is no incoming data)
#---------------------------
def Tick():

    #global PlayNextAt
    #if PlayNextAt > datetime.datetime.now():
    #    return

    global CurrentThread
    if CurrentThread and CurrentThread.isAlive() == False:
        CurrentThread = None

    if CurrentThread == None and len(ThreadQueue) > 0:
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, "Starting new thread.")
        CurrentThread = ThreadQueue.pop(0)
        CurrentThread.start()
        
    return

#---------------------------
#   [Optional] Parse method (Allows you to create your own custom $parameters) 
#---------------------------
def Parse(parseString, userid, username, targetid, targetname, message):
    return parseString
#---------------------------
#   [Optional] Reload Settings (Called when a user clicks the Save Settings button in the Chatbot UI)
#---------------------------
def ReloadSettings(jsonData):
    # Execute json reloading here

    if ScriptSettings.EnableDebug:
        Parent.Log(ScriptName, "Saving settings.")

    global EventReceiver
    try:
        if EventReceiver:
            EventReceiver.Disconnect()

        ScriptSettings.__dict__ = json.loads(jsonData)
        ScriptSettings.Save(SettingsFile)
        EventReceiver = None

        Start()
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, "Settings saved successfully")
    except Exception as e:
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, str(e))

    return

#---------------------------
#   [Optional] Unload (Called when a user reloads their scripts or closes the bot / cleanup stuff)
#---------------------------
def Unload():
    # Disconnect EventReceiver cleanly
    try:
        if EventReceiver:
            EventReceiver.Disconnect()
    except:
        if ScriptSettings.EnableDebug:
            Parent.Log(ScriptName, "Event receiver already disconnected")

    return

#---------------------------
#   [Optional] ScriptToggled (Notifies you when a user disables your script or enables it)
#---------------------------
def ScriptToggled(state):
    return

def openreadme():
    os.startfile(ReadMe)
