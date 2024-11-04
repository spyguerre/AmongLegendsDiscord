from websockets.asyncio.client import connect


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


def listKills(gameData, participantId):
    kills = []
    for frame in gameData[1]["frames"]:
        for event in frame["events"]:
            if event["type"] == "CHAMPION_KILL":
                if event["killerId"] == participantId:
                    kills.append(event.copy())
    return kills


def listAssists(gameData, participantId):
    assists = []
    for frame in gameData[1]["frames"]:
        for event in frame["events"]:
            if event["type"] == "CHAMPION_KILL":
                if participantId in event["assistingParticipantIds"]:
                    assists.append(event.copy())
    return assists


def listTakedowns(gameData, participantId):
    takedowns = []
    for frame in gameData[1]["frames"]:
        for event in frame["events"]:
            if event["type"] == "CHAMPION_KILL":
                if participantId in event["assistingParticipantIds"] or participantId == event["killerId"]:
                    takedowns.append(event.copy())
    return takedowns


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


def getKDAD(gameData, participantId):  # Returns Kills, Deaths, Assists, and total Damage to champions
    participantStats = gameData[0]["participants"][participantId-1]["stats"]
    return participantStats["kills"], participantStats["deaths"], participantStats["assists"], participantStats["totalDamageDealtToChampions"]


def getTeamKDAD(gameData, convertedteamId):
    participants = gameData[0]["participants"]
    teamKDA = []
    for participant in participants:
        if participant["teamId"] == (convertedteamId+1)*100:
            teamKDA.append(getKDAD(gameData, participant["participantId"]))
    return teamKDA


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
    gameDuration = gameData[0]["gameDuration"]*1000  # In miliseconds

    completedTasks = 0
    for ordre in ordres:
        if ordre[1] >= gameDuration:  # If the order wasn't given/given for later than the end of the game then count it as completed
            completedTasks += 1
        elif ordre[0] == "blue":
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


def getScoreSerpentin(gameData, puuid):
    score = 0

    participantId = getParticipantId(gameData, puuid)
    convertedTeamId = getConvertedTeamId(gameData, participantId)

    wonGame = gameData[0]["teams"][convertedTeamId]["Win"] == "Win"

    teamKDAD = getTeamKDAD(gameData, convertedTeamId)
    teamMostDeaths = 0
    for participantKDAD in teamKDAD:
        teamMostDeaths = max(teamMostDeaths, participantKDAD[1])
    hasTeamMostDeaths = teamMostDeaths == getKDAD(gameData, participantId)[1]

    teamMostDamage = 0
    for participantKDAD in teamKDAD:
        teamMostDamage = max(teamMostDamage, participantKDAD[3])
    hasTeamMostDamage = teamMostDamage == getKDAD(gameData, participantId)[3]

    score -= 3
    if wonGame:
        score += 2
    if hasTeamMostDeaths:
        score += 2
    if hasTeamMostDamage:
        score += 2

    return score


def getScoreEscroc(guessTab, teamId, playerIndex):
    score = 0

    impVotes = 0
    for playeri in guessTab[teamId]:
        if playeri[playerIndex] == "imposteur":
            impVotes += 1

    score -= 1
    if impVotes >= 1:
        score += 1
    if impVotes >= 2:
        score += 1
    if impVotes >= 3:
        score += 2

    return score


def getScoreSuperHeros(gameData, puuid):
    score = 0

    participantId = getParticipantId(gameData, puuid)
    convertedTeamId = getConvertedTeamId(gameData, participantId)

    teamKDAD = getTeamKDAD(gameData, convertedTeamId)
    teamMostKills = 0
    for participantKDAD in teamKDAD:
        teamMostKills = max(teamMostKills, participantKDAD[0])
    hasTeamMostKills = teamMostKills == getKDAD(gameData, participantId)[0]

    teamMostAssists = 0
    for participantKDAD in teamKDAD:
        teamMostAssists = max(teamMostAssists, participantKDAD[2])
    hasTeamMostAssists = teamMostAssists == getKDAD(gameData, participantId)[2]

    score -= 2
    if hasTeamMostAssists:
        score += 2
    if hasTeamMostKills:
        score += 2
    if hasTeamMostAssists and hasTeamMostKills:
        score += 2

    return score


def getScoreAnalyste(gameData, puuid, order):  # order sous forme de string ici : par exemple "dak"
    score = 0

    participantId = getParticipantId(gameData, puuid)
    kdad = getKDAD(gameData, participantId)

    orderL = []  # Order sous forme de liste, par ex : [1, 2, 0]
    for letter in order:
        if letter == "k":
            orderL.append(0)
        elif letter == "d":
            orderL.append(1)
        else:
            orderL.append(2)

    marge = kdad[order[0]] + 2 < kdad[order[1]] + 1 < kdad[order[2]]
    inegalitesLarges = kdad[orderL[0]] <= kdad[orderL[1]] <= kdad[orderL[2]]
    uneInegaliteStricte = (kdad[orderL[0]] < kdad[orderL[1]]) or (kdad[orderL[1]] < kdad[orderL[2]])

    score -= 3
    if marge:
        score += 2
    if inegalitesLarges:
        score += 2
    if uneInegaliteStricte:
        score += 2

    return score


def getScoreReglo(gameData, puuid, side):
    score = 0

    participantId = getParticipantId(gameData, puuid)

    if not side:  # Mourir
        deaths = listDeaths(gameData, participantId)
        deathCount = len(deaths)
        deltaMax = 0
        firstBefore8 = False
        if deathCount:  # Si pas de mort ou 1 max, le delta reste à 0. Si pas de morts, pas de récompense pour <= 8 min.
            if deaths[0]["timestamp"] <= 8 * 60 * 1000:
                firstBefore8 = True
            for i in range(len(deaths) - 1):
                deltaMax = max(deltaMax, deaths[i+1]["timestamp"] - deaths[i]["timestamp"])

    else:  # Obtenir un takedown
        takedowns = listTakedowns(gameData, participantId)
        takedownCount = len(takedowns)
        deltaMax = 0
        firstBefore8 = False
        if takedownCount:
            if takedowns[0]["timestamp"] <= 8 * 60 * 1000:
                firstBefore8 = True
            for i in range(len(takedowns) - 1):
                deltaMax = max(deltaMax, takedowns[i+1]["timestamp"] - takedowns[i]["timestamp"])

    score -= 3
    if firstBefore8:
        score += 2
    if deltaMax <= 5*60*1000:
        score += 2
    if deltaMax <= 7*60*1000:
        score += 2

    return score
