import json
import os
import errno
import re
import warnings


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
	Save data to file. 
	NOTE: Writes as text file, not binary.
	"""
	ensure_path(fdir)
	with open(os.path.join(fdir, fname), 'w') as f:
		json.dump(data, f, indent=indent, sort_keys=True)


def load_json(fname, fdir='.'):
	"""
	Reads data from file. 
	NOTE: Reads from text file, not binary.
	"""
	with open(os.path.join(fdir, fname), 'r') as f:
		return json.load(f)


def weeks_in_season(season):
	"""
	Return a list of the week numbers for games
	played in the regular season.
	"""
	return [int(w['Number']) for w in 
				load_json('Weeks.json', fdir='data/'+str(season)+'/') if 
				int(w['SeasonType']) == 1]


def index_game_folders():
	"""
	Create a dictionary with the gameid as the
	key and the path to the containing folder as
	the value.
	"""
	game_index = {}
	for root, dirs, files in os.walk('data'):
		for f in dirs:
			try:
				gameid = int(re.search(r'game_(?P<id>\d+)', f).group('id'))
				game_index[gameid] = os.path.join(root, f)
			except AttributeError:
				pass
	dump_json(game_index, 'game_index.json', fdir='data', indent=4)


def find_game_folder(gameid):
	"""
	Find the game folder in the data directory which
	matches the given game ID.
	"""
	for root, dirs, files in os.walk('data'):
		for f in dirs:
			if f == 'game_' + str(gameid):
				return os.path.join(root, f)
	print 'Could not find game', gameid
	raw_input()


def add_boxscore_data(sdata, stype, team_box):
	"""
	Format data type for boxscore data.
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
		try:
			sdata = float(sdata)
		except ValueError:
			pass
	if stype == "Comp-Att":
		team_box["Comp"] = sdata[0]
		team_box["Att"] = sdata[1]
	else:
		team_box[stype] = sdata


def poss_to_secs(poss):
	"""
	Convert string possession time in 'mm:ss' format to float seconds.
	"""
	new_poss = re.split(':', poss)
	return 60 * float(new_poss[0]) + float(new_poss[1])


def contains_str(class_name):
	"""
	Allow contains to return only classes with whole
	string, ie. class="class_name other_class_name" will be
	found, while class="class_name_fake" will not.
	"""
	return 'contains(concat(\' \', @class, \' \'), \' ' + class_name + ' \')'


def check_game_index_exists():
	"""
	Look for game index file and creates it if it doesn't exist
	"""
	try:
		assert(os.path.isfile(os.path.join('data', 'game_index.json')))
	except AssertionError:
		index_game_folders()


def find_game_folder(response):
	"""
	Given a URL, find it's associated game folder
	"""
	check_game_index_exists()
	game_index = load_json('game_index.json', fdir='data')
	gameid = re.search(r'\?id=(?P<id>\d+)', response.url).group('id')
	return game_index[gameid], gameid


def build_teamgame_index():
	teamgame_index = {}
	for root, dirs, files in os.walk('data'):
		for f in files:
			try:
				gameid = re.match(r'gameinfo_(?P<gameid>\d+).json', f).group('gameid')
				gameinfo = load_json(os.path.join(root, f))
				try:
					teamgame_index[gameinfo['HomeTeamId']].append(gameid)
				except KeyError:
					teamgame_index[gameinfo['HomeTeamId']] = [gameid]
				try:
					teamgame_index[gameinfo['AwayTeamId']].append(gameid)
				except KeyError:
					teamgame_index[gameinfo['AwayTeamId']] = [gameid]
			except AttributeError:
				pass
	dump_json(teamgame_index, 'teamgame_index.json', fdir='data', indent=4)


def analyze_stats(ftype='boxscore', stdir='data'):
	"""
	Find how many bad scrapes there were in the entire directory
	and deletes bad scrape files if needed
	:kwarg ftype: describes the file type to analyze (boxscore or playerstats) 
	:kwarg stdir: directory to start searching through
	"""
	if ftype != 'boxscore' and ftype != 'playerstats':
		warnings.warn("ftype must be \"boxscore\" or \"playerstats\". Returning None.", UserWarning)
	ngood = 0
	nbad = 0
	errorlog = {}
	for root, dirs, files in os.walk(stdir):
		# Find gameid
		for f in files:
			try:
				gameid = re.match(r'gameinfo_(?P<gameid>\d+).json', f).group('gameid')
				break
			except AttributeError:
				pass
		# Good scrape
		fbadbox = os.path.join(root, 'bad_'+ftype+'.json')
		if os.path.isfile(os.path.join(root, 'boxscore.json')):
			ngood += 1
			# If bad_boxscore file still here when it shouldn't be, delete it
			if os.path.isfile(fbadbox):
				os.remove(fbadbox)
		# Bad scrape
		elif os.path.isfile(fbadbox):
			nbad += 1
			errorlog[gameid] = load_json(fbadbox)
	return ngood, nbad, errorlog