import ConfigParser
import io
import os.path
from subprocess import Popen, PIPE

def createConfig():
	steamid64 = raw_input("Please enter the steamid64 of the player for the timelapse: ")
	demoinfogo_Path = raw_input("Please enter your demoinfogo.exe path: ")
	config = ConfigParser.SafeConfigParser()
	config.add_section('CsHGSettings')
	config.set('CsHGSettings', 'steamid64', steamid64)
	config.set('CsHGSettings', 'demoinfogo_Path', demoinfogo_Path)

	with open('CsHG.cfg', 'wb') as configfile:
		config.write(configfile)

def loadConfig():
	config = ConfigParser.SafeConfigParser()
	try:
		config.read('CsHG.cfg')
		steamid64 = config.get('CsHGSettings','steamid64')
		demoinfogoPath = config.get('CsHGSettings', 'demoinfogo_Path')
		return steamid64, demoinfogoPath
	except ConfigParser.NoOptionError:
		print "Error while reading the config file. Try deleting CsHG.cfg and restarting."
		exit()

if os.path.isfile('CsHG.cfg'):
	print "Found config, loading."
else:
	print "Found no config, creating one."
	createConfig()

steamid64, demoinfogoPath = loadConfig()
print "steamid64 = " + steamid64 + "; demoinfogoPath = " +  demoinfogoPath;

demopath = "E:\\Program Files (x86)\\Steam\\SteamApps\\common\\Counter-Strike Global Offensive - replays and screenshots\\csgo\\replays\\match730_003205395876109353290_2111552552_131.dem"
process = Popen([demoinfogoPath[1:-1],demopath],stdout=PIPE)

username="unknown"
userID = 0
totalDeaths = 0
usernameKills = 0
for line in process.stdout:
	if "tick:" in line:
		lastTick= int(line[6:])
	if "player info" in line:
		for line in process.stdout:
			if "}" in line:
				if lastXuid == steamid64:
					username = lastName
					userID = lastUserID
					print "Found our player " + username + " with steamid64 " + steamid64 + "  and userID " + userID
				#print "Found player " + lastName + " with steamid64 " + lastXuid + " and userID " + lastUserID 
				break
			if "name:" in line:
				lastName = line[6:-2]
			if "xuid:" in line:
				lastXuid = line[6:-2]
			if "userID:" in line:
				lastUserID = line[8:-2]

	if "player_death" in line:
		for line in process.stdout:
			if "}" in line:
				break
			if "attacker: "+ username in line:
				usernameKills = usernameKills + 1
				print "Killed by " + username + " at tick " + str(lastTick)
print "Total kills: " + str(usernameKills) 
print "Last tick: " + str(lastTick)