import discord
from discord.ext import commands
import datetime
import sqlite3
import requests
from pandas import json_normalize
from lcuapi import LCU  # From https://github.com/jjmaldonis/lcu-api/tree/master !
from lcuapi.exceptions import LCUClosedError, LCUDisconnectedError
import random
import asyncio
from prettytable import PrettyTable
from updateRoleScores import *


# Creating the bot
intents = discord.Intents.default()
# noinspection PyUnresolvedReferences
intents.members = True
bot = commands.Bot(intents=intents)


# Connecting to db
con = sqlite3.connect("sus.db")
cursor = con.cursor()


# Connect to league client api
lcu = LCU()
lcu.wait_for_client_to_open()
lcu.wait_for_login()


# Global variables
key = open("riotKey.txt").read()  # Define Riot API Key
gameData = {}  # save game data here
# game = lcu.get("/lol-match-history/v1/games/__________")  # En cas de bug en partie
# gameTimeline = lcu.get(f"/lol-match-history/v1/game-timelines/{game['gameId']}")
# gameData = [game, gameTimeline]


# Converts an api response to a readable dict
def ansToDict(ans):
    return json_normalize(ans.json()).to_dict()


def createTeamsEmbed():
    embed = discord.Embed(
        title=f"Partie actuelle",
        color=discord.Colour.blurple(),
    )
    for i in [0, 1]:  # Ajoute les deux teams à l'embed
        cursor.execute("SELECT * FROM game WHERE teamId = ?", (i,))
        res = cursor.fetchall()
        embed.add_field(
            name=f"**Team de {'gauche' if i == 0 else 'droite'}**",
            value="\n".join([f"<@!{player[0]}>" for player in res]) if res else "Vide"
        )

    return embed


def listRoles():
    # L'imposteur doit être présent dans chaque team et est donc défini à part de la liste qui suit.
    roles = {
        "Roméo": (
            "Tu es amoureux.se de %joueur de l'équipe adverse et dois mourir dès que cette personne meurt.",
            [0, 1, 2, 3, 4]
        ),
        "droïde": (
            "Je te donnerai des ordres à exécuter au fil de la partie... garde tes mp à portée de main :p\nIndique-moi ta position avant le début de la partie avec `/position <pos>` pour que je puisse un minimum custom tes ordres >:)",
            []
        ),
        "serpentin": (
            "Tu dois gagner la game en ayant le plus de morts de ta team et le plus de dégâts !",
            []
        ),
        "escroc": (
            "Ton seul but est de te faire voter imposteur le plus possible en fin de partie.",
            []
        ),
        "super-héros": (
            "Tu dois gagner la partie en ayant le plus de kills ou d'assists... ou les deux ;)",
            []
        ),
        "analyste": (
            "Ton kda doit respecter l'odre croissant suivant en fin de partie : %order",
            ["kda", "kad", "dka", "dak", "akd", "adk"]
        ),
        "réglo": (
            "Dès que tu %which1 pour la première fois (de préférence avant 8 min), tu dois %which2 toutes les 5 minutes au plus jusqu'à la fin de la partie.",
            [0, 1]
        ),
        "radin": (
            "Tu ne gardes jamais plus de 1200 gold sur toi. Juste au cas où.",
            []
        ),
        "philosophe": (
            "Tu aimes bien prendre ton temps dans la vie. Mourir peut attendre, gagner aussi. Tu feras donc durer la partie autant que possible. Mais c'est mieux de gagner quand même.",
            []
        ),
    }
    """ "gambler": (
            "Tu parie les positions des joueurs adverses pendant l'écran de chargement grâce à `/gamble <top> <jgl> <mid> <adc> <sup>`, en remplissant les rôles avec les numéros correspondants aux joueurs ci-dessous.\nTu obtiens aussi des points bonus pour les bons guess de rôles en fin de partie !",
            []
        )
    }"""

    return roles


def listDroidOrders():
    orders = {  # Orders can be given 4 minutes in or later
        "blue": {  # order id
            "description": "Invade le blue ennemi à %timestamp.",  # Description
            "integerTimestamp": True,  # Whether or not timestamp for this order should be integer minutes
            "preferedPositions": [  # Positions this order can be given to before 14 min
                ["jgl", None],  # [position, teamId] / None for any
                ["mid", None],
                ["top", 1],
                ["adc", 0],
                ["sup", 0]
            ],
            "timeToExecute": 30,  # In seconds, time before timestamp to send the order
            "minimumBreakTime": 0  # In seconds, how much minimum time to wait before giving next task
        },
        "red": {
            "description": "Invade le red ennemi à %timestamp.",
            "integerTimestamp": True,
            "preferedPositions": [
                ["jgl", None],
                ["mid", None],
                ["top", 0],
                ["adc", 1],
                ["sup", 1]
            ],
            "timeToExecute": 30,
            "minimumBreakTime": 0
        },
        "gankTop": {
            "description": "Gank la top lane à %timestamp.",
            "integerTimestamp": True,
            "preferedPositions": [
                ["jgl", None],
                ["mid", None]
            ],
            "timeToExecute": 30,
            "minimumBreakTime": 0
        },
        "gankMid": {
            "description": "Gank la mid lane à %timestamp.",
            "integerTimestamp": True,
            "preferedPositions": [
                ["jgl", None],
                ["top", None],
                ["adc", None],
                ["sup", None]
            ],
            "timeToExecute": 30,
            "minimumBreakTime": 0
        },
        "gankBot": {
            "description": "Gank la bot lane à %timestamp.",
            "integerTimestamp": True,
            "preferedPositions": [
                ["jgl", None],
                ["mid", None]
            ],
            "timeToExecute": 30,
            "minimumBreakTime": 0
        },
        "noCS": {
            "description": "Ne tue pas de sbire ni de camp de %timestamp à %endtimestamp.",
            "integerTimestamp": True,
            "preferedPositions": [
                [None, None]
            ],
            "timeToExecute": 5,
            "minimumBreakTime": 2*60
        },
        "assistEpicMonsters": {
            "description": "Obtiens le takedown sur tous les monstres épiques tués (même ceux des ennemis) entre %timestamp et %endtimestamp.",
            "integerTimestamp": False,
            "preferedPositions": [
            ],
            "timeToExecute": 15,
            "minimumBreakTime": 4*60
        },
        "assistTowers": {
            "description": "Obtiens le takedown sur toutes les tourelles détruites entre %timestamp et %endtimestamp.",
            "integerTimestamp": False,
            "preferedPositions": [
            ],
            "timeToExecute": 15,
            "minimumBreakTime": 4 * 60
        },
        "die": {
            "description": "Meure avant %timestamp.",
            "integerTimestamp": False,
            "preferedPositions": [
                [None, None]
            ],
            "timeToExecute": 20,
            "minimumBreakTime": 1*60  # Pour être à peu près sûr que notre pauvre droïde ait respawn
        },
        "recall": {
            "description": "Back immédiatement. (à %timestamp)",
            "integerTimestamp": True,
            "preferedPositions": [
                [None, None]
            ],
            "timeToExecute": 15,
            "minimumBreakTime": 0
        },
        "sell": {
            "description": "Gagne au moins 1000 gold avant %timestamp. (Quitte à vendre des items)",
            "integerTimestamp": True,
            "preferedPositions": [
            ],
            "timeToExecute": 55,
            "minimumBreakTime": 0
        },
        "stealCamp": {
            "description": "Vole un camp à ton jungler avant %timestamp.",
            "integerTimestamp": True,
            "preferedPositions": [
                ["top", None],
                ["mid", None],
                ["adc", None],
                ["sup", None]
            ],
            "timeToExecute": 55,
            "minimumBreakTime": 0
        },
        "stealWave": {
            "description": "Vole une wave (6 sbires) à un laner avant %timestamp.",
            "integerTimestamp": True,
            "preferedPositions": [
                ["jgl", None],
                ["sup", None]
            ],
            "timeToExecute": 55,
            "minimumBreakTime": 0
        }
    }

    return orders


def isValidEarlyOrder(order, position, teamId):
    prefs = order["preferedPositions"]
    valid = False
    for pref in prefs:
        if (pref[0] is None or pref[0] == position) and (pref[1] is None or pref[1] == teamId):
            valid = True
            break

    return valid


def getGameState(ctx):
    cursor.execute("SELECT guildId FROM game WHERE discordId = ?", (ctx.author.id,))
    res = cursor.fetchall()
    guildId = res[0][0]

    cursor.execute("SELECT inGame FROM guildInfo WHERE guildId = ?", (guildId,))
    res = cursor.fetchall()

    return res[0][0]


def addScore(discordId, score):
    cursor.execute("SELECT score FROM player WHERE discordId = ?", (discordId,))
    currentScore = cursor.fetchall()[0][0]

    newScore = currentScore + score

    cursor.execute("UPDATE player SET score = ? WHERE discordId = ?", (newScore, discordId))
    con.commit()


async def processGuesses(teams, playChannel):
    # Calculer les tableaux des guess
    guessTab = []  # Contient les guess
    for t in [0, 1]:
        guessTabByTeam = []
        for i, playeri in enumerate(teams[t]):
            playerGuess = playeri[5].split("/")  # Tableau des guess que le joueur i de la team t a input
            playerGuess.insert(i, None)  # Insérer un None pour avoir des indices cohérents pour l'itération qui suit
            guessTabByTeam.append(playerGuess)
        guessTab.append(guessTabByTeam)

    # Calculer les points de guess et les prettytables
    tables = [PrettyTable(), PrettyTable()]
    guessScore = []  # Contient pour chaque team les points gagnés et les points perdus par chaque couple de deux joueurs
    for t in [0, 1]:

        # Calcul du tableau des points gagnés par le player i de la team t
        posScoreByTeam = []
        for i, playeri in enumerate(teams[t]):
            playerGuessPosScore = []
            scorePerGuess = 1
            if playeri[2] == "gambler":
                scorePerGuess = 2
            for j, playerj in enumerate(teams[t]):
                if i == j:
                    playerGuessPosScore.append(0)
                else:
                    score = scorePerGuess * (guessTab[t][i][j] == playerj[2])
                    addScore(playeri[0], score)
                    playerGuessPosScore.append(score)

            posScoreByTeam.append(playerGuessPosScore)

        guessScore.append(posScoreByTeam)

        # Calcul du tableau des points perdus par le player i de la team t
        negScoreByTeam = []
        for i, playeri in enumerate(teams[t]):
            playerGuessNegScore = []
            scorePerGuess = -1
            if playeri[2] in ["imposteur", "escroc"]:
                scorePerGuess = -2
            for j, playerj in enumerate(teams[t]):
                if i == j:
                    playerGuessNegScore.append(0)
                else:
                    score = scorePerGuess * (guessTab[t][j][i] == playeri[2])
                    addScore(playeri[0], score)
                    playerGuessNegScore.append(score)

            negScoreByTeam.append(playerGuessNegScore)

        guessScore.append(negScoreByTeam)

        # Calcul des prettytables
        # Première colonne / joueurs
        tables[t].add_column(f"Team de {'gauche' if not t else 'droite'} :",
                             ["\u200b"] * 2 + [(await bot.fetch_user(player[0])).name for player in teams[t]])
        # Deuxième colonne / points gagnés
        tables[t].add_column("\u200b", ["\u200b"] * 2 + [f"+{sum(posScoreList)}" for posScoreList in posScoreByTeam])

        # Colonnes des joueurs
        for j, playerj in enumerate(teams[t]):
            fieldName = (await bot.fetch_user(playerj[0])).name
            fieldValue = [playerj[2], str(sum(negScoreByTeam[j]))]
            fieldValue += ["/" if guessTab[t][i][j] is None else guessTab[t][i][j] for i in range(len(teams[t]))]

            tables[t].add_column(fieldName, fieldValue)

        await playChannel.send(f"```{tables[t].get_string()}```")

    return guessTab


async def processRoles(teams, playChannel, guessTab):
    scoresLists = [[], []]
    for t in [0, 1]:
        for i, playeri in enumerate(teams[t]):
            scoreDelta = None
            if playeri[2] == "imposteur":
                scoreDelta = getScoreImposteur(gameData, playeri[7])
            elif playeri[2] == "Roméo":
                julietteIndex = playeri[3]
                julietteNameTag = teams[1-t][julietteIndex][7]
                scoreDelta = getScoreRomeo(gameData, playeri[7], julietteNameTag)
            elif playeri[2] == "droïde":
                cursor.execute("SELECT ordre, timestamp FROM droïdes WHERE discordId = ? ORDER BY timestamp", (playeri[0],))
                ordres = cursor.fetchall()
                scoreDelta = getScoreDroide(gameData, playeri[7], ordres)
            elif playeri[2] == "serpentin":
                scoreDelta = getScoreSerpentin(gameData, playeri[7])
            elif playeri[2] == "escroc":
                scoreDelta = getScoreEscroc(guessTab, t, i)
            elif playeri[2] == "super-héros":
                scoreDelta = getScoreSuperHeros(gameData, playeri[7])
            elif playeri[2] == "analyste":
                scoreDelta = getScoreAnalyste(gameData, playeri[7], playeri[3])
            elif playeri[2] == "réglo":
                scoreDelta = getScoreReglo(gameData, playeri[7], playeri[3])
            elif playeri[2] == "radin":
                scoreDelta = getScoreRadin(gameData, playeri[7])
            elif playeri[2] == "philosophe":
                scoreDelta = getScorePhilosophe(gameData, playeri[7])
            elif playeri[2] == "gambler":
                enemyNameTags = [enemy[7] for enemy in teams[1-t]]
                scoreDelta = getScoreGambler(gameData, enemyNameTags, list(playeri[3]))

            addScore(playeri[0], scoreDelta)
            scoresLists[t].append(scoreDelta)

    table = PrettyTable()
    #  Team de gauche
    table.add_column("Team de gauche", [(await bot.fetch_user(playeri[0])).name for playeri in teams[0]])
    table.add_column("Rôle", [playeri[2] for playeri in teams[0]])
    table.add_column("Points de rôle", [f"{'+' if score > 0 else ''}{score}" for score in scoresLists[0]])
    # Colonne milieu
    table.add_column("/", ["/" if i % 2 else "\\" for i in range(len(teams[0]))])
    # Team de droite
    table.add_column("Points de rôle", [f"{'+' if score > 0 else ''}{score}" for score in scoresLists[1]])
    table.add_column("Rôle", [playeri[2] for playeri in teams[1]])
    table.add_column("Team de droite", [(await bot.fetch_user(playeri[0])).name for playeri in teams[1]])

    await playChannel.send(f"```{table.get_string()}```")


async def processData():
    # Croiser les données de la game avec les stats des joueurs
    # discordId teamId role subRole guildId guess discordId nameTag score
    teams = []
    for t in [0, 1]:
        cursor.execute(
            "SELECT * FROM game JOIN player ON game.discordId = player.discordId WHERE game.teamId = ? ORDER BY game.discordId",
            (t,)
        )
        teamt = cursor.fetchall()
        teams.append(teamt)

    # Envoyer un premier feedback
    cursor.execute("SELECT playChannelId FROM guildInfo WHERE guildId = ?", (teams[0][0][4],))
    playChannel = await bot.fetch_channel(int(cursor.fetchall()[0][0]))
    await playChannel.send("J'ai bien reçu les guess de tout le monde, je process la data et je reviens 🫡")

    # Process les points et les tableaux des guess
    guessTab = await processGuesses(teams, playChannel)

    # Process les points des rôles et envoie le message de récap
    await processRoles(teams, playChannel, guessTab)


# When bot gets online
@bot.event
async def on_ready():
    now = datetime.datetime.now()
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print(str(now.day) + "/" + str(now.month) + "/" + str(now.year) + " " + str(now.hour) + ":" + str(now.minute))
    print('------')


# When bot joins a server
@bot.event
async def on_guild_join(guild):
    cursor.execute(f"SELECT * FROM guildInfo WHERE guildId = ?", (guild.id,))
    res = cursor.fetchall()

    # Add server to guildInfo table if it's not already inside
    if not len(res):
        cursor.execute(f"INSERT INTO guildInfo VALUES (?, ?, ?)", (guild.id, None, 0))
        con.commit()


@bot.slash_command(
    name="set_play_channel",
    description="Pour changer le channel dans lequel le bot doit envoyer les messages de jeu."
)
async def set_play_channel(ctx):
    cursor.execute(
        f"UPDATE guildInfo SET playChannelId = ? WHERE guildId = ?",
        (ctx.channel.id, ctx.guild.id)
    )
    con.commit()
    await ctx.respond("Channel changé !")


@bot.slash_command(
    name="profile",
    description="Pour link ton profil LoL avec discord."
)
async def profile(ctx, nametag: discord.Option(str, description="Nom_InGame#Tag")):
    if "#" not in nametag:
        await ctx.respond("Il me faut ton # aussi :p")
        return

    # Vérifier que le joueur existe
    name, tag = nametag.split("#")
    ans = requests.get(f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={key}")
    if ans.status_code != 200:  # Si le joueur n'existe pas
        await ctx.respond("Pas trouvé ton profil :/ Vérifie ton nom#tag")
        return

    # Insérer ou update le joueur en fonction de s'il est déjà dans la table
    cursor.execute(f"SELECT * FROM player WHERE discordId = ?", (ctx.author.id,))
    res = cursor.fetchall()
    if not len(res):  # Le joueur ne s'est pas encore inscrit
        cursor.execute(f"INSERT INTO player VALUES (?, ?, ?)", (ctx.author.id, nametag, 0))
    else:  # Le joueur était déjà inscrit
        cursor.execute(f"UPDATE player SET nameTag = ? WHERE discordId = ?", (nametag, ctx.author.id))
    con.commit()

    await ctx.respond("Tu es maintenant inscrit :)")


@bot.slash_command(
    name="play",
    description="Pour participer à une partie."
)
async def play(
        ctx,
        team: discord.Option(str, description="Team de gauche / team de droite / aucun pour ne pas jouer", choices=["gauche", "droite", "aucun", "reset"]),
        player: discord.Option(str, description="Pour ajouter / enlever quelqu'un d'une team", required=False, default="")
):
    # Vérifie le game state
    cursor.execute("SELECT inGame FROM guildInfo WHERE guildId = ?", (ctx.guild.id,))
    res = cursor.fetchall()
    if res[0][0] != 0 and team != "reset":
        await ctx.respond("Les rôles pour cette partie ont déjà été donnés visiblement. Pour TOUT reset, exécute `/play reset`")
        return

    if not player:  # Sélectionne l'auteur du message comme player par défaut
        player = ctx.author.id
    else:  # Sinon récupère l'id de la personne forcée
        player = int(player[2:-1])

    if team == "gauche":
        team = 0
    elif team == "droite":
        team = 1
    elif team == "aucun":
        team = -1
    else:  # team = reset
        # Supprime toutes les infos de la partie et reset le game state
        cursor.execute("DELETE FROM game")
        cursor.execute("DELETE FROM droïdes")
        cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (0, ctx.guild.id))
        con.commit()
        await ctx.respond("Partie reset.")
        return

    # Retirer le joueur de la db si il ne joue pas
    if team == -1:
        cursor.execute("DELETE FROM game WHERE discordId = ?", (player,))
        con.commit()
        await ctx.respond(f"Ah, {'<@'+str(player)+'>, ' if ctx.author.id != player else ''} tu nous détestes.")
        return

    # Check que le joueur n'est pas déjà dans une équipe
    cursor.execute("SELECT * FROM game WHERE discordId = ?", (player,))
    res = cursor.fetchall()
    if len(res):
        if res[0][1] == team:
            await ctx.respond("Tu es déjà dans cette équipe !")
            return

    # Check qu'il n'y a pas déjà 10 joueurs dans la partie
    cursor.execute("SELECT * FROM game WHERE teamId = ?", (team,))
    res = cursor.fetchall()
    if len(res) >= 5:
        embed = createTeamsEmbed()
        await ctx.respond(f"J'ai déjà 5 personnes dans la team de **{'gauche' if team == 0 else 'droite'}**. Tu peux exécuter `/play aucun @joueur` pour enlever de force une personne de la team.", embed=embed)
        return

    # Enlève le joueur de l'autre équipe au cas où, puis l'ajoute à la bonne
    cursor.execute("DELETE FROM game WHERE discordId = ?", (player,))
    cursor.execute("INSERT INTO game VALUES (?, ?, ?, ?, ?, ?)", (player, team, None, None, ctx.guild.id, None))
    con.commit()

    await ctx.respond(f"{'<@'+str(player)+'>, tu' if player != ctx.author.id else 'Tu'} joues maintenant dans l'**équipe de {'gauche' if team == 0 else 'droite'}**.")


@bot.slash_command(
    name="game",
    description="Pour voir l'état actuel de la partie."
)
async def game(ctx):
    await ctx.respond(embed=createTeamsEmbed())


@bot.slash_command(
    name="roles",
    description="A exécuter lorsque le host lance le champ select !"
)
async def roles(ctx):
    # Vérifie que les rôles n'ont pas déjà été donné
    if getGameState(ctx) != 0:
        await ctx.respond("Je partage l'engouement, mais les rôles ont déjà été donnés pour cette partie !")
        return

    # Vérifie qu'un play_channel est set, sinon le set au channel actuel
    cursor.execute("SELECT playChannelId FROM guildInfo WHERE guildId = ?", (ctx.guild.id,))
    res = cursor.fetchall()
    if not res[0][0]:
        cursor.execute("UPDATE guildInfo SET playChannelId = ? WHERE guildId = ?", (ctx.channel.id, ctx.guild.id))
        con.commit()
        await ctx.channel.send("J'ai enregistré le channel actuel en tant que channel de jeu. Vous pouvez le changer avec `/set_play_channel`")

    await ctx.respond("Je vous envoie vos rôles...")

    # Recense les joueurs des deux équipes
    cursor.execute("SELECT * FROM game WHERE teamId = ? ORDER BY discordId", (0,))
    team1 = cursor.fetchall()
    team1Count = len(team1)
    cursor.execute("SELECT * FROM game WHERE teamId = ? ORDER BY discordId", (1,))
    team2 = cursor.fetchall()
    team2Count = len(team2)

    teams = [team1, team2]
    teamCounts = [team1Count, team2Count]

    # Randomise les rôles des deux équipes
    for t in [0, 1]:
        impostorIdx = random.randint(0, max(0, teamCounts[t] - 1))  # Désigne l'imposteur de l'équipe
        for j, tup in enumerate(teams[t]):
            player = await bot.fetch_user(tup[0])

            subRole = None
            embed = None
            if impostorIdx == j:  # Imposteur
                role = "imposteur"
                description = "Tu dois secrètement faire perdre ton équipe sans te faire démasquer."
            else:  # Choisit un autre rôle au pif
                rolesL = listRoles()
                role = random.choice(list(rolesL.keys()))

                # Choose subrole if the role chosen above requires it
                if rolesL[role][1]:
                    subRole = random.choice(rolesL[role][1])

                # Retrouve la description associée au rôle et la complète avec le subrole si besoin
                description = rolesL[role][0]
                if "%joueur" in description:  # Roméo
                    julietteId = int(teams[1-t][subRole][0])  # Choisit une Juliette dans l'équipe d'en face
                    description = description.replace("%joueur", f"<@{julietteId}>")
                elif "%order" in description:  # Analyste
                    description = description.replace("%order", f"{subRole[0]} < {subRole[1]} < {subRole[2]}")
                elif "%which1" in description:  # Réglo
                    which1 = "meures" if not subRole else "obtiens un takedown (kill ou assist)"
                    which2 = "mourir" if not subRole else "obtenir un takedown"
                    description = description.replace("%which1", which1).replace("%which2", which2)
                elif role == "gambler":
                    embed = discord.Embed()
                    embed.add_field(name="Team ennemie :", value="\n".join([f"**{enemyJ+1}** : <@!{teams[1-t][enemyJ][0]}>" for enemyJ in range(len(teams[1-t]))]))

            # Save role & subRole to db
            cursor.execute(
                "UPDATE game SET role = ?, subRole = ? WHERE discordId = ?",
                (role, subRole, tup[0])
            )
            con.commit()

            await player.send(f"Tu es **{role}**.\n*{description}*", embed=embed)

    # Update l'état de la game dans la db
    cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (1, ctx.guild.id))
    con.commit()

    await ctx.channel.send("Je viens d'envoyer les rôles à tout le monde... 🕵️")


@bot.slash_command(
    name="gamble",
    description="A exécuter EN MP pour faire tes paris en tant que gambler !"
)
async def gamble(
        ctx,
        top: discord.Option(str, choices=["1", "2", "3", "4", "5"]),
        jgl: discord.Option(str, choices=["1", "2", "3", "4", "5"]),
        mid: discord.Option(str, choices=["1", "2", "3", "4", "5"]),
        adc: discord.Option(str, choices=["1", "2", "3", "4", "5"]),
        sup: discord.Option(str, choices=["1", "2", "3", "4", "5"])
):
    # Vérifie que le joueur est gambler
    cursor.execute("SELECT role FROM game WHERE discordId = ?", (ctx.author.id,))
    res = cursor.fetchall()
    if res[0][0] != "gambler":
        await ctx.respond("Tu n'es pas gambler chenapan !")
        return

    # Vérifie que la partie n'a pas encore commencé
    if getGameState(ctx) not in [1, 2]:
        await ctx.respond("Trop tard... la partie a déjà commencé depuis plus de 30 secondes.")
        return

    gambleList = [top, jgl, mid, adc, sup]

    # Cherche des doublons dans la liste
    doublon = False
    for i in range(5):
        if gambleList.count(str(i+1)) > 1:
            doublon = True

    # Enregistre le gamble dans la db
    gambleStr = "".join(gambleList)
    cursor.execute("UPDATE game SET subRole = ? WHERE discordId = ?", (gambleStr, ctx.author.id))
    con.commit()

    if doublon:
        await ctx.respond(f"Tu as des doublons dans ta liste : `{'/'.join(gambleList)}`\nTu peux toujours exécuter la commande de nouveau pour changer tes gamble si tu le souhaites.")
    else:
        # Retrouver les pings des joueurs de la teams pour preview les gambles
        cursor.execute("SELECT teamId FROM game WHERE discordId = ?", (ctx.author.id,))
        res = cursor.fetchall()
        teamId = res[0][0]
        cursor.execute("SELECT discordId FROM game WHERE teamId = ? ORDER BY discordId", (1-teamId,))
        res = cursor.fetchall()
        gambleDict = dict([(pos, f"<@!{res[int(gambleList[i])-1][0]}>") for i, pos in enumerate(["top", "jgl", "mid", "adc", "sup"])])

        # Crée l'embed
        embed = discord.Embed()
        embed.add_field(name="Team ennemie :", value="\n".join([f"**{list(gambleDict.keys())[i]}** : {list(gambleDict.values())[i]}" for i in range(5)]))

        await ctx.respond(f"J'ai bien enregistré tes gambles !", embed=embed)


@bot.slash_command(
    name="position",
    description="Ta position, à m'envoyer EN MP en tant que droïde avant le début de la partie."
)
async def position(
        ctx,
        ta_position: discord.Option(str, choices=["top", "jgl", "mid", "adc", "sup"])
):
    # Vérifie que le joueur est droïde
    cursor.execute("SELECT role FROM game WHERE discordId = ?", (ctx.author.id,))
    res = cursor.fetchall()
    if res[0][0] != "droïde":
        await ctx.respond("Tu n'es pas droïde chenapan !")
        return

    # Vérifie que la partie n'a pas encore commencé
    if getGameState(ctx) not in [1, 2]:
        await ctx.respond("Trop tard... la partie a déjà commencé depuis plus de 30 secondes.")
        return

    cursor.execute("UPDATE game SET subRole = ? WHERE discordId = ?", (ta_position, ctx.author.id))
    con.commit()
    await ctx.respond("J'ai bien enregistré ta position pour cette partie !")


@bot.slash_command(
    name="start",
    description="A utiliser lorsque la partie se lance !"
)
async def start(ctx):
    # Vérifie que la partie n'a pas déjà été lancée
    if getGameState(ctx) != 1:
        await ctx.respond("Je partage l'engouement, mais la partie a déjà été lancée !")
        return

    # Update l'état de la game dans la db
    cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (2, ctx.guild.id))
    con.commit()

    await ctx.respond("Partie lancée... GLHF ! ⚔️")

    # Attend un peu pour laisser le temps au gambler
    await asyncio.sleep(25)

    # Avance l'état de la partie pour lock les gamble
    cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (3, ctx.guild.id))
    con.commit()

    # Garde en mémoire la durée actuelle de la partie (en s)
    gameTime = 30

    # Retrouve tous les joueurs droïdes dans la partie
    cursor.execute("SELECT discordId, teamId, subRole FROM game WHERE role = 'droïde'")
    oldDroides = cursor.fetchall()

    # Check la position de chaque droïde, sinon lui en assigne une random
    droides = []
    for droide in oldDroides:
        if droide[2] is None:
            droides.append([await bot.fetch_user(droide[0]), droide[1], random.choice(["top", "jgl", "mid", "adc", "sup"])])
        else:
            droides.append([await bot.fetch_user(droide[0]), droide[1], droide[2]])

    # Décide des ordres à donner aux droïdes
    for droide in droides:
        ordres = listDroidOrders()

        # Shuffle l'ordre dictionnaire
        ordresL = list(ordres.items())  # Prend la liste des items pour pouvoir la shuffle après
        random.shuffle(ordresL)

        # Prend les 6 premiers ordres tels que les deux premiers soient valides pour le rôle/teamId en early
        newOrdresL = []
        while len(newOrdresL) < 2:  # Calcule les deux premiers
            if isValidEarlyOrder(ordresL[0][1], droide[2], droide[1]):
                newOrdresL.append(ordresL.pop(0))
            else:
                ordresL.append(ordresL.pop(0))
        for _ in range(4):  # Rajoute les 4 suivants
            newOrdresL.append(ordresL.pop(0))

        # Attribue un timestamp aux ordres
        finalOrders = []
        orderTime = 3*60  # Pas d'ordre avant 3 minutes de jeu
        for i in range(6):
            if i:
                orderTime += newOrdresL[i-1][1]["minimumBreakTime"]
                orderTime += random.randrange(2*60, 6*60)
            else:
                orderTime += random.randrange(0, 3*60)

            if newOrdresL[i][1]["integerTimestamp"]:
                orderTime += (60 - orderTime % 60) % 60  # Rajouter le temps qu'il faut pour arriver sur la prochaine minute entière

            finalOrders.append([newOrdresL[i][0], orderTime])

        # Ajoute les ordres à la db
        for ordreId, timestamp in finalOrders:
            cursor.execute("INSERT INTO droïdes VALUES (?, ?, ?)", (droide[0].id, ordreId, timestamp))
        con.commit()

        droide.append(finalOrders)  # Elément k=3

    # Envoyer les ordres aux droïdes...

    gs = getGameState(ctx)
    ordersDict = listDroidOrders()
    while gs <= 3:
        for droide in droides:
            thisOrders = droide[3]
            for orderId, timestamp in thisOrders:
                if timestamp == gameTime + ordersDict[orderId]["timeToExecute"] + 3:  # if it's time to give this order - Lets 3 more seconds to compensate for late start, process time etc.
                    timestamp2 = timestamp + ordersDict[orderId]["minimumBreakTime"]
                    await droide[0].send("Beep Boop.\n**"+ordersDict[orderId]["description"].replace("%timestamp", f"{str(timestamp // 60).zfill(2)}:{str(timestamp % 60).zfill(2)}").replace("%endtimestamp", f"{str(timestamp2 // 60).zfill(2)}:{str(timestamp2 % 60).zfill(2)}")+"**")
        await asyncio.sleep(1)
        gameTime += 1
        gs = getGameState(ctx)


@bot.slash_command(
    name="end",
    description="Pour indiquer au bot que la partie est terminée. N'utiliser QUE LORSQUE l'écran des stats a chargé."
)
async def end(
        ctx,
        data: discord.Option(discord.Attachment, description="A remplir si Spy ne joue pas.", required=False) = None
):
    # Check previous game state
    if getGameState(ctx) != 3:
        await ctx.respond("La partie n'est pas en cours !")
        return

    # Get data from file if provided else try from LCU
    global gameData
    if data is None:
        try:
            game = lcu.get("/lol-match-history/v1/products/lol/current-summoner/matches?begIndex=0&endIndex=0")["games"]["games"][0]
            gameTimeline = lcu.get(f"/lol-match-history/v1/game-timelines/{game['gameId']}")
            gameData = [game, gameTimeline]
        except (LCUClosedError, LCUDisconnectedError):
            await ctx.channel.send(f"{ctx.author.mention} Spy n'est visiblement pas connecté, il me faut les données de la partie dans un .txt en argument :/")
    else:
        gameData = requests.get(data.url).json()

    # Update game state
    cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (4, ctx.guild.id))
    con.commit()

    # Répond avant d'envoyer les mp pour être sûr d'être dans les temps
    await ctx.respond("Gg ! A présent, checkez vos MP pour guess les rôles de vos alliés ! 👀")

    # DM each player and ask them to guess their teammates' roles
    cursor.execute("SELECT discordId, teamId FROM game ORDER BY discordId")
    players = cursor.fetchall()
    for player in players:
        # Retrouve le user
        playerId, teamId = player[0], player[1]
        playerUser = await bot.fetch_user(int(playerId))

        # Crée l'embed en cherchant les teammates de l'utilisateur
        embed = discord.Embed()
        cursor.execute("SELECT discordId FROM game WHERE teamId = ? AND discordId != ? ORDER BY discordId", (teamId, playerId))
        res = cursor.fetchall()
        embed.add_field(name="Team alliée :", value="\n".join([f"**{i+1}** : <@!{res[i][0]}>" for i in range(len(res))]))

        await playerUser.send(f"La partie est terminée !\n*Guess le rôle de tes alliés maintenant en utilisant `/report <rôle de l'allié 1> ... <rôle de l'allié 4>` ! Le numéro de tes teammates sont donnés ci-dessous*", embed=embed)


@bot.slash_command(
    name="report",
    description="A utiliser EN MP pour faire tes guess sur les rôles de tes alliés lorsque la partie est terminée !"
)
async def report(
        ctx,
        role1: discord.Option(str, choices=["imposteur"] + list(listRoles().keys())),
        role2: discord.Option(str, choices=["imposteur"] + list(listRoles().keys())),
        role3: discord.Option(str, choices=["imposteur"] + list(listRoles().keys())),
        role4: discord.Option(str, choices=["imposteur"] + list(listRoles().keys())),
):
    # Check game state
    if getGameState(ctx) != 4:
        await ctx.respond("La partie n'est pas encore terminée ! Si c'est pourtant le cas, exécute `/end <game_data>` dans le serveur discord !")
        return

    # Update guesses into db
    roleList = [role1, role2, role3, role4]
    cursor.execute("UPDATE game SET guess = ? WHERE discordId = ?", ("/".join(roleList), ctx.author.id))
    con.commit()

    # Create embed for double check
    embed = discord.Embed()
    cursor.execute("SELECT teamId FROM game WHERE discordId = ?", (ctx.author.id,))
    teamId = cursor.fetchall()[0][0]
    cursor.execute("SELECT discordId FROM game WHERE teamId = ? AND discordId != ? ORDER BY discordId", (teamId, ctx.author.id))
    res = cursor.fetchall()
    embed.add_field(name="Team alliée :", value="\n".join([f"<@!{res[i][0]}> : **{roleList[i]}**" for i in range(4)]))

    await ctx.respond("Tes guess ont bien été enregistrés !", embed=embed)

    # Check si c'est le dernier joueur à report
    cursor.execute("SELECT * FROM game ORDER BY discordId")
    game = cursor.fetchall()
    allGuessed = True
    for player in game:
        if player[5] is None:
            allGuessed = False
            break

    # Si c'est le dernier, change le game state et process la data, sinon attend les autre joueurs
    if allGuessed:
        cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (5, game[0][4]))
        con.commit()
        await processData()


@bot.slash_command(
    name="scoreboard",
    description="Montre les joueurs ayant le plus de point. Si c'est toi, bravo. Tu peux flex."
)
async def scoreboard(ctx):
    cursor.execute("SELECT score, discordId FROM player")
    players = cursor.fetchall()

    embed = discord.Embed()
    embed.title = "Meilleurs imposteurs de ce serveur :"

    playersFromServer = []  # Scoreboard must only contain players from the server in which the command is executed.
    for player in players:
        if ctx.guild.get_member(player[1]) is not None:
            playersFromServer.append(player)

    playersFromServer.sort(reverse=True)
    top10 = playersFromServer[:10]  # N'affiche que les 10 premiers

    field1 = [f"{i+1}." for i in range(len(top10))]
    field2 = [f"<@!{player[1]}>" for player in top10]
    field3 = [str(player[0]) for player in top10]

    discordIdsSorted = [player[1] for player in playersFromServer]
    # Le joueur n'est pas dans le top 10 mais est dans la liste des joueurs du serveur ; alors le rajoute en bas pour qu'il voie son rang
    if ctx.author.id not in discordIdsSorted[:10] and ctx.author.id in discordIdsSorted:
        rank = discordIdsSorted.index(ctx.author.id)
        field1 += ["", "|", "", f"{rank+1}."]
        field2 += ["", "|", "", f"<@!{playersFromServer[rank][1]}>"]
        field3 += ["", "|", "", f"{playersFromServer[rank][0]}"]

    embed.add_field(name="__n°__", value="\n".join(field1))
    embed.add_field(name="__Joueur__", value="\n".join(field2))
    embed.add_field(name="__Score__", value="\n".join(field3))

    await ctx.respond(embed=embed)


@bot.slash_command(
    name="gs"
)
async def gs(ctx, gamestate):
    cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (gamestate, ctx.guild.id))
    con.commit()
    await ctx.respond("gs updated")


# Run the bot
token = open("token.txt", "r").read()
bot.run(token)
