

def getParticipantId(gameData, puuid):
    participants = gameData[0]["participantIdentities"]
    for participant in participants:
        if participant["puuid"] == puuid:
            return participant["participantId"]


def getConvertedTeamId(gameData, participantId):
    participant = gameData[0]["participants"][participantId-1]
    teamId = participant["teamId"]
    convertedTeamId = teamId // 100 - 1  # Converts teamId from 100 or 200 to 0 or 1
    return convertedTeamId


def listDeaths(gameData, participantId):
    deaths = []
    for frame in gameData[1]["frames"]:
        for event in frame["events"]:
            if event["type"] == "CHAMPION_KILL":
                if event["victimId"] == participantId:
                    deaths.append(event.copy())
    return deaths


def listEpicMonsterKills(gameData):
    res = []
    for frame in gameData[1]["frames"]:
        for event in frame["events"]:
            if event["type"] == "ELITE_MONSTER_KILL":
                res.append(event.copy())
    return res


def listTowerKills(gameData):
    res = []
    for frame in gameData[1]["frames"]:
        for event in frame["events"]:
            if event["type"] == "BUILDING_KILL":
                res.append(event.copy())
    return res


def getLevel(gameData, participantId, timestamp):  # Returns player level at closest available timestamp before indicated timestamp
    for frame in gameData[1]["frames"]:
        framets = frame["timestamp"]
        if timestamp >= framets:
            return frame["participantFrames"][str(participantId)]["level"]


def getCoordinates(gameData, participantId, timestamp):  # Returns player coordinates at closest available timestamp before indicated timestamp
    for frame in gameData[1]["frames"]:
        framets = frame["timestamp"]
        if timestamp >= framets:
            coordinatesDict = frame["participantFrames"][str(participantId)]["position"]
            return coordinatesDict["x"], coordinatesDict["y"]


def getCS(gameData, participantId, timestamp):  # Returns (minions, jglMinions) at closest available timestamp before indicated timestamp
    for frame in gameData[1]["frames"]:
        framets = frame["timestamp"]
        if timestamp >= framets:
            participantFrame = frame["participantFrames"][str(participantId)]
            return participantFrame["minionsKilled"], participantFrame["jungleMinionsKilled"]


def getGold(gameData, participantId, timestamp):  # Returns (minions, jglMinions) at closest available timestamp before indicated timestamp
    for frame in gameData[1]["frames"]:
        framets = frame["timestamp"]
        if timestamp >= framets:
            participantFrame = frame["participantFrames"][str(participantId)]
            return participantFrame["currentGold"]


def getDeathTime(level, timestamp):
    # D'après https://leagueoflegends.fandom.com/wiki/Death#Death_timer // Pourquoi faire si compliqué ? Bonne question
    brw = [10, 10, 12, 12, 14, 16, 20, 25, 28, 32.5, 35, 37.5, 40, 42.5, 45, 47.5, 50, 52.5]
    tif = 0
    if 15*60*1000 <= timestamp < 30*60*1000:  # Entre 15 et 30 min
        tif = int(2*(timestamp/60/1000 - 15))*0.425/100
    elif 30*60*1000 <= timestamp < 45*60*1000:  # Entre 30 et 45 min
        tif = 12.75/100 + int(2*(timestamp/60/1000 - 30))*0.30/100
    elif 45*60*1000 <= timestamp < 55*60*1000:  # Entre 45 min et 55 min
        tif = 21.75/100 + int(2*(timestamp/60/1000 - 45))*1.45/100
    elif 55*60*1000 <= timestamp:  # Plus que 55 min (pensez à finir la game imo)
        tif = 50/100

    return brw[level-1] * (1+min(tif, 50/100))


def getLane(x, y):
    if (x >= 12100 or y <= 2800) and x >= 3000 and y <= 12000:
        return "bot"
    elif (x <= 2520 or y >= 12170) and x <= 12000 and y >= 3000:
        return "top"
    elif abs(x - y) <= 1800 and 2000 <= x <= 13000 and 2000 <= y <= 13000:
        return "mid"
    else:
        return "none"


def dist(x1, y1, x2, y2):
    return ((x1-x2)**2 + (y1-y2)**2)**(1/2)


def getBuff(x, y):
    if dist(x, y, 3825, 7910) <= 1000:
        return "blue0"
    elif dist(x, y, 10978, 6948) <= 1000:
        return "blue1"
    elif dist(x, y, 7740, 3937) <= 1000:
        return "red0"
    elif dist(x, y, 7156, 10837) <= 1000:
        return "red1"
    else:
        return "none"


def getFountain(x, y):
    if dist(x, y, 500, 500) <= 1000:
        return "fountain0"
    elif dist(x, y, 14300, 14300) <= 1000:
        return "fountain1"
    else:
        return "none"


def getScoreImposteur(gameData, puuid):
    score = 0

    participantId = getParticipantId(gameData, puuid)
    convertedTeamId = getConvertedTeamId(gameData, participantId)
    lostGame = gameData[0]["teams"][convertedTeamId]["Win"] == "Fail"

    if lostGame:
        score += 4
    else:
        score -= 2

    return score


def getScoreRomeo(gameData, puuid, juliettePuuid):
    score = 0

    romeoId = getParticipantId(gameData, puuid)
    romeoDeaths = listDeaths(gameData, romeoId)

    julietteId = getParticipantId(gameData, juliettePuuid)
    julietteDeaths = listDeaths(gameData, julietteId)

    deathsUnder25 = 0
    deathsUnder30 = 0
    deathsOver40 = 0
    for jDeath in julietteDeaths:  # Check for every Juliette death, if Romeo died shortly before, or when he closest died after
        jTimestamp = jDeath["timestamp"]

        # Check if Juliette died while Romeo was dead
        rLevel = getLevel(gameData, romeoId, jTimestamp)
        currentDeathTime = getDeathTime(rLevel, jTimestamp)
        diedBefore = False
        for rDeath in romeoDeaths:
            rTimestamp = rDeath["timestamp"]
            if jTimestamp - currentDeathTime <= rTimestamp <= jTimestamp:
                diedBefore = True
                break

        # Compute closest Romeo death past this Juliette death
        delta = None
        if not diedBefore:
            for rDeath in romeoDeaths:
                rTimestamp = rDeath["timestamp"]
                if rTimestamp >= jTimestamp:  # Liste ordonnée par timestamp normalement, donc ici la mort la plus early après la mort de juliette
                    delta = rTimestamp - jTimestamp
                    break

        if diedBefore:  # Roméo était déjà mort lorsque Juliette est morte
            deathsUnder25 += 1
            deathsUnder30 += 1
        elif delta is None:  # Roméo n'est pas mort entre la mort de Juliette et la fin de la partie
            deathsOver40 += 1
        else:  # Sinon delta représente la mort de Roméo la plus proche suivant celle de Juliette
            deathsUnder25 += delta <= 25*1000
            deathsUnder30 += delta <= 30*1000
            deathsOver40 += delta >= 40*1000

    jDeathCount = len(julietteDeaths)
    if deathsUnder25 == jDeathCount:
        score += 2
    if deathsUnder25/jDeathCount >= 0.8:
        score += 1
    if deathsUnder30/jDeathCount >= 0.5:
        score += 1
    if deathsOver40/jDeathCount >= 0.5:
        score -= 4

    return score


def getScoreDroide(gameData, puuid, ordres):  # Ordres = Liste des couples ("intitulé", timestamp)
    score = 0
    participantId = getParticipantId(gameData, puuid)
    convertedTeamId = getConvertedTeamId(gameData, participantId)

    completedTasks = 0
    for ordre in ordres:
        if ordre[0] == "blue":
            coords = getCoordinates(gameData, participantId, ordre[1]+5000)  # + 5000 pour être sûrs de tomber sur la frame de la bonne minute
            if getBuff(coords[0], coords[1]) == f"blue{1-convertedTeamId}":
                completedTasks += 1
        elif ordre[0] == "red":
            coords = getCoordinates(gameData, participantId, ordre[1]+5000)
            if getBuff(coords[0], coords[1]) == f"red{1-convertedTeamId}":
                completedTasks += 1
        elif ordre[0] == "gankTop":
            coords = getCoordinates(gameData, participantId, ordre[1]+5000)
            if getLane(coords[0], coords[1]) == "top":
                completedTasks += 1
        elif ordre[0] == "gankMid":
            coords = getCoordinates(gameData, participantId, ordre[1]+5000)
            if getLane(coords[0], coords[1]) == "mid":
                completedTasks += 1
        elif ordre[0] == "gankBot":
            coords = getCoordinates(gameData, participantId, ordre[1]+5000)
            if getLane(coords[0], coords[1]) == "bot":
                completedTasks += 1
        elif ordre[0] == "noCS":
            cs1 = getCS(gameData, participantId, ordre[1]+5000)[0]
            cs2 = getCS(gameData, participantId, ordre[1] + 2*60*1000 + 5000)[0]
            csGaigned = cs2 - cs1
            if csGaigned > 0:
                completedTasks += 1
        elif ordre[0] == "assistEpicMonsters":
            allTakedowns = True
            for kill in listEpicMonsterKills(gameData):
                if ordre[1] <= kill["timestamp"] <= ordre[1]+4*60*1000:
                    if participantId not in kill["assistingParticipantIds"] and kill["killerId"] != participantId:
                        allTakedowns = False
                        break
            if allTakedowns:
                completedTasks += 1
        elif ordre[0] == "assistTowers":
            allTakedowns = True
            for kill in listTowerKills(gameData):
                if ordre[1] <= kill["timestamp"] <= ordre[1] + 4 * 60 * 1000:
                    if participantId not in kill["assistingParticipantIds"] and kill["killerId"] != participantId:
                        allTakedowns = False
                        break
            if allTakedowns:
                completedTasks += 1
        elif ordre[0] == "die":
            deaths = listDeaths(gameData, participantId)
            died = False
            for death in deaths:
                if ordre[1] <= death["timestamp"] <= ordre[1] + 20 * 1000:
                    died = True
                    break
            if died:
                completedTasks += 1
        elif ordre[0] == "recall":
            coords = getCoordinates(gameData, participantId, ordre[1]+5000)
            if getFountain(coords[0], coords[1]) == f"fountain{convertedTeamId}":
                completedTasks += 1
        elif ordre[0] == "sell":
            gold1 = getGold(gameData, participantId, ordre[1] - 1*60*1000 + 5000)
            gold2 = getGold(gameData, participantId, ordre[1] + 5000)
            if gold2 - gold1 >= 1000:
                completedTasks += 1
        elif ordre[0] == "stealCamp":
            cs1 = getCS(gameData, participantId, ordre[1] - 1*60*1000 + 5000)[1]
            cs2 = getCS(gameData, participantId, ordre[1] + 5000)[1]
            csGaigned = cs2 - cs1
            if csGaigned >= 4:
                completedTasks += 1
        elif ordre[0] == "stealWave":
            cs1 = getCS(gameData, participantId, ordre[1] - 1*60*1000 + 5000)[0]
            cs2 = getCS(gameData, participantId, ordre[1] + 5000)[0]
            csGaigned = cs2 - cs1
            if csGaigned >= 6:
                completedTasks += 1

    score -= 3
    if completedTasks >= 6:
        score += 2
    if completedTasks >= 4:
        score += 2
    if completedTasks >= 2:
        score += 2

    return score
