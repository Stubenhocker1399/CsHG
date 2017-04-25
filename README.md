<h1><b>Cs</b>go<b>H</b>ighlight<b>G</b>enerator</h1>
<h2>A program for creating kill-videos/timelapses out of csgo demos</h2>

Using a collection of demos, this python2.7 program scans through each demo with [csgo-demoinfo](https://github.com/ValveSoftware/csgo-demoinfo) and gets all the kills of one player, which are then recorded into small clips using [OBS Studio](https://github.com/jp9000/obs-studio) and CSGO's [Game State Intregation](https://developer.valvesoftware.com/wiki/Counter-Strike:_Global_Offensive_Game_State_Integration).


## Requirements
* [Counter Strike: Global Offensive](https://store.steampowered.com/app/730/)
* [csgo-demoinfo](https://github.com/ValveSoftware/csgo-demoinfo)
* [OBS Studio](https://github.com/jp9000/obs-studio)
* [pypiwin32](https://pypi.python.org/pypi/pypiwin32)


## Installation
* Clone this repository
* Compile csgo-demoinfo to get its executable
* If not already installed, run ```pip install pypiwin32``` to install pypiwin32
* Install OBS Studo and Counter Strike: Global Offensive
* Set-up OBS Studio's hotkeys so that Page-Down->Start Recording & Page-Up->Stop Recording
* Copy [gamestate_integration_CsHG.cfg](csgo/cfg/gamestate_integration_CsHG.cfg) to CSGO's config folder. (csgo/cfg/)
* Edit the CsHG.py top configuration settings to match what you want to do
* Run CSGO in windowed mode
* Run CsHG.bat, enter the configuration questions.
* ???
* Profit


## Example Video

<a href="http://www.youtube.com/watch?feature=player_embedded&v=emTGJn8Ojs0
" target="_blank"><img src="http://img.youtube.com/vi/emTGJn8Ojs0/0.jpg" 
alt="ExampleTimelapseVideo" width="240" height="180" border="10" /></a>
