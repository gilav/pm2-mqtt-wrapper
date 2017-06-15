#
# interface between MQTT and PM2
#
# Does:
# - publish processes state
# - perform process on/off
# - based on crouton python client example: http://crouton.mybluemix.net/crouton/gettingStarted
#
#
# topics will be like:
# - published message (send information and command reslt): /place/device/address
# - received message (get commands)                       : /place/device/address__in
#
# topic value meaning/syntax:
# - outgoing for info: value/state
# - incomming for command: >on/off/value
# - outgoing for command output: <on/off/value
#
#
# Lavaux Gilles 2017/05
#
# IMPORTANT:
# - connect to MQTT using normal mode (not WS), using non TLS connection.
# - the mqtt user + password IS DEFINED in the native.py file. When configured, set it in .pyc and remove the .py (this is a very basic password hidding)
#
#
import paho.mqtt.client as mqtt
import os,sys,time
import ConfigParser
import traceback
from datetime import datetime
import json


#
from pm2 import pm2

#
VERSION="V:0.9.1 Lavaux Gilles 2017/04"

#
configPath=None


# configuration setting properties name
# configuration are in a conf.d subfolder
SETTING_Main='Main'
SETTING_place='place'
SETTING_device='device'
SETTING_clientName='clientName'
SETTING_hostname='hostname'
SETTING_Main='Main'
SETTING_port='port'
SETTING_user='user'
SETTING_password='password'
SETTING_delay='sendDelay'
SETTING_Ui='Ui'
SETTING_DEBUG='DEBUG'
SETTING_config_ui='config_ui'
SETTING_Pm2Binding='Pm2Binding'
SETTING_Pm2OpsBinding='Pm2OpsBinding'

# MQTT broker address
hostname='not-set'
port=-1
user=None
password=None
# delay between ststus send
delay=60

# global
clientName=None
deviceJson=None
configPath=None

# global
pmwrapper=None
devicePm2Binding={}
devicePm2OpsBinding={}
connected=False
connectNum=0


#
DEBUG=False


#
# current date time
#
def dateNow():
    d=datetime.fromtimestamp(time.time())
    return d.strftime("%Y-%m-%d %H:%M:%S")





#
# create a pm2 wrapper
#
def createWrapper(name):
    wrapper = pm2.Pm2Wrapper(name)
    print " got pmwrapper:%s" % wrapper
    return wrapper



#
# get pm2 processes state and publish it
#
def publishProcessState(cl, placeName, deviceName):
    global devicePm2Binding, devicePm2OpsBinding, deviceJson
    if DEBUG:
        print " publishProcessState; place=%s; device=%s" % (placeName, deviceName)
    if len(devicePm2Binding.keys()) == 0:
        if DEBUG:
            print " publishProcessState: devicePm2Binding is empty"
        return
    
    # do a pm2 jlist
    process = pm2.do_jlist()
    for item in devicePm2Binding:
        if not item.endswith('__in'):
            procName = devicePm2Binding[item]
            topic = "%s/%s/%s" % (placeName, deviceName, item)
            if DEBUG:
                print "\n publishProcessState: topic 0:'%s'" % topic
                print " publishProcessState: test pm2 process for %s; pm2 process name=%s" % (item, procName)
            done=False
            for proc in process:
                if proc.getName()==procName:
                    if DEBUG:
                        print " publishProcessState:    publishProcessState: found process %s" % procName
                    done=True
                    if DEBUG:
                        print " publishProcessState: publish status for found process:%s: dump:%s" % (procName,  proc.getInfo())
                    if proc.isOnline():
                        info="%s CPU:%s MEM:%s Restarts:%s" % (proc.getStatus().capitalize(), ("%s" % proc.getCpu())+'%', pm2.GetHumanReadableSize(proc.getMem(), 1), proc.getRestarts())
                    else:
                        info="%s Restarts:%s" % (proc.getStatus().capitalize(), proc.getRestarts())
                    switchOn = proc.getStatus()=='online'
                    doPublish(cl, topic, info)
                    
                    # if there is a op binding for 'topicxxx__in', publish switch state
                    if devicePm2OpsBinding.has_key(item+'__in'):
                        if DEBUG:
                            print " publishProcessState: publish status for found process '%s' OPS: state=%s" % (item,  switchOn)
                        if switchOn:
                            doPublish(cl, topic+'__in', '<on')
                        else:
                            doPublish(cl, topic+'__in', '<off')
                    else:
                        if DEBUG:
                            print " publishProcessState: process %s has NO OPS" % procName
                    done=True
                    break
            if not done:
                if DEBUG:
                    print " publishProcessState: publish status for NOT found process:%s:" % procName
                # if there is a op binding, set xxx_switch state
                if devicePm2OpsBinding.has_key(item+'__in'):
                    if DEBUG:
                        print " publishProcessState: publish status for found process '%s' OPS: off" % (item)
                    doPublish(cl, topic+'__in', '<off')
                else:
                    if DEBUG:
                        print " publishProcessState: process %s has NO OPS" % procName

#
# publish to mqtt
#
def doPublish(cl, topic, data):
    try:
        if DEBUG:
            print " ## doPublish: topic=%s; data='%s'" % (topic, data)
        cl.publish(topic, data)
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        errorMsg = " !! doPublish ERROR on topic='%s'; data='%s':%s  %s" %  (topic, data, exc_type, exc_obj)
        print errorMsg
        traceback.print_exc(file=sys.stdout)


#
# get pm2 process name and operation binding
#
def getPm2Binding(config):
    global devicePm2Binding, devicePm2OpsBinding
    if DEBUG:
        print "###  getInitialProcessState"
    bindings = config.items(SETTING_Pm2Binding)
    print " bindings:%s" % bindings
    for item in bindings:
        if DEBUG:
            print " do pm2 binding for:%s" % (item,)
        devicePm2Binding[item[0]] = item[1]

    bindings = config.items(SETTING_Pm2OpsBinding)
    for item in bindings:
        print " do pm2 ops binding for:%s" % (item,)
        devicePm2OpsBinding[item[0]] = item[1]

    

#
# load a configuration:
#
#
def loadConfig(aPath, aName):
    global connectNum, hostname, port, user, password, delay, clientName, deviceJson, DEBUG
    tmp=aPath
    if aName is not None:
        tmp = "%s/%s" % (aPath, aName)
    print "  loadConfig:'%s'" % tmp
    __config = ConfigParser.RawConfigParser()
    __config.optionxform=str
    __config.read(tmp)
    clientName = __config.get(SETTING_Main, SETTING_clientName)
    clientPlace = __config.get(SETTING_Main, SETTING_place)
    clientDevice = __config.get(SETTING_Main, SETTING_device)
    configUi = __config.get(SETTING_Ui, SETTING_config_ui)
    hostname = __config.get(SETTING_Main, SETTING_hostname)
    port = int(__config.get(SETTING_Main, SETTING_port))
    try:
        user = __config.get(SETTING_Main, SETTING_user)
    except:
        print " no user set!"
        pass
    try:
        password = __config.get(SETTING_Main, SETTING_password)
    except:
        print " no password set!"
        pass
    delay = int(__config.get(SETTING_Main, SETTING_delay))
    try:
        DEBUG = __config.get(SETTING_Main, SETTING_DEBUG)
        if DEBUG=='on':
            print "  debug config: %s" % DEBUG
            DEBUG=True
    except:
        print "  no debug config, use default"
    print "  broker %s:%s; ststus send delay:%s" % (hostname, port, delay)
    #if user != None and password != None:
    #print "  broker user:%s; password:xxxx" % (user)
    print "  client %s; place=%s; device=%s\n  ui=%s" % (clientName, clientPlace, clientDevice, configUi)

    device=None
    if aName is not None:
        with open("%s/%s" % (aPath, configUi), 'r') as fichier:
            device = json.load(fichier)
    else:
        with open("%s/%s" % (os.path.dirname(aPath), configUi), 'r') as fichier:
            device = json.load(fichier)
    device["deviceInfo"]["clientName"] = clientName
    device["deviceInfo"]["place"] = clientPlace
    device["deviceInfo"]["device"] = clientDevice
    deviceJson = json.dumps(device)

    #
    getPm2Binding(__config)

    #
    while True:
        try:
            connectNum+=1
            print "  calling createMqttClient[%s]" % connectNum
            createMqttClient(device, clientPlace, clientDevice)
            print "  client exited? will re create it in 60 secs"
        except:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            errorMsg = "  !!! create mqtt client error:%s  %s\n  will re create it in 60 secs" %  (exc_type, exc_obj)
            print errorMsg
        time.sleep(60)

    print "######################################   loadConfig '%s' done" % aPath


#
# create a mqtt client
#
def createMqttClient(device, clientPlace, clientDevice):
    global connected, user, password, deviceJson, pmwrapper, devicePm2OpsBinding, clientName, deviceJson # clientPlace, clientDevice,
    print " will create client name='%s'; clientPlace=%s; clientDevice=%s" % (clientName, clientPlace, clientDevice)
    client = mqtt.Client(clientName)
    if user!=None and password != None:
        print " setting client user and password"
        import native
        client.username_pw_set(native.user, native.password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.will_set('%s/%s/lwt' % (clientPlace, clientDevice), 'anythinghere', 0, False)
    print " client '%s' created" % clientName

    client.connect(hostname, port, 60)
    print " client '%s' connected to %s:%s" % (clientName, hostname, port)
    connected=True

    # create the MP2 wrapper, populate it with handlers for all bindings
    pmwrapper = createWrapper(clientName)
    n=0
    for key in device["deviceInfo"]["endPoints"]:
        aTopic = '%s/%s/%s' % (clientPlace, clientDevice, str(key))
        print "   endPoints %s; topic=%s" % (key, aTopic) 
        # get needed handler operation if any
        if devicePm2OpsBinding.has_key(key):
            op = devicePm2OpsBinding[key]
            print "   client %s op=%s" % (clientName, op) 
            fnc = pm2.getOpsFunction(op)
            print "   client %s function=%s" % (clientName, fnc) 
            pmwrapper.addHandler(aTopic, fnc)
            # subscribe to topic__in to receive commands from mqtt
            aTopic
            client.subscribe(aTopic)
            print " !!!! client %s subscribed[%s] to: '%s' done, pmwrapper set." % (clientName, n, aTopic)
        else:
            print " no OPS binding"
            
        n=n+1
    print " client %s subscribe/publish done" % clientName

    # initial process state publish
    publishProcessState(client, clientPlace, clientDevice)

    print " will do client %s  loop_start" % clientName
    client.loop_start()
    numLoop=0
    actionTime=time.time()+delay
    while connected:
        if time.time() > actionTime:
            now = dateNow()
            print "\n\n > mqttHandler-pm2 loop[%s] at %s" % (numLoop, now)
            doAction(client, clientPlace, clientDevice, now)
            print " waiting %s sec..." % delay
            numLoop+=1
            actionTime=time.time()+delay
        else:
            print " still %s sec..." % int(actionTime - time.time())
        time.sleep(1)
    client.loop_stop(True)
    print "######################################   client.loop_stop done"


#
# method used in loop
# publish data + time + processes state
#
def doAction(client, clientPlace, clientDevice, now):
        adate = now.split(' ')[0]
        atime = now.split(' ')[1]
        client.publish('%s/%s/%s' % (clientPlace, clientDevice, 'aDate'), str(adate))
        client.publish('%s/%s/%s' % (clientPlace, clientDevice, 'aTime'), str(atime))
        publishProcessState(client, clientPlace, clientDevice)


#
#
# mqtt callbacks
#
#

#callback when we recieve a connack
def on_connect(client, userdata, flags, rc):
    print(" >> on_connect with result code " + str(rc))


#callback when we receive a published message from the server
def on_message(client, userdata, msg):
    global pmwrapper
    topic = str(msg.topic)
    print(" >> on_message: topic='"+topic + "': " + str(msg.payload)+"; userData=%s" % userdata)
    toks = topic.split("/")
    if len(toks) != 3: # because topic starts with /
        raise Exception("unsupported topic format(wrong number of tokens %s):%s" % (len(toks), topic))
    
    place = topic.split("/")[0]
    device = topic.split("/")[1]
    address = topic.split("/")[2]
    payload = str(msg.payload)
    print("  place='"+place + "'; device='" + device + "'; address='" + address + "'; payload='" + payload +"'")

    if payload.startswith('<'):
        print("  is an incomming command feedback, dismiss it")
        return
    
    if address.endswith('__in'):
        if pmwrapper.knowsTopic(msg.topic):
            if payload.startswith('>'):
                pmwrapper.consumeMessage(client, msg, msg.payload[1:], devicePm2Binding)
            else:
                print("  skipped invalid incomming command(payload not starting with '>'):%s" % payload)
    else:
        print("  skipped invalid input topic(not ending with '__in'):%s" % address)


#
# callback on disconnect
# does nothing, hust set the connected flag to false, this will stop the client loop
# does nothing because this software will be run by something that will take care of restarting it on exit (PM2 or superviror or systemd)
#
def on_disconnect(client, userdata, rc):
    global connected
    print(" >> on_disconnect")
    connected=False
    if rc != 0:
        print("Broker disconnection:%s" % rc)
    #time.sleep(10)
    #print(" client reconnect to %s:%s ..." % (hostname, port))
    #client.connect(hostname, port, 60)





#
#
#
def main(aPath):
    global configPath
    configPath=aPath
    print "\nmqttHandler for PM2 %s" % VERSION
    print "starting, using configuration path:'%s'" % configPath
    if os.path.isfile(configPath):
        if configPath.endswith(".conf"):
            print " applying configuration item:%s" % configPath
            try:
                loadConfig(configPath, None)
            except:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                errorMsg = "  !!! config load error on '%s' error:%s  %s\n%s\n" %  (configPath, exc_type, exc_obj, traceback.format_exc())
                print errorMsg
        else:
            print " confg file dont ends with .conf:%s" % configPath
    else:
        print " config is not a file:%s" % configPath


#
#
#
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:    
        print "syntax: python mqttHandler-xxx.py configPath"


