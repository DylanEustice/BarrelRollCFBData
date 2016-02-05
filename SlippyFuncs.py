import json
import os
import errno


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