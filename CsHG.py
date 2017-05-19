analyzeOnly = True
numOfThreads = 4
recording = False
wallbangsOnly = False
teamkillsOnly = True
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
import win32com
import win32com.client as comctl
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import sys
import json
import threading
from threading import Lock
import Queue

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
	#usernameKills = 0
	kills = []
	wallbangs = []
	headshots = []
	teamkills = []
	warmup = True
	wasWallbang = False
	wasHeadshot = False
	wasTeamkill = False
	kill=False
	firstTick = 99999999
	for line in process.stdout:
		if "tick:" == line[:5]:
			lastTick= int(line[6:])
			if lastTick<firstTick:
				firstTick = lastTick
				#print "Tick: " + str(lastTick) + " FirstTick: " + str(firstTick)
		#elif "player info" in line: #not in every demo
		elif "adding:player" == line[:13]:
			for line in process.stdout:
		#		if "}" in line:
				if " filesDownloaded" == line[:16]: #lazy end of adding player info
					if lastXuid == steamid64:
						username = lastName
						userID = lastUserID
						#print "Found our player " + username + " with steamid64 " + steamid64 + "  and userID " + userID
					#print "Found player " + lastName + " with steamid64 " + lastXuid + " and userID " + lastUserID 
					break
				elif " name:" == line[:6]:
					lastName = line[6:-2]
				elif " xuid:" == line[:6]:
					lastXuid = line[6:-2]
				elif " userID:" in line[:8]:
					lastUserID = line[8:-2]
		elif "---- CCSUsrMsg_WarmupHasEnded" == line[:29]:
			#print "Warmup end."
			if lastUserID == -1: #our user user hasn't been found 
				break;
			warmup=False;
		elif "player_death" == line[:12]:
			killedTeam = 0
			killerTeam = 0
			for line in process.stdout:
				if "}" == line[:1]:
					if not warmup and kill:  #we are only interested in kills outside of warmup
						if wasWallbang:
							wallbangs.append(lastTick)
						if wasHeadshot:
							headshots.append(lastTick)
						if wasTeamkill:
							teamkills.append(lastTick)
						#usernameKills = usernameKills + 1
						#print "Killed by " + username + " at tick " + str(lastTick)
						kills.append(lastTick)
					kill=False
					wasWallbang = False
					wasHeadshot = False
					wasTeamkill = False
					break
				elif " attacker: "+ username == line[:len(" attacker: "+ username)]:
					kill=True
					for line in process.stdout:
						if "  team: CT" == line[:10]:
							killerTeam = 1
							break
						elif "  team: T" == line[:9]:
							killerTeam = 2
							break
					if killedTeam == killerTeam:
						wasTeamkill = True
				elif " penetrated: 1" == line[:14]: #penetrated: 1 for wallbangs
					wasWallbang=True
				elif " headshot: 1" == line[:12]:
					wasHeadshot=True
				elif " userid" == line[:7]:
					for line in process.stdout:
						if "  team: CT" == line[:10]:
							killedTeam = 1
							break
						elif "  team: T" == line[:9]:
							killedTeam = 2
							break
	#print "Total kills: " + str(usernameKills) 
	#print "First tick: " + str(firstTick)
	#print "Last tick: " + str(lastTick)
	return kills, firstTick, wallbangs, headshots, teamkills

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
		kills, firstTick, wallbangs, headshots, teamkills = analyzeDemo(join(demopath,demo))
		if teamkillsOnly:
			kills = teamkills
		if wallbangsOnly:
			kills = wallbangs
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

class demoInfo:
	demoName = "unknown";
	kills = []
	wallbangs = []
	headshots = []
	teamkills = []
	firstTick = 0
	def __init__(self, _demoname, _kills, _firstick, _wallbangs, _headshots, _teamkills):
		self.demoName = _demoname
		self.kills = _kills
		self.firstTick = _firstick
		self.wallbangs = _wallbangs
		self.headshots = _headshots
		self.teamkills = _teamkills

	def __str__(self):
		return json.dumps({self.demoName:{"firstTick": self.firstTick, "kills":self.kills, "wallbangs":self.wallbangs, "headshots":self.headshots, "teamkills":self.teamkills}}, sort_keys=True, indent=4, separators=(',', ': '))

	def __lt__(self, other):
		return self.demoName < other.demoName

def analyzeAndPrintDemo(demofiles):
	while True:
		demo = q.get()
		global totalKills
		print "("+ str(demofiles.index(demo)+1) + "/" + str(len(demofiles)) + ")Demo: " + demo+ "\n"
		kills, firstTick, wallbangs, headshots, teamkills = analyzeDemo(join(demopath,demo))
		demoinfo = demoInfo(demo, kills, firstTick, wallbangs, headshots, teamkills)
		print str(demoinfo)
		lock.acquire()
		try:	
			totalKills = totalKills + len(kills)
			demoinfos.append(demoinfo)
			print "("+ str(demofiles.index(demo)+1) + "/" + str(len(demofiles)) + ")Demo kills: " + str(len(kills)) + " totalKills: " + str(totalKills) + "\n"
		finally:
			lock.release()
		q.task_done()

class demoInfoEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, demoInfo): 
			return {"demoFile":obj.demoName,"firstTick": obj.firstTick, "kills":obj.kills}
		return json.JSONEncoder.default(self, obj)

def loadJson():
	print "loading json"
	if not os.path.isfile("CsHG.json"):
		file = open("CsHG.json", "w+")
		file.writelines(json.dumps({steamid64:{}}, sort_keys=True, indent=4, separators=(',', ': '), cls=demoInfoEncoder))
		file.close()
	with open("CsHG.json") as f:
		jsonData = json.load(f)
	return jsonData

def saveJson(demoinfosloaded, demoinfos):
	for demoinfo in demoinfos:
		demosinfosloaded[steamid64][demoinfo.demoName] = {}
		demosinfosloaded[steamid64][demoinfo.demoName]['firstTick'] = demoinfo.firstTick
		demosinfosloaded[steamid64][demoinfo.demoName]["kills"] = []
		demosinfosloaded[steamid64][demoinfo.demoName]["wallbangs"] = []
		demosinfosloaded[steamid64][demoinfo.demoName]["headshots"] = []
		for kill in demoinfo.kills:
			demosinfosloaded[steamid64][demoinfo.demoName]["kills"].append(kill)
		for wallbang in demoinfo.wallbangs:
			demosinfosloaded[steamid64][demoinfo.demoName]["wallbangs"].append(wallbang)
		for headshot in demoinfo.headshots:
			demosinfosloaded[steamid64][demoinfo.demoName]["headshots"].append(headshot)
		for teamkill in demoinfo.teamkills:
			demosinfosloaded[steamid64][demoinfo.demoName]["teamkills"].append(teamkill)
	with open("CsHG.json", "w+") as f:
		f.writelines(json.dumps(demosinfosloaded,sort_keys=True, indent=4, separators=(',', ': '), cls=demoInfoEncoder))

#####################################################################################

steamid64, demoinfogoPath, csgoPath = getConfig()

demopath = "E:\\Program Files (x86)\\Steam\\SteamApps\\common\\Counter-Strike Global Offensive - replays and screenshots\\csgo\\replays\\" #todo make configurable
#demopath = "E:\\Program Files (x86)\\Steam\\SteamApps\\common\\Counter-Strike Global Offensive\\csgo\\"  #pug_de_mirage_2017-05-06_21.dem"
demofiles = [f for f in listdir(demopath) if isfile(join(demopath, f)) and ".dem" == f[-4:]]

print len(demofiles)

CSGOGamestatePostEvent = threading.Event()
threading._start_new_thread(startGameStateServer, ())

wsh = win32com.client.Dispatch("WScript.Shell")
obsPID = checkOBS(recording)
	
if not analyzeOnly:
	runCSGOCommand("+snd_musicvolume 0", csgoPath)
	runCSGOCommand("+sv_cheats 1", csgoPath)
	runCSGOCommand("+snd_setmixer Dialog vol 0", csgoPath)
	runCSGOCommand("+engine_no_focus_sleep 0", csgoPath)
	runCSGOCommand("+snd_mute_losefocus 0", csgoPath)
	viewDemos()

if analyzeOnly:
	totalKills = 0
	demoinfos = []
	q = Queue.Queue()
	lock = Lock()
	for i in range(numOfThreads):
		t = threading._start_new_thread(analyzeAndPrintDemo, (demofiles,))
	
	demosinfosloaded = loadJson()
	
	alreadyAnalysed = []
	for key in demosinfosloaded[steamid64]:
		print key 
		#if key == steamid64:
		alreadyAnalysed.append(key)
	
	for demo in demofiles:
		if alreadyAnalysed.count(demo) == 0:
			q.put(demo)

	q.join()			
		
	saveJson(demosinfosloaded, demoinfos)

	for key, value in demosinfosloaded.items():
		print key, value

threading._shutdown()
if shutdownAfterFinish:
	shutdownPC()