import time
import mqtt_command as cmd_sender

class CommandQueue:
	def __init__(self, command_complete_callback):
		self.queue = []
		self.running_command = None
		self.last_command_completion_time = 0
		self.command_interval = 1
		self.command_complete_callback = command_complete_callback
		self.bus = None
	
	def enqueue(self, command):
		if command:
			self.queue.append(command)

	def tick(self):
		if self.running_command is None and len(self.queue) > 0 and self.__enoughTimeHasPassed():
			self.__execute_now(self.queue.pop(0))

	def __execute_now(self, command):
		if command.get('op', None) is not None:
			self.running_command = cmd_sender.send_command(self.bus, command["op"], command.get("args", []), self.__on_complete(command))

	def __on_complete(self, command):
		def execute_callback(result):
			self.command_complete_callback(command["op"], command["args"], result)
			self.running_command = None
			self.last_command_completion_time = time.time()
		return execute_callback

	def __enoughTimeHasPassed(self) -> bool:
		t = time.time()
		delta = t - self.last_command_completion_time
		return delta >= self.command_interval