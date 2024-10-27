import discord
from discord.ext import commands
import datetime
import sqlite3
import requests
from pandas import json_normalize
from lcuapi import LCU
import random
import asyncio


# Creating the bot
bot = commands.Bot()


# Connecting to db
con = sqlite3.connect("sus.db")
cursor = con.cursor()


# Define Riot API Key
key = open("riotKey.txt").read()


# Connect to league client api
"""lcu = LCU()
lcu.wait_for_client_to_open()
lcu.wait_for_login()
"""
# ans = lcu.get("/lol-match-history/v1/game-timelines/7164199652")
# print(ans)


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
            "Dès que tu %which1 pour la première fois, tu dois %which2 toutes les 5 minutes au plus jusqu'à la fin de la partie.",
            [0, 1]
        ),
        "radin": (
            "Tu ne gardes jamais plus de 1200 gold sur toi. Juste au cas où.",
            []
        ),
        "philosophe": (
            "Tu aimes bien prendre ton temps dans la vie. Tu feras donc durer la partie autant que possible.",
            []
        ),
        "gambler": (
            "Tu parie les positions des joueurs adverses pendant l'écran de chargement grâce à `/gamble <top> <jgl> <mid> <adc> <sup>`, en remplissant les rôles avec les numéros correspondants aux joueurs ci-dessous.\nTu obtiens aussi des points bonus pour les bons guess de rôles en fin de partie !",
            []
        )
    }

    # Ordres Droid :
    # Invade le blue/red ennemi dans la prochaine minute
    # Roam/gank une lane dans la prochaine minute
    # Ne tue pas de sbire pendant 2 min
    # Assiste tous les kills de monstre épique/tourelles pendant les 5 prochaines minutes (même pour les ennemis)
    # Meure dans les 30 prochaines secondes
    # Back immédiatement
    # Vend un item à 1000+ gold dans la prochaine minute
    # Vole un camp à ton jungler / farme une wave d'un laner dans la prochaine minute

    return roles


def getGameState(ctx):
    cursor.execute("SELECT guildId FROM game WHERE discordId = ?", (ctx.author.id,))
    res = cursor.fetchall()
    guildId = res[0][0]

    cursor.execute("SELECT inGame FROM guildInfo WHERE guildId = ?", (guildId,))
    res = cursor.fetchall()

    return res[0][0]


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
async def profile(ctx, name: discord.Option(str, description="Nom_InGame#Tag")):
    if "#" not in name:
        await ctx.respond("Il me faut ton # aussi :p")
        return

    # Récupérer le puuid du joueur
    name, tag = name.split("#")
    ans = requests.get(f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}?api_key={key}")
    if ans.status_code != 200:  # Si le joueur n'existe pas
        await ctx.respond("Pas trouvé ton profil :/ Vérifie ton nom#tag")
        return
    data = ansToDict(ans)
    puuid = data["puuid"][0]

    # Insérer ou update le joueur en fonction de s'il est déjà dans la table
    cursor.execute(f"SELECT * FROM player WHERE discordId = ?", (ctx.author.id,))
    res = cursor.fetchall()
    if not len(res):  # Le joueur ne s'est pas encore inscrit
        cursor.execute(f"INSERT INTO player VALUES (?, ?, ?)", (ctx.author.id, puuid, 0))
    else:  # Le joueur était déjà inscrit
        cursor.execute(f"UPDATE player SET leaguePuuid = ? WHERE discordId = ?", (puuid, ctx.author.id))
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
        cursor.execute("DELETE FROM game")
        con.commit()
        await ctx.respond("Partie reset.")
        return

    # Retirer le joueur de la db si il ne joue pas
    if team == -1:
        cursor.execute("DELETE FROM game WHERE discordId = ?", (player,))
        con.commit()
        await ctx.respond("Ah, tu nous détestes.")
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
    cursor.execute("INSERT INTO game VALUES (?, ?, ?, ?, ?)", (player, team, None, None, ctx.guild.id))
    con.commit()

    await ctx.respond(f"Tu joues maintenant dans l'**équipe de {'gauche' if team == 0 else 'droite'}**.")


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
    if getGameState(ctx) == 1:
        await ctx.respond("Je partage l'engouement, mais les rôles ont déjà été donnés pour cette partie !")
        return

    # Vérifie qu'un play_channel est set, sinon le set au channel actuel
    cursor.execute("SELECT playChannelId FROM guildInfo WHERE guildId = ?", (ctx.guild.id,))
    res = cursor.fetchall()
    if not res[0][0]:
        cursor.execute("UPDATE guildInfo SET playChannelId = ? WHERE guildId = ?", (ctx.channel.id, ctx.guild.id))
        con.commit()
        await ctx.channel.send("J'ai enregistré le channel actuel en tant que channel de jeu. Vous pouvez le changer avec `/set_play_channel`")

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
                    description = description.replace("%order", f"{subRole[0]} ≤ {subRole[1]} ≤ {subRole[2]}")
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

    await ctx.respond("Je viens d'envoyer les rôles à tout le monde... 🕵️")


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
    if getGameState(ctx) == 3:
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
        await ctx.respond(f"Tu as des doublons dans ta liste : `{'-'.join(gambleList)}`\nTu peux toujours exécuter la commande de nouveau pour changer tes gamble si tu le souhaites.")
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
    if getGameState(ctx) == 3:
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
    if getGameState(ctx) in [2, 3]:
        await ctx.respond("Je partage l'engouement, mais la partie a déjà été lancée !")
        return

    # Update l'état de la game dans la db
    cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (2, ctx.guild.id))
    con.commit()

    await ctx.respond("Partie lancée... GLHF ! ⚔️")

    # Attend un peu pour laisser le temps au gambler
    await asyncio.sleep(30)

    # Avance l'état de la partie pour lock les gamble
    cursor.execute("UPDATE guildInfo SET inGame = ? WHERE guildId = ?", (3, ctx.guild.id))
    con.commit()

    await asyncio.sleep(10)
    await ctx.author.send("coucou")


# Run the bot
token = open("token.txt", "r").read()  # Oh 42
bot.run(token)
