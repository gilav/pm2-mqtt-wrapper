#
#
#
#
#

from abc import ABCMeta, abstractmethod
import sys,os,time
import subprocess
import traceback
import json

#
#
# various supported PM2 commands
COMMAND_PM2_JLIST='pm2 jlist'
COMMAND_PM2_START='pm2 start'
COMMAND_PM2_STOP='pm2 stop'
#
OP_START_STOP_SWITCH='startStopSwitchOP'
#
DEBUG=False



#
# exec a command
#
def execute(command):
    if DEBUG:
        print " ### will execute command:%s" % command
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Poll process for new output until finished
    while False:
        nextline = process.stdout.readline()
        if nextline == '' and process.poll() is not None:
            break
        sys.stdout.write(nextline)
        sys.stdout.flush()

    output = process.communicate()[0]
    exitCode = process.returncode
    if DEBUG:
        print " #######################  execute result; exitCode=%s, len(out)=%s" % (exitCode, output)

    return exitCode, output


#
# return human readable size
#
def GetHumanReadableSize(size,precision=2):
    suffixes=['B','KB','MB','GB','TB']
    suffixIndex = 0
    while size > 1024 and suffixIndex < 4:
        suffixIndex += 1 #increment the index of the suffix
        size = size/1024.0 #apply the division
    return "%.*f%s"%(precision,size,suffixes[suffixIndex])


#
# noop handler
# No Operation Handler: does nothing
#
def noop(cl, box, name, address, payload, pm2Binding):
    #if box!="inbox":
    #    raise Exception('box is not inbox')
    data = "noop: client=%s; box='%s'; name='%s'; address='%s'; payload='%s'" % (cl, box, name, address, payload)
    respTopic = "/outbox/%s/%s" % (name, address)
    return respTopic, data

#
# COMMAND_PM2_JLIST handler
# Perform a PM2 jlist command:
#
def jlist_op(cl, box, name, address, payload, pm2Binding):
    #if box!="inbox":
    #    raise Exception('box is not inbox')
    data={}
    data['value']='jlist'
    data['stdout'] = "jlist_op: client=%s; box='%s'; name='%s'; address='%s'; payload='%s'" % (cl, box, name, address, payload)
    data['out'] = 'N/A'
    respTopic = "/outbox/%s/%s" % (name, address)
    return respTopic, data

#
# COMMAND_PM2_STOP handler
#
def stop_op(cl, box, name, address, payload, pm2Binding):
    print " >>>>>> stop_op: client=%s; box='%s'; name='%s'; address='%s'; payload='%s'" % (cl, box, name, address, payload)
    # get pm2 process name from binding
    data={}
    if payload != 'off':
        raise Exception("start_op has not on value:'%s'" % data['value'])
    data['value']=payload
    pm2Process = pm2Binding[address]
    print " ###  stop_op pm2Process:%s" % pm2Process
    cmd='pm2 stop %s' % pm2Process
    exitCode, data['stdout'] = execute(cmd)
    if exitCode!=0:
        raise Exception('%s exicode != 0: %s' % (cmd, exitCode))
        # set switch position to on
        #respTopic = "/%s/%s/%s" % (box, name, address)
        #return respTopic, 'on'
    else:
        respTopic = "/%s/%s/%s" % (box, name, address)
        data['out'] = 'off'
        return respTopic, data

#
# COMMAND_PM2_START handler
#
def start_op(cl, box, name, address, payload, pm2Binding):
    print " >>>>>> start_op: client=%s; box='%s'; name='%s'; address='%s'; payload='%s'" % (cl, box, name, address, payload)
    # get pm2 process name from binding
    data={}
    if payload != 'on':
        raise Exception("start_op has not on value:'%s'" % data['value'])
    data['value']=payload
    pm2Process = pm2Binding[address]
    print " ###  start_op pm2Process:%s" % pm2Process
    cmd='pm2 start %s' % pm2Process
    exitCode, data['stdout'] = execute(cmd)
    if exitCode!=0:
        raise Exception('%s exicode != 0: %s' % (cmd, exitCode))
        # set switch position to off
        #respTopic = "/%s/%s/%s" % (box, name, address)
        #return respTopic, 'off'
    else:
        respTopic = "/%s/%s/%s" % (box, name, address)
        data['out'] = 'on'
        return respTopic, data

#
# OP_START_STOP_SWITCH handler
#
def start_stop_switch_op(cl, box, name, address, payload, pm2Binding):
    print " >>>>>> start_stop_switch_op: client=%s; box='%s'; name='%s'; address='%s'; payload='%s'" % (cl, box, name, address, payload)
    
    if payload=='on': 
        return start_op(cl, box, name, address, payload, pm2Binding)
    elif payload=='off':
        return stop_op(cl, box, name, address, payload, pm2Binding)
    else:
        raise Exception("Wrong on/off payload:'%s'" % payload)



#
# return the function associated with a binding
# at this time support only process start/stop
#
def getOpsFunction(opBinding):
    if opBinding==OP_START_STOP_SWITCH:
        return start_stop_switch_op
    else:
        raise Exception("unknown ops function:%s" % opBinding)
    


#
# perfoem a PM2 jlist command
# return a list of Pm2Process object
#
def do_jlist():
    print " > do pm2 jlist"
    res=[]
    cmd='pm2 jlist'
    exitCode, jsondata = execute(cmd)
    if exitCode!=0:
        raise Exception('%s exicode != 0: %s' % (cmd, exitCode))
    if DEBUG:
        print "  pm2 jlist done: output length=%s" % len(jsondata)

    
    # get fake one
    if 1==2:
        fd=open('res_5', 'r')
        jsondata=fd.read()
        fd.close()
        print "  pm2 jlist parsed"

    device = json.loads(jsondata)

    n=0
    for item in device:
        #print " process[%s]: pis=%s" % (n, item)
        j=0

        if 1==2:
            print " process[%s]: keys:" % item 
            for key in item.keys():
                print "   key[%s]=%s" % (j, key)
                j+=1

            j=0
            print " process[%s]: pm2_env keys:" % item 
            for key in item['pm2_env']:
                print "   pm2_env key[%s] %s=%s" % (j, key, item['pm2_env'][key])
                j+=1
            
        process=Pm2Process()
        process.pid=item['pid']
        monit=item['monit']
        if monit is not None:
            process.cpu=item['monit']['cpu']
            process.mem=item['monit']['memory']
        process.name=item['name']
        process.status=item['pm2_env']['status']
        process.restarts=item['pm2_env']['restart_time']
        res.append(process)
        n+=1
        print "  check done on process[%s]:%s" % (n, process.getInfo())

    print "   pm2 jlist found %s process" % len(res)
    return res


#
# will hold info of PM2 process
#
class Pm2Process():

    def __init__(self):
        self.pid=-1
        self.name=None
        self.status=''
        self.restarts=-1
        self.cpu=-1
        self.mem=-1

    def getInfo(self):
        return "PID:%s; name=%s; status=%s; restarts=%s; cpu=%s; mem=%s" % (self.pid, self.name, self.status, self.restarts, self.cpu, GetHumanReadableSize(self.mem))

    def  getName(self):
        return self.name

    def  getPid(self):
        return self.pid

    def  getStatus(self):
        return self.status

    def  getCpu(self):
        return self.cpu

    def  getMem(self):
        return self.mem

    def  getRestarts(self):
        return self.restarts

    def  isOnline(self):
        return self.status=='online'

    def  isStopped(self):
        return self.status=='stopped'

    def  isErrored(self):
        return self.status=='errored'

    
#
# define an abstract base handler
#
class Handler_Base():
    __metaclass__ = ABCMeta
    
    #
    #
    #
    def __init__(self, topic, fnct):
        if DEBUG:
            print(" init class Handler_Base; topic=%s; function=%s" % (topic, fnct))
        self.topic=topic
        self.fnct=fnct

    #
    #
    #
    def getInfo(self):
        return "Handler_Base for topic=%s; function=%s" % (self.topic, self.fnct)

    #
    #
    @abstractmethod
    def doMessage(selfs, cl, box, name, address, msg, payload, pm2Binding):
        pass


#
# define an handler
#
class PmHandler(Handler_Base):
    #
    #
    #
    def __init__(self, topic, fnct):
        Handler_Base.__init__(self, topic, fnct)
        print("init class PmHandler; topic=%s; function=%s" % (topic, fnct))

    #
    #
    #
    def doMessage(self, cl, box, name, address, payload, pm2Binding):
        if DEBUG:
            print(">>> doMessage using function %s: client=%s; box='%s'; name='%s'; address='%s'; payload='%s', pm2binding:%s" % (self.fnct, cl, box, name, address, payload, pm2Binding))
        respTopic, data = self.fnct(cl, box, name, address, payload, pm2Binding)
        return respTopic, data
        
#
# define a wrapper associated with a mqtt client.
# handlers will be associated with topic path, and will execute operations when mqtt messages are consumed
#
class Pm2Wrapper():
    #
    #
    #
    def __init__(self, id):
        print(" init class Pm2Wrapper")
        self.client = None
        self.id=id
        self.handlers={}

    #
    # get wrapper info
    #
    def getInfo(self):
        return "Pm2Wrapper %s; client=%s" % (self.id, self.client)

    #
    # set the mqtt client
    #
    def setClient(self, cl):
        self.client = cl

    #
    # get the mqtt client
    #
    def getClient(self):
        return self.client

    #
    # add an handler
    #
    def addHandler(self, topic, funct):
        anHandler = PmHandler(topic, funct)
        self.handlers[topic]=anHandler

    #
    # return handlers
    #
    def getHandlers(self):
        return self.handlers

    #
    # tell if a messages topic is known, i.e. has an associated handler
    #
    def knowsTopic(self, top):
        return self.handlers.has_key(top);   
        
    #
    # consume MQTT messages
    #
    def consumeMessage(self, cl, msg, payload, pm2Binding):
        if DEBUG:
            print(" consumeMessage: client=%s; msg=%s; payload='%s', pm2binding:%s" % (cl, msg, payload, pm2Binding))
        #print(msg.topic + ": " + str(msg.payload))
        box = msg.topic.split("/")[0]
        name = msg.topic.split("/")[1]
        address = msg.topic.split("/")[2]

        n=0
        done=0
        error=0
        for topic in self.handlers.keys():
            if DEBUG:
                print("  consumeMessage: test handler[%s]:'%s' vs topic:'%s'" % (n, topic, msg.topic))
            if topic==msg.topic:
                  if DEBUG:
                      print("!!!!!!!!!! consumeMessage: topic match")
                  try:
                      respTopic, data = self.handlers[topic].doMessage(cl, box, name, address, payload, pm2Binding)
                      if DEBUG:
                          print("!!!!!!!!!! consumeMessage result: topic='%s' data='%s'" % (respTopic, data))
                      if data.has_key('out'):
                          self.provideMessage(cl, respTopic, data['out'])
                      else:
                          raise Exception("result data has no 'out' key")
                      done+=1
                  except:
                      exc_type, exc_obj, exc_tb = sys.exc_info()
                      errorMsg = "!!!!!!!!!!!!!!!!!!!!!!!! consumeMessage on topic '%s' error:%s  %s\n%s\n" %  (msg.topic, exc_type, exc_obj, traceback.format_exc())
                      print errorMsg
                      error+=1
            n=n+1
            
        if DEBUG and done==0:
            print("!!!!!!!!!! consumeMessage: strange, no handler match topic")

    #
    #
    #
    def provideMessage(self, cl, topic, data):
        if DEBUG:
            print(" provideMessage: client=%s; topic='%s';  data='%s'" % (cl, topic, data))
        cl.publish(topic, '<'+data)


        
#
# used for test purpose:
# - create a handler with nNO Operation action associated to PM2 jlist command
#
def main():
    print "starting..."

    do_jlist()
    
    wrapper = Pm2Wrapper('pmw-wrapper-test')
    print " wrapper created"
    wrapper.addHandler(COMMAND_PM2_JLIST, noop)
    print " noop handler added"

#
# used for test purpose
#
if __name__ == "__main__":
    main()
