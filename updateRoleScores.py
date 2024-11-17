

def getParticipantId(gameData, nameTag):
    participants = gameData[0]["participantIdentities"]
    name, tag = nameTag.lower().split("#")
    for participant in participants:
        if participant["player"]["gameName"].lower() == name.lower() and participant["player"]["tagLine"].lower() == tag.lower():
            return participant["participantId"]

    print(f"Did not find participant with name '{nameTag}' in match referenced by game data.")


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
        if timestamp-60*1000 <= framets <= timestamp:
            return frame["participantFrames"][str(participantId)]["level"]


def getCoordinates(gameData, participantId, timestamp):  # Returns player coordinates at closest available timestamp before indicated timestamp
    for frame in gameData[1]["frames"]:
        framets = frame["timestamp"]
        if timestamp-60*1000 <= framets <= timestamp:
            coordinatesDict = frame["participantFrames"][str(participantId)]["position"]
            return coordinatesDict["x"], coordinatesDict["y"]


def getCS(gameData, participantId, timestamp):  # Returns (minions, jglMinions) at closest available timestamp before indicated timestamp
    for frame in gameData[1]["frames"]:
        framets = frame["timestamp"]
        if timestamp-60*1000 <= framets <= timestamp:
            participantFrame = frame["participantFrames"][str(participantId)]
            return participantFrame["minionsKilled"], participantFrame["jungleMinionsKilled"]


def getGold(gameData, participantId, timestamp):  # Returns (minions, jglMinions) at closest available timestamp before indicated timestamp
    for frame in gameData[1]["frames"]:
        framets = frame["timestamp"]
        if timestamp-60*1000 <= framets <= timestamp:
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


def getScoreImposteur(gameData, nameTag):
    score = 0

    participantId = getParticipantId(gameData, nameTag)
    convertedTeamId = getConvertedTeamId(gameData, participantId)
    lostGame = gameData[0]["teams"][convertedTeamId]["win"] == "Fail"

    if lostGame:
        score += 4
    else:
        score -= 2

    return score


def getScoreRomeo(gameData, nameTag, julietteNameTag):
    score = 0

    romeoId = getParticipantId(gameData, nameTag)
    romeoDeaths = listDeaths(gameData, romeoId)

    julietteId = getParticipantId(gameData, julietteNameTag)
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
    if jDeathCount:  # Eviter les division par 0...
        if deathsUnder25 == jDeathCount:
            score += 2
        if deathsUnder25/jDeathCount >= 0.8:
            score += 1
        if deathsUnder30/jDeathCount >= 0.5:
            score += 1
        if deathsOver40/jDeathCount > 0.6:
            score -= 2
    else:  # Dans ce cas Juliette n'est jamais morte, donc techniquement Roméo a tous ses points.
        score += 4

    return score


def getScoreDroide(gameData, nameTag, ordres):  # Ordres = Liste des couples ("intitulé", timestamp)
    score = 0
    participantId = getParticipantId(gameData, nameTag)
    convertedTeamId = getConvertedTeamId(gameData, participantId)
    gameDuration = gameData[0]["gameDuration"]*1000  # In miliseconds

    completedTasks = 0
    for ordre in ordres:
        if ordre[1]*1000 >= gameDuration:  # If the order wasn't given/given for later than the end of the game then count it as completed
            completedTasks += 1
        elif ordre[0] == "blue":
            coords = getCoordinates(gameData, participantId, ordre[1]*1000+5000)  # + 5000 pour être sûrs de tomber sur la frame de la bonne minute
            if getBuff(coords[0], coords[1]) == f"blue{1-convertedTeamId}":
                completedTasks += 1
        elif ordre[0] == "red":
            coords = getCoordinates(gameData, participantId, ordre[1]*1000+5000)
            if getBuff(coords[0], coords[1]) == f"red{1-convertedTeamId}":
                completedTasks += 1
        elif ordre[0] == "gankTop":
            coords = getCoordinates(gameData, participantId, ordre[1]*1000+5000)
            if getLane(coords[0], coords[1]) == "top":
                completedTasks += 1
        elif ordre[0] == "gankMid":
            coords = getCoordinates(gameData, participantId, ordre[1]*1000+5000)
            if getLane(coords[0], coords[1]) == "mid":
                completedTasks += 1
        elif ordre[0] == "gankBot":
            coords = getCoordinates(gameData, participantId, ordre[1]*1000+5000)
            if getLane(coords[0], coords[1]) == "bot":
                completedTasks += 1
        elif ordre[0] == "noCS":
            cs1 = getCS(gameData, participantId, ordre[1]*1000+5000)[0]
            cs2 = getCS(gameData, participantId, ordre[1]*1000 + 2*60*1000 + 5000)[0]
            csGaigned = cs2 - cs1
            if csGaigned == 0:
                completedTasks += 1
        elif ordre[0] == "assistEpicMonsters":
            allTakedowns = True
            for kill in listEpicMonsterKills(gameData):
                if ordre[1]*1000 <= kill["timestamp"] <= ordre[1]*1000+4*60*1000:
                    if participantId not in kill["assistingParticipantIds"] and kill["killerId"] != participantId:
                        allTakedowns = False
                        break
            if allTakedowns:
                completedTasks += 1
        elif ordre[0] == "assistTowers":
            allTakedowns = True
            for kill in listTowerKills(gameData):
                if ordre[1]*1000 <= kill["timestamp"] <= ordre[1]*1000 + 4 * 60 * 1000:
                    if participantId not in kill["assistingParticipantIds"] and kill["killerId"] != participantId:
                        allTakedowns = False
                        break
            if allTakedowns:
                completedTasks += 1
        elif ordre[0] == "die":
            deaths = listDeaths(gameData, participantId)
            died = False
            for death in deaths:
                if ordre[1]*1000 - 20*1000 <= death["timestamp"] <= ordre[1]*1000:
                    died = True
                    break
            if died:
                completedTasks += 1
        elif ordre[0] == "recall":
            coords = getCoordinates(gameData, participantId, ordre[1]*1000+5000)
            if getFountain(coords[0], coords[1]) == f"fountain{convertedTeamId}":
                completedTasks += 1
        elif ordre[0] == "sell":
            gold1 = getGold(gameData, participantId, ordre[1]*1000 - 1*60*1000 + 5000)
            gold2 = getGold(gameData, participantId, ordre[1]*1000 + 5000)
            if gold2 - gold1 >= 1000:
                completedTasks += 1
        elif ordre[0] == "stealCamp":
            cs1 = getCS(gameData, participantId, ordre[1]*1000 - 1*60*1000 + 5000)[1]
            cs2 = getCS(gameData, participantId, ordre[1]*1000 + 5000)[1]
            csGaigned = cs2 - cs1
            if csGaigned >= 4:
                completedTasks += 1
        elif ordre[0] == "stealWave":
            cs1 = getCS(gameData, participantId, ordre[1]*1000 - 1*60*1000 + 5000)[0]
            cs2 = getCS(gameData, participantId, ordre[1]*1000 + 5000)[0]
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


def getScoreSerpentin(gameData, nameTag):
    score = 0

    participantId = getParticipantId(gameData, nameTag)
    convertedTeamId = getConvertedTeamId(gameData, participantId)

    wonGame = gameData[0]["teams"][convertedTeamId]["win"] == "Win"

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

    score -= 2
    if impVotes >= 1:
        score += 1
    if impVotes >= 2:
        score += 1
    if impVotes >= 3:
        score += 2

    return score


def getScoreSuperHeros(gameData, nameTag):
    score = 0

    participantId = getParticipantId(gameData, nameTag)
    convertedTeamId = getConvertedTeamId(gameData, participantId)

    wonGame = gameData[0]["teams"][convertedTeamId]["win"] == "Win"

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
    if wonGame:
        score += 2
    if hasTeamMostAssists and hasTeamMostKills:
        score += 2
    if hasTeamMostAssists or hasTeamMostKills:
        score += 2

    return score


def getScoreAnalyste(gameData, nameTag, order):  # order sous forme de string ici : par exemple "dak"
    score = 0

    participantId = getParticipantId(gameData, nameTag)
    kdad = getKDAD(gameData, participantId)

    orderL = []  # Order sous forme de liste, par ex : [1, 2, 0]
    for letter in order:
        if letter == "k":
            orderL.append(0)
        elif letter == "d":
            orderL.append(1)
        else:
            orderL.append(2)

    marge = kdad[orderL[0]] + 2 < kdad[orderL[1]] + 1 < kdad[orderL[2]]
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


def getScoreReglo(gameData, nameTag, side):
    score = 0

    participantId = getParticipantId(gameData, nameTag)

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
    if (deltaMax <= 5*60*1000 and not side) or (deltaMax <= 4*60*1000 and side):
        score += 2
    if (deltaMax <= 7*60*1000 and not side) or (deltaMax <= 6*60*1000 and side):
        score += 2

    return score


def getScoreRadin(gameData, nameTag):
    score = 0

    participantId = getParticipantId(gameData, nameTag)

    maxGold = 0
    for frame in gameData[1]["frames"]:
        currentGold = frame["participantFrames"][str(participantId)]["currentGold"]
        maxGold = max(maxGold, currentGold)

    if maxGold <= 1205:
        score += 1
    if maxGold <= 1305:
        score += 1
    if maxGold <= 1500:
        score += 1
    if maxGold > 2000:
        score -= 3

    return score


def getScorePhilosophe(gameData, nameTag):
    score = 0

    participantId = getParticipantId(gameData, nameTag)
    convertedTeamId = getConvertedTeamId(gameData, participantId)

    wonGame = gameData[0]["teams"][convertedTeamId]["win"] == "Win"
    gameDuration = gameData[0]["gameDuration"] // 60  # En minutes

    score -= 4
    if wonGame:
        score += 1
    score += max(0, int((gameDuration - 15)/5))  # càd 0 point à 15 min, 1 point à 20 min, ..., 3 points à 30 min, 4 points à 35, etc.

    return score


def getScoreGambler(gameData, enemyNameTags, guesses):
    score = 0

    enemyPositions = []
    for nameTag in enemyNameTags:
        participantId = getParticipantId(gameData, nameTag)
        timeline = gameData[0]["participants"][participantId-1]["timeline"]
        lane = timeline["lane"]
        role = timeline["role"]

        position = None
        if lane == "TOP":
            position = 0
        elif lane == "JUNGLE":
            position = 1
        elif lane == "MIDDLE":
            position = 2
        elif lane == "BOTTOM" and role == "CARRY":
            position = 3
        elif lane == "BOTTOM" and role == "SUPPORT":
            position = 4

        enemyPositions.append(position)

    correctGuesses = 0
    for i in range(len(guesses)):  # Itération sur les rôles : i = 0 -> top ... i = 4 -> sup
        if enemyPositions[int(guesses[i])-1] == i:  # Pourquoi c'était si compliqué ET CA MARCHE TOUJOURS PAAAAAA
            correctGuesses += 1

    if correctGuesses == 5:
        score += 2
    if correctGuesses <= 2:
        score -= 3

    return score
