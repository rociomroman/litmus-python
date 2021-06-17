
import time
import random
import logging
logger = logging.getLogger(__name__)
import os, sys
from kubernetes import client
import signal
import pkg.types.types as types
import pkg.events.events as events
import string
import random

# ENVDetails contains the ENV details
class ENVDetails(object):
	def __init__(self):
		self.ENV = []

	def append(self, value):
		self.ENV.append(value)
		
#WaitForDuration waits for the given time duration (in seconds)
def WaitForDuration(duration):
	time.sleep(duration)

#Atoi stands for ASCII to Integer Conversion
def atoi(string):
    res = 0

    # Iterate through all characters of
    #  input and update result
    for i in range(len(string)):
        res = res * 10 + (ord(string[i]) - ord('0'))

    return res

# RandomInterval wait for the random interval lies between lower & upper bounds
def RandomInterval(interval):
	intervals = interval.split("-")
	lowerBound = 0
	upperBound = 0

	if len(intervals) == 1:
		lowerBound = 0
		upperBound = atoi(intervals[0])
	elif len(intervals) == 2:
		lowerBound = atoi(intervals[0])
		upperBound = atoi(intervals[1])
	else:
		return print("unable to parse CHAOS_INTERVAL, provide in valid format")

	#rand.Seed(time.Now().UnixNano())
	waitTime = lowerBound + random.randint(0, upperBound-lowerBound)
	print("[Wait]: Wait for the random chaos interval {}".format(waitTime))
	WaitForDuration(waitTime)
	return None

# GetRunID generate a random
def GetRunID():
	runId = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 6))
	return str(runId)

def receive_signal(signum, stack):
    print('Received:', signum)

# AbortWatcher continuosly watch for the abort signals
# it will update chaosresult w/ failed step and create an abort event, if it recieved abort signal during chaos
def AbortWatcher(expname, resultDetails, chaosDetails, eventsDetails):
	AbortWatcherWithoutExit(expname, resultDetails, chaosDetails, eventsDetails)
	#sys.exit(0)

# class NotifySignal:
# 	kill_now = False
# 	signals = {
# 		signal.SIGINT: 'SIGINT',
# 		signal.SIGTERM: 'SIGTERM'
# 	}

# 	def __init__(self):
# 		signal.signal(signal.SIGINT, self.exit_gracefully)
# 		signal.signal(signal.SIGTERM, self.exit_gracefully)

# 	def exit_gracefully(self, signum, frame):
# 		print("\nReceived {} signal".format(self.signals[signum]))
# 		self.kill_now = True

# AbortWatcherWithoutExit continuosly watch for the abort signals
def AbortWatcherWithoutExit(expname, resultDetails, chaosDetails, eventsDetails):

	# signChan channel is used to transmit signal notifications.
	# killer = NotifySignal()
	# while not killer.kill_now:
	# 	time.sleep(1)
		#print('Press Ctrl+C')
	
	print("[Chaos]: Chaos Experiment Abortion started because of terminated signal received")
	# updating the chaosresult after stopped
	failStep = "Chaos injection stopped!"
	types.SetResultAfterCompletion(resultDetails, "Stopped", "Stopped", failStep)
	
	# generating summary event in chaosengine
	msg = expname + " experiment has been aborted"
	types.SetEngineEventAttributes(eventsDetails, types.Summary, msg, "Warning", chaosDetails)
	events.GenerateEvents(eventsDetails, chaosDetails, "ChaosEngine")

	# generating summary event in chaosresult
	types.SetResultEventAttributes(eventsDetails, types.Summary, msg, "Warning", resultDetails)
	events.GenerateEvents(eventsDetails, chaosDetails, "ChaosResult")

#GetIterations derive the iterations value from given parameters
def GetIterations(duration, interval):
	iterations = 0
	if interval != 0:
		iterations = duration / interval
	return max(iterations, 1)

# Getenv fetch the env and set the default value, if any
def Getenv(key, defaultValue):
	value = os.Getenv(key)
	if value == "":
		value = defaultValue

	return value

#Adjustment contains rule of three for calculating an integer given another integer representing a percentage
def Adjustment(a, b):
	return (a * b) / 100

#FilterBasedOnPercentage return the slice of list based on the the provided percentage
def FilterBasedOnPercentage(percentage, list):

	finalList = []
	newInstanceListLength = max(1, Adjustment(percentage, len(list)))
	#rand.Seed(time.Now().UnixNano())

	# it will generate the random instanceList
	# it starts from the random index and choose requirement no of volumeID next to that index in a circular way.
	index = random.randint(0, len(list))
	for i in range(newInstanceListLength):
		finalList = finalList.append(list[index])
		index = (index + 1) % len(list)

	return finalList

# SetEnv sets the env inside envDetails struct
def SetEnv(envDetails, key, value):
	if value != "" :
		envDetails.append(client.V1EnvVar(name=key, value=value))

# SetEnvFromDownwardAPI sets the downapi env in envDetails struct
def SetEnvFromDownwardAPI(envDetails, apiVersion, fieldPath):
	if apiVersion != "" & fieldPath != "" :
		# Getting experiment pod name from downward API
		experimentPodName = getEnvSource(apiVersion, fieldPath)
		envDetails.append(client.V1EnvVar(name="POD_NAME", value_from=experimentPodName))

# getEnvSource return the env source for the given apiVersion & fieldPath
def getEnvSource(apiVersion, fieldPath):
	downwardENV = client.V1EnvVarSource(field_ref=client.V1ObjectFieldSelector(api_version=apiVersion,field_path=fieldPath))
	return downwardENV