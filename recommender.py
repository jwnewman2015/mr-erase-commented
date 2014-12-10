from __future__ import division
from math import floor
from math import sqrt
from steam import api
import json

path = '/home/jwnewman/mr_erase_commented/recommender/'

gameDataPath = 'gameData.dat'
gameIDsPath = 'gameIDs.dat'
cosineMatrixPath1 = 'cosineMatrix1.dat'
cosineMatrixPath2 = 'cosineMatrix2.dat'

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

	writeJson(sortedGameIDs, gameIDsPath)

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
	gameIDs = getJson(gameIDsPath)

	return gameIDs

def getGameData():
	gameData = getJson(gameDataPath)

	return gameData

def getCosineMatrix():
	cosineMatrix = getJson(cosineMatrixPath1)
	cosineMatrix2 = getJson(cosineMatrixPath2)

	cosineMatrix.update(cosineMatrix2)

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

	for game in profile:
		appID = game['appid']
		if int(appID) in gameIDs:
			if 'average' in gameData[str(appID)]:
				cosineArray[str(appID)] = game['playtime_forever'] / gameData[str(appID)]['average']

	return cosineArray

def updateGameData(userGames):
	gameData = getGameData()

	for game in userGames:
		appid = str(game['appid'])
		if appid not in gameData:
			gameData[appid] = dict()
			gameData[appid]['owners'] = 1
			gameData[appid]['hours'] = game['playtime_forever']
			gameData[appid]['average'] = game['playtime_forever']

		gameData[appid]['name'] = game['name']
		gameData[appid]['img_icon_url'] = game['img_icon_url']
		gameData[appid]['img_logo_url'] = game['img_logo_url']

	writeJson(gameData, gameDataPath)

def getProfile(userID):
	errorCount = 0
	profile = []
	keepGoing = True

	while keepGoing:
		try:
			if errorCount == 10:
				return -4, "API timed out 10 times, could not get profile"
				keepGoing = False
				break

			# Get a user's game library
			games = api.interface("IPlayerService").GetOwnedGames(steamid = userID, include_appinfo = 1, include_played_free_games = 1)

			# Handle the (rare) case where user has no games
			if 'game_count' not in games["response"]:
				return -2, "Your profile is private!"
				break

			if games["response"]["game_count"] == 0:
				return -1, "You don't own any games!"
				break

			for game in games['response']['games']:
				appid = str(game['appid'])
				data = game
				data['appid'] = appid
				profile.append(data)

			break

		except api.HTTPTimeoutError:
			errorCount += 1

		# User's profile is private
		except api.HTTPError as e:
			if str(e) == "Server connection failed: Unauthorized (401)":
				return -2, "Your profile is private!"
			else:
				return -3, e
			break

		except Exception as e:
			return -3, e
			break

	updateGameData(games['response']['games'])

	return 0, profile

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

def getSimilarProfiles(userID, cosineArray, cosineMatrix):
	similarityTuples = []

	for id, games in cosineMatrix.items():
		if str(id) == str(userID):
			continue

		angle = angleBetweenVector(cosineArray, games)
		similarityTuples.append((str(id), angle))

	sortedTuples = sorted(similarityTuples, key=lambda tup: tup[1], reverse=True)

	return sortedTuples

def recommendGames(similarityScores, cosineArray, cosineMatrix):
	games = dict()

	for i in range(0, 30):
		id = similarityScores[i][0]
		angle = similarityScores[i][1]

		for game, score in cosineMatrix[id].items():
			if game not in cosineArray:
				if game not in games:
					games[str(game)] = angle * score
				else:
					games[str(game)] += angle * score

	topGames = sorted(games.items(), key=lambda tup: tup[1], reverse=True)

	return topGames[:20]

#def printGames(topGames, gameData):
#	print "Based on your user profile, we recommend you try:"
#
#	for i in range(0, 20):
#		print i+1, gameData[topGames[i][0]]['name']

def topGameData(topGames, gameData):
	topList = []

	for appid, score in topGames:
		data = gameData[appid]
		data['appid'] = appid

		topList.append(data)

	return topList

def getIDFromUsername(username):
	api.key.set("A946F35FD4CD2C8F3896F7970B4A6DCF")

	response = api.interface("ISteamUser").ResolveVanityUrl(vanityurl = username)

	if response['response']['success'] == 42:
		return 42;
	else:
		return response['response']['steamid']

def getTopGames(userID, profile):
	api.key.set("A946F35FD4CD2C8F3896F7970B4A6DCF")

	cosineMatrix = getCosineMatrix()

	gameData = getGameData()

	cosineArray = getArrayFromProfile(userID, profile, gameData)
	similarityScores = getSimilarProfiles(userID, cosineArray, cosineMatrix)
	topGames = recommendGames(similarityScores, cosineArray, cosineMatrix)
	info = topGameData(topGames, gameData)


#	print topGames
#	printGames(topGames, gameData)
#	print info

	return info
#	printGames(topGames, gameData)



def main():
#	gameData = getGameData()

	response = getIDFromUsername("TeriosShadow")
	id, profile = getProfile(response)
	getTopGames(response, profile)
#	print response

#	profiles = getUserData()
#	cosineMatrix = generateCosineMatrix(gameData, profiles)
#	writeJson(cosineMatrix, cosineMatrixPath)

#	cosineMatrix = getCosineMatrix()
#	api.key.set("A946F35FD4CD2C8F3896F7970B4A6DCF")
#	userID = 76561198058997412

#	profile = getProfile(userID)
#	cosineArray = getArrayFromProfile(userID, profile, gameData)

#	similarityScores = getSimilarProfiles(userID, profile, cosineMatrix)
#	topGames = recommendGames(similarityScores, profile, cosineMatrix)
#	printGames(topGames, gameData)

if __name__ == '__main__':
	main()