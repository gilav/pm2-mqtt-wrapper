
Interface between MQTT and PM2
Lavaux Gilles 2017/05



 Does:
 - publish processes state
 - perform process on/off
 - based on crouton python client example: http://crouton.mybluemix.net/crouton/gettingStarted


 Mqtt topics will be like:
 - published message (send information and command reslt): /place/device/address
 - received message (get commands)                       : /place/device/address__in

 topic value meaning/syntax:
 - outgoing for info: value/state
 - incomming for command: >on/off/value
 - outgoing for command output: <on/off/value
 Notice incomming commands have < prefix, command result are outputed with > prefix



PM2 can be used to start a mqttHandler with the following command:
  >pm2 -n mqttHandler-pm2 start mqttHandler-pm2.py --interpreter python -- conf.d/raspi-home.conf

