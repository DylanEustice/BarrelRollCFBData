import json
import os
import errno
import re


def ensure_path(path):
	"""
	Make sure os path exists, create it if not
	"""
	try:
		os.makedirs(path)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise


def dump_json(data, fname, fdir='.', indent=None):
	"""
	Saves data to file. 
	NOTE: Writes as text file, not binary.
	"""
	ensure_path(fdir)
	with open(os.path.join(fdir, fname), 'w') as f:
		json.dump(data, f, indent=indent)


def load_json(fname, fdir='.'):
	"""
	Reads data from file. 
	NOTE: Reads from text file, not binary.
	"""
	with open(os.path.join(fdir, fname), 'r') as f:
		return json.load(f)


def weeks_in_season(season):
	"""
	Returns a list of the week numbers for games
	played in the regular season.
	"""
	return [int(w['Number']) for w in 
				load_json('Weeks.txt', fdir='data/'+str(season)+'/') if 
				int(w['SeasonType']) == 1]


def index_game_folders():
	"""
	Creates a dictionary with the gameid as the
	key and the path to the containing folder as
	the value.
	"""
	game_index = dict()
	for root, dirs, files in os.walk('.\\data'):
		for f in dirs:
			try:
				gameid = int(re.search(r'game_(?P<id>\d+)', f).group('id'))
				game_index[gameid] = os.path.join(root, f)
			except AttributeError:
				pass
	dump_json(game_index, 'game_index.txt', fdir='data', indent=4)


def find_game_folder(gameid):
	"""
	Finds the game folder in the data directory which
	matches the given game ID.
	"""
	for root, dirs, files in os.walk('.\\data'):
		for f in dirs:
			if f == 'game_' + str(gameid):
				return os.path.join(root, f)
	print 'Could not find game', gameid
	raw_input()


def add_boxscore_data(sdata, stype, team_box):
	"""
	Formats data type for boxscore data.
	"""
	stype = str(stype)
	# Convert certain stat types
	if ((stype == "Passing" or stype == "Rushing" or stype == "Penalties") and 
		"1st Down " + stype not in team_box):
		stype = "1st Down " + stype
	elif stype == "Average":
		stype = "Yards per Rush"
	elif stype == "Attempts":
		stype = "Rushing Attempts"
	# Convert data types
	if stype == "3rd Down Conv" or stype == "4th Down Conv":
		try:
			sdata = 0.01 * float(re.sub('%', '', sdata))
		except ValueError:
			sdata = 0.0
	elif stype == "Comp-Att":
		sdata = [float(x) for x in re.split('-', sdata)]
	elif stype == "Possession":
		sdata = poss_to_secs(sdata)
	else:
		sdata = float(sdata)
	team_box[stype] = sdata


def poss_to_secs(poss):
	"""
	Converts string possession time in 'mm:ss' format to float seconds.
	"""
	new_poss = re.split(':', poss)
	return 60 * float(new_poss[0]) + float(new_poss[1])