import time
import datetime
import json
import sys
import paho.mqtt.client as mqtt
from mqtt_command_queue import CommandQueue

sys.path.append("./BHSTools")
from BHSTools.intellibus import *


# PUBLISHED TOPICS
# topic -> body
#
# ${topicRoot}/zone/${zone_name} -> "Ready"|"Not Ready"
# ${topicRoot}/system -> "Ready"|"Not Ready"
# ${topicRoot}/arm -> "Armed"|"Disarmed"
# ${topicRoot}/time -> current system time
# ${topicRoot}/command/result -> result of recently executed command
#
#
# CONSUMED TOPICS
#
# ${topicRoot}/command -> {"op": number, "args": string[]} (supports all commands that command.py supports as of Nov 2021)
# ${topicRoot}/command/query -> zone number
# ${topicRoot}/command/arm -> delay in seconds, does not bypass
# ${topicRoot}/command/disarm -> no body
# ${topicRoot}/command/code -> no body

configFile = open('mqtt_config.json')
configuration = json.load(configFile)
configFile.close()

client = mqtt.Client(client_id=configuration['mqtt']['client_id'])


def publish(topic, value):
	client.publish(configuration['mqtt']['topic_root'] + topic, value, qos=1, retain=True)

def publish_zone_state(zone, state):
	zone_name = configuration['zone_names'][zone]
	state = "Ready" if state else "Not ready"
	print(zone_name + " " + state)
	publish("zone/" + zone_name, state)
	
def publish_system_state(state):
	print("System " + ("ready" if state else "not ready"))
	publish("system", "Ready" if state else "Not ready")

def publish_arm_state(state):
	print("System " + ("armed" if state else "disarmed"))
	publish("arm", "Armed" if state else "Disarmed")
	
def publish_time(time):
	time = time.strftime("%a, %b %d, %Y %I:%M %p")
	#print("Time: " + time) 
	publish("time", time)
	
def publish_command_result(result):
	publish("command/result", result)

def handle_announcement(args):
	if args[0] == 54: #current time
		d = datetime.datetime(2000 + args[1], args[2], args[3], args[4], args[5], args[6])
		publish_time(d)
	elif args[0] == 36: #zone not ready
		publish_zone_state(args[1], False)
	elif args[0] == 37: #zone ready
		publish_zone_state(args[1], True)
	elif args[0] == 43: #system not ready
		publish_system_state(False)
	elif args[0] == 42: #system ready
		publish_system_state(True)
	elif args[0] == 50: #armed
		publish_arm_state(True)
	elif args[0] == 51: #disarmed
		publish_arm_state(False)
	elif args[0] == 44: #countdown start
		print("Countdown start")
	elif args[0] == 45: #countdown end
		print("Countdown end")
	elif args[0] == 34: #arm state change?
		pass
	elif args[0] == 4 or args[0] == 5: #duplicate? zone ready announcements
		pass
	else:
		print('Unrecognized announcement ' + args.hex(sep=' '), end=' | ')
		for my_byte in args:
			print(my_byte, end=' ')
		print()


def command_complete(cmd, args, result):
	#result is bytes or string
	result_string = result
	if isinstance(result, bytes):
		result_string = tohex(result) + " | " + result.decode("utf-8")
	if result_string:
		result_string = " with: " + result_string
	else:
		result_string = ""
	
	result_string = "command: " + str(cmd) + " (" + str(args) + ") " + " completed" + result_string + "."
	publish_command_result(result_string)
	#print(result_string)
		
	if cmd == 709: #query zone
		publish_zone_state(result[2], not result[3])
	elif cmd == 16: #echo
		print("Echo: " + tohex(result))
	elif cmd == 90: #DB record
		print("DB: " + result.decode("utf-8"))
	elif cmd == 1000: #arm
		success = result[1] == 0
		result_string = "Arm " + ("complete" if success else "failed")
		publish_command_result(result_string)
		print(result_string)
	elif cmd == 1001: #disarm
		result_string = "Disarm complete"
		publish_command_result(result_string)
		print(result_string)
	else:
		print(result_string)


command_queue = CommandQueue(command_complete) #commands to execute, to make up for the command sender only handling one at a time

def query_all_zone_states():
	for i in range(len(configuration['zone_names'])):
		command_queue.enqueue({"op": 709, "args": ["1", str(i+1)]})
	#TODO: figure out command to query overall system ready status and add command to get armed state

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
	print("Connected with result code " + str(rc))
	# Subscribing in on_connect() means that if we lose the connection and
	# reconnect then subscriptions will be renewed.
	topic_root = configuration['mqtt']['topic_root']
	client.subscribe(topic_root + "command")
	client.subscribe(topic_root + "command/#")
	query_all_zone_states() #get initial system state
	
def intToHex(int):
	return f'{int:0>2X}'

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	command_topic_root = configuration['mqtt']['topic_root'] + "command"
	body = msg.payload.decode("utf-8")
	if msg.topic == command_topic_root:	
		#print(msg.topic + ": " + command)
		command_queue.enqueue(json.loads(body))
	else:
		command_topic = msg.topic[len(command_topic_root)+1:]
		if command_topic == "query":
			command_queue.enqueue({"op": 709, "args": ["1", body]})
		elif command_topic == "code":
			command_queue.enqueue({"op": 90, "args": ["Supers.db", "0"]})
		elif command_topic == "arm":
			delay = intToHex(int(body) if body else 60)
			user = intToHex(91)
			bypass = False
			bypass = intToHex(8 if bypass else 0)
			command_queue.enqueue({"op": 1000, "args": ["00 00 " + user + " 00 00 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 " + delay + " " + bypass + " 00 00 00"]})
		elif command_topic == "disarm":
			user = intToHex(91)
			command_queue.enqueue({"op": 1001, "args": ["00 00 " + user + " 00 00 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"]})


client.on_connect = on_connect
client.on_message = on_message

print('Connecting to ' + configuration['mqtt']['server_address']  + ' as ' + configuration['mqtt']['client_id'] )
client.connect(configuration['mqtt']['server_address'], 1883, 60)

client.loop_start()

# Wait for connection to set `client_id`, etc.
while not client.is_connected():
    time.sleep(0.1)

# A bus that allows us to hook into the read loop.
# If we have multiple queued of commands (such as on startup), we must wait some time between commands or subsequent commands may get a result from a previous one
# This happens because it seems that a command may receive multiple responses and we want to wait until there are no more responses likely to be received before executing the next command
# By adding a hook into the read loop, we can check for the passage of time to coordinate the execution of queued commands
#
# A method to remove listeners has been added to allow commands to remove themselves and be garbage collected when they have been completed
class MqttBus(Intellibus):
	def __init__(self, iface, run_loop_hook, **kwargs):
		super().__init__(iface, **kwargs)
		self.run_loop_hook = run_loop_hook
	
	def run(self):
		self.stop_flag = False
		while not self.stop_flag:
			self.run_loop_hook()
			pkt, synced = self.read()
			for l in self.listeners:
				try:
					l.receive(pkt, synced)
				except Exception as ex:
					print('{} threw {}'.format(l, ex))

	def remove_listener(self, listener):
		self.listeners.remove(listener)

bus = MqttBus(configuration['intellibus_port'], command_queue.tick) #, debug='tx,rx', dbgout=sys.stderr)
command_queue.bus = bus

# A simple device that only listens for announcements
class MqttDevice(VirtDevice):
	def __init__(self, ibus):
		super().__init__(ibus, 5, 3121, fromhex('00 00 FF FF FF FF'), 0, (7,1), 0x7FFE)
	
	def handle_cmd_nosync(self, cmd, arg, sync):
		if cmd == 0x802: # Event announcement
			handle_announcement(arg)
			#print(type(arg))
			#print('{:04X} ( {} )'.format(cmd, arg))

dvc = MqttDevice(bus)
bus.run()