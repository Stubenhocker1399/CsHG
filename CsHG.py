analyzeOnly = False
recording = False
wallbangsOnly = True
shutdownAfterFinish = False
debugDemoViewing = False

import ConfigParser
import io
import os
from os import listdir
from os.path import isfile, join
import subprocess
from subprocess import Popen, PIPE
import time
import win32com.client as comctl
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import sys
import json
import threading

def createConfig():
	steamid64 = raw_input("Please enter the steamid64 of the player for the timelapse: ")
	demoinfogoPath = raw_input("Please enter your demoinfogo.exe path: ")
	csgoPath = raw_input("Please enter your csgo.exe path: ")
	config = ConfigParser.SafeConfigParser()
	config.add_section('CsHGSettings')
	config.set('CsHGSettings', 'steamid64', steamid64)
	config.set('CsHGSettings', 'demoinfogo_path', demoinfogoPath)
	config.set('CsHGSettings', 'csgo_path', csgoPath)
	with open('CsHG.cfg', 'wb') as configfile:
		config.write(configfile)

def loadConfig():
	config = ConfigParser.SafeConfigParser()
	try:
		config.read('CsHG.cfg')
		steamid64 = config.get('CsHGSettings','steamid64')
		demoinfogoPath = config.get('CsHGSettings', 'demoinfogo_path')
		csgoPath = config.get('CsHGSettings', 'csgo_path')
		return steamid64, demoinfogoPath, csgoPath
	except ConfigParser.NoOptionError:
		print "Error while reading the config file. Try deleting CsHG.cfg and restarting."
		exit()

def getConfig():
	if os.path.isfile('CsHG.cfg'):
		print "Found config, loading."
	else:
		print "Found no config, creating one."
		createConfig()
	steamid64, demoinfogoPath, csgoPath = loadConfig()
	print "Config: steamid64 = " + steamid64 + " demoinfogoPath = " +  demoinfogoPath + " csgoPath: " + csgoPath
	return steamid64, demoinfogoPath, csgoPath

def analyzeDemo(demopath):
	process = Popen([demoinfogoPath[1:-1],demopath],stdout=PIPE)

	username="unknown"
	userID = -1
	totalDeaths = 0
	usernameKills = 0
	kills = []
	warmup=True;
	wasWallbang=False
	kill=False
	firstTick = 99999999
	for line in process.stdout:
		if "tick:" in line:
			lastTick= int(line[6:])
			if lastTick<firstTick:
				firstTick = lastTick
				#print "Tick: " + str(lastTick) + " FirstTick: " + str(firstTick)
		#elif "player info" in line: #not in every demo
		elif "adding:player" in line:
			for line in process.stdout:
		#		if "}" in line:
				if "filesDownloaded" in line: #lazy end of adding player info
					if lastXuid == steamid64:
						username = lastName
						userID = lastUserID
						#print "Found our player " + username + " with steamid64 " + steamid64 + "  and userID " + userID
					#print "Found player " + lastName + " with steamid64 " + lastXuid + " and userID " + lastUserID 
					break
				elif "name:" in line:
					lastName = line[6:-2]
				elif "xuid:" in line:
					lastXuid = line[6:-2]
				elif "userID:" in line:
					lastUserID = line[8:-2]
		elif "CCSUsrMsg_WarmupHasEnded" in line:
			#print "Warmup end."
			if lastUserID == -1: #our user user hasn't been found 
				break;
			warmup=False;
		elif "player_death" in line:
			for line in process.stdout:
				if "}" in line:
					if not warmup and kill and (wasWallbang or not wallbangsOnly):  #we are only interested in kills outside of warmup
						usernameKills = usernameKills + 1
						#print "Killed by " + username + " at tick " + str(lastTick)
						kills.append(lastTick)
					kill=False
					wasWallbang=False
					break
				elif "attacker: "+ username in line:
					kill=True					
				elif "penetrated: 1" in line: #penetrated: 1 for wallbangs
					wasWallbang=True
	#print "Total kills: " + str(usernameKills) 
	#print "First tick: " + str(firstTick)
	#print "Last tick: " + str(lastTick)
	return kills, firstTick

def runCSGOCommand(command, csgoPath):
	if type(command) is str:
		process = Popen([csgoPath[1:-1], "-hijack", command],stdout=PIPE)
	else:	
		command.insert(0,"-hijack")
		command.insert(0,csgoPath[1:-1])
		process = Popen(command,stdout=PIPE)	

class GameStateServer(HTTPServer):
	def init_state(self):
		CSGOGamestatePostEvent.clear()

class HandleCSGOPost(BaseHTTPRequestHandler):
	def do_POST(self):		
		length = int(self.headers['Content-Length'])
		body = self.rfile.read(length).decode('utf-8')	
		self.send_header('Content-type', 'text/html')
		self.send_response(200)
		self.end_headers()	
		jsonPost = json.loads(body)
		if 'map' in jsonPost and 'name' in jsonPost['map']:
			#print jsonPost['map']['name']
			CSGOGamestatePostEvent.set()
			CSGOGamestatePostEvent.clear()
	
	def log_message(self, format, *args):
		return
	
	def log_error(self, format, *args):
		return
	
	def finish(self):
		if not self.wfile.closed:
			self.wfile.flush()
		self.wfile.close()
		self.rfile.close()

def startGameStateServer():
	server = GameStateServer(('localhost', 3000), HandleCSGOPost)
	server.init_state()
	try:
		server.serve_forever()
	except (KeyboardInterrupt, SystemExit):
		pass	
	server.server_close()

def waitForCsgoPost(amount = 1):
	for i in range(0,amount):
		print "Wait for csgoPost " + str(i + 1) + " out of " + str(amount)
		CSGOGamestatePostEvent.wait()
		#print "Got      csgoPost"

def findProcessByName(name):
	applications = os.popen("tasklist").readlines()
	PID = -1
	for app in applications:
		if app[:9] in name:
			PID = int(app[29:34])
			break
	return PID

def checkOBS(recording):
	obsPID = findProcessByName(["obs32.exe","obs64.exe"])
	if obsPID != -1:
		print "OBSPID found: " + str(obsPID) + " Recording: " + str(recording) + " (Don't forget to setup the hotkeys: Page-Down=>Start Recording & Page-Up=>Stop Recording)"
	else:
		print "OBS not found. Recording: " + str(recording) + " Make sure you start OBS. (Don't forget to setup the hotkeys: Page-Down=>Start Recording & Page-Up=>Stop Recording)"
		recording = False  #Don't attempt to send hotkeys when OBS is not running.
	return obsPID

def shutdownPC():
	subprocess.call(["shutdown", "-f", "-s", "-t", "60"])

def demoDebug(message):
	if debugDemoViewing:
		print message

def viewDemos():
	totalKills = 0
	for demo in demofiles:
		kills, firstTick = analyzeDemo(join(demopath,demo))
		totalKills = totalKills + len(kills)
		print "totalKills: "+ str(totalKills) + " Kills = " + str(kills) + " ("+ str(demofiles.index(demo)+1) + "/" + str(len(demofiles)) + ")Demo: " + demo
		if len(kills) != 0:
		
			demoDebug("Loading demo...")
			runCSGOCommand(["+playdemo", join(demopath,demo)],csgoPath)	
			demoDebug("Waiting for 20 ticks")
			waitForCsgoPost(20)
			time.sleep(1)
			runCSGOCommand("+sv_cheats 1", csgoPath)
			runCSGOCommand("+mp_teamcashawards 0", csgoPath)
			runCSGOCommand("+mp_playercashawards 0", csgoPath)
			#todo diable afterround messages
			for kill in kills:
				if recording:
					wsh.SendKeys("{PGUP}")
				demoDebug("Kill " + str(kills.index(kill)+1) + " out of " + str(len(kills)))
				demoDebug("Pausing demo")
				runCSGOCommand("+demo_pause",csgoPath)
				time.sleep(0.1) #sleep at least more than one tick
				demoDebug("Skipping to tick " + str(kill))
				runCSGOCommand(["+demo_gototick", str(kill-firstTick-129)],csgoPath)
				#time.sleep(1)
				waitForCsgoPost()
				runCSGOCommand("+cl_draw_only_deathnotices 1", csgoPath)
				time.sleep(1)#(0.2)
				runCSGOCommand("+cl_draw_only_deathnotices 0", csgoPath)#enable and disabling hides the spectator gui
				demoDebug("Spectating player")
				runCSGOCommand(["+spec_player_by_accountid", steamid64, "+firstperson"],csgoPath)#todo find a better way
				time.sleep(1)#(0.3)
				demoDebug("Resuming demo")
				runCSGOCommand("+demo_resume",csgoPath)
				wsh.AppActivate(obsPID)
				time.sleep(1)
				if recording:
					wsh.SendKeys("{PGDN}")
				time.sleep(2)
			if recording:
					wsh.SendKeys("{PGUP}")
			demoDebug("Exiting demo...")
			runCSGOCommand("+disconnect",csgoPath)

#####################################################################################

steamid64, demoinfogoPath, csgoPath = getConfig()

#demopath = "E:\\Program Files (x86)\\Steam\\SteamApps\\common\\Counter-Strike Global Offensive - replays and screenshots\\csgo\\replays\\match730_003205395876109353290_2111552552_131.dem" #todo make configurable
#demopath = "E:\\Program Files (x86)\\Steam\\SteamApps\\common\\Counter-Strike Global Offensive - replays and screenshots\\csgo\\replays\\match730_003049383948598640776_0279539867_136.dem" #todo make configurable
demopath = "E:\\Program Files (x86)\\Steam\\SteamApps\\common\\Counter-Strike Global Offensive - replays and screenshots\\csgo\\replays\\match730_003038239255789830182_0161544285_135.dem"
#kills, firstTick = analyzeDemo(demopath)
#kills = [50422, 104205, 107647, 118102, 128610, 135671, 138697, 144274, 158406, 161902, 165446] # for faster debugging/testing


demopath = "E:\\Program Files (x86)\\Steam\\SteamApps\\common\\Counter-Strike Global Offensive - replays and screenshots\\csgo\\replays\\" #todo make configurable
demofiles = [f for f in listdir(demopath) if isfile(join(demopath, f)) and ".dem" == f[-4:]]

print len(demofiles)

CSGOGamestatePostEvent = threading.Event()
threading._start_new_thread(startGameStateServer, ())

obsPID = checkOBS(recording)
	
if not analyzeOnly:
	runCSGOCommand("+snd_musicvolume 0", csgoPath)
	runCSGOCommand("+sv_cheats 1", csgoPath)
	runCSGOCommand("+snd_setmixer Dialog vol 0", csgoPath)
	viewDemos()

if analyzeOnly:
	pass	#todo multithreaded analyze to a file for later use

threading._shutdown()
if shutdownAfterFinish:
	shutdownPC()