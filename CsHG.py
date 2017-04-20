import ConfigParser
import io
import os.path

def createConfig():
	username = raw_input("Please enter the username for the timelapse: ")
	demoinfogo_Path = raw_input("Please enter your demoinfogo.exe path: ")
	config = ConfigParser.SafeConfigParser()
	config.add_section('CsHGSettings')
	config.set('CsHGSettings', 'username', username)
	config.set('CsHGSettings', 'demoinfogo_Path', demoinfogo_Path)

	with open('CsHG.cfg', 'wb') as configfile:
		config.write(configfile)

def loadConfig():
	config = ConfigParser.SafeConfigParser()
	config.read('CsHG.cfg')
	username = config.get('CsHGSettings','username')
	demoinfogoPath = config.get('CsHGSettings', 'demoinfogo_Path')
	return username, demoinfogoPath

if os.path.isfile('CsHG.cfg'):
	print "Found config, loading."
else:
	print "Found no config, creating one."
	createConfig()

username, demoinfogoPath = loadConfig()
print "Username = " + username + "; demoinfogoPath = " +  demoinfogoPath;