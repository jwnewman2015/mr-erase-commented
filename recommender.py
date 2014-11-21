from __future__ import division
from math import floor
from math import pow
from math import sqrt
from steam import user
from steam import api
import json

# Read JSON from a file
def getJson(fileName):
	json_data = open(fileName)
	data = json.load(json_data)
	json_data.close()
	return data

# Write JSON to a file
def writeJson(json_data, fileName):
	with open(fileName, 'w+') as outfile:
		json.dump(json_data, outfile, indent=4)

# Gets the current file number and profile count from a data file
def getNumProfiles():
	file = open('NumProfiles.dat')
	numProfiles = int(file.read())
	file.close()
	
	return numProfiles

def printGameIDs(gameData):
	gameIDs = []
	
	for id in gameData:
		gameIDs.append(int(id))
	
	sortedGameIDs = sorted(gameIDs)
	
	writeJson(sortedGameIDs, 'gameIDs.dat')
	
def getUserData():
	numProfiles = getNumProfiles()
	numFiles = int(floor(numProfiles / 2000)) + 1
	
	profiles = dict()
	
	for i in xrange(0, numFiles):
		fileName = 'Profiles_' + str(i) + '.dat'
		fileData = getJson(fileName)
		profiles.update(fileData)
	
	return profiles

def getGameIDs():
	gameIDs = getJson('gameIDs.dat')
	
	return gameIDs
	
def getGameData():
	gameData = getJson('gameData.dat')
	
	return gameData

def getCosineMatrix():
	cosineMatrix = getJson('cosineMatrix.dat')
	
	return cosineMatrix
	
def generateCosineMatrix(gameData, profiles):
	cosineMatrix = dict()
	gameIDs = getGameIDs()
	
	for id, profile in profiles.items():
		cosineMatrix[str(id)] = dict()
		
		for game in profile['games']:
			if int(game['appid']) in gameIDs:
				appID = str(game['appid'])
				if 'average' in gameData[appID]:
					cosineMatrix[str(id)][appID] = game['playtime_forever'] / gameData[appID]['average']
				
	return cosineMatrix

def getArrayFromProfile(userID, profile, gameData):
	cosineArray = dict()
	
	gameIDs = getGameIDs()
	
	for appID, playtime in profile.items():
		if int(appID) in gameIDs:
			if 'average' in gameData[str(appID)]:
				cosineArray[str(appID)] = playtime / gameData[str(appID)]['average']
	
	return cosineArray
	
def getProfile(userID):
	errorCount = 0
	profile = dict()
	keepGoing = True
	
	while keepGoing:
		print "Getting your steam profile...\n"
		try:
			if errorCount == 10:
				print "Timeout Error 10 times, printing and quitting"
				keepGoing = False
				break
			
			# Get a user's game library
			games = api.interface("IPlayerService").GetOwnedGames(steamid = userID, include_appinfo = 1, include_played_free_games = 1)
			
			# Handle the (rare) case where user has no games
			if 'game_count' not in games["response"]:
				print "User's profile is private"
				break
			
			if games["response"]["game_count"] == 0:
				print "User has no games, continuing with next user"
				break
			
			profile = dict()
			for game in games['response']['games']:
				profile[str(game['appid'])] = game['playtime_forever']
				
			break
		
		except api.HTTPTimeoutError:
			print "HTTPTimeoutError, trying again..."
			errorCount += 1
		
		# User's profile is private
		except api.HTTPError as e:
			if str(e) == "Server connection failed: Unauthorized (401)":
				print "Profile is private, continuing with next user"
			else:
				print "Unknown Exception:", e
				keepGoing = False
			break
			
		except Exception as e:
			print "Unknown Exception:", e
			keepGoing = False
			break
	
	return profile

def vectorLength(row):
	return sqrt(sum(timePlayed**2 for timePlayed in row.values()))

def angleBetweenVector(profile1, profile2):
	dotProduct = 0
	
	for id, time in profile1.items():
		if str(id) in profile2:
			dotProduct += time * profile2[str(id)]
	
	if dotProduct > 0:
		return dotProduct / (vectorLength(profile1) * vectorLength(profile2))
	else:
		return 0

def getSimilarProfiles(userID, profile, cosineMatrix):
	similarityTuples = []
	
	for id, games in cosineMatrix.items():
		if str(id) == str(userID):
			continue
		
		angle = angleBetweenVector(profile, games)
		similarityTuples.append((str(id), angle))
	
	sortedTuples = sorted(similarityTuples, key=lambda tup: tup[1], reverse=True)
	
	return sortedTuples
	
def recommendGames(similarityScores, profile, cosineMatrix):
	games = dict()
	
	for i in range(0, 10):
		id = similarityScores[i][0]
		angle = similarityScores[i][1]
		
		for game, score in cosineMatrix[id].items():
			if game not in profile:
				if game not in games:
					games[str(game)] = angle * score
				else:
					games[str(game)] += angle * score
	
	topGames = sorted(games.items(), key=lambda tup: tup[1], reverse=True)
	
	return topGames[:10]

def printGames(topGames, gameData):
	print "Based on your user profile, we recommend you try:"
	
	for i in range(0, 10):
		print i+1, gameData[topGames[i][0]]['name']
		
	
def main():
	gameData = getGameData()
#	profiles = getUserData()
#	cosineMatrix = generateCosineMatrix(gameData, profiles)
#	writeJson(cosineMatrix, 'cosineMatrix.dat')

	cosineMatrix = getCosineMatrix()
	api.key.set("xxxx")
	userID = 76561198058997412
	
	profile = getProfile(userID)
	cosineArray = getArrayFromProfile(userID, profile, gameData)
	
	similarityScores = getSimilarProfiles(userID, profile, cosineMatrix)
	topGames = recommendGames(similarityScores, profile, cosineMatrix)
	printGames(topGames, gameData)
	
if __name__ == '__main__':
	main()
