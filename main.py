import discord
from discord.ext import commands
import datetime
import sqlite3
import requests
from pandas import json_normalize
from lcuapi import LCU
import random


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
        "Roméo": [0, 1, 2, 3, 4],  # Doit mourir après un joueur dans la team en face
        "droïde": [],  # Exécute des ordres au fil de la partie
        "serpentin": [],  # Gagne la game avec le + de morts et dégâts
        "escroc": [],  # Se fait voter comme imposteur
        "super-héros": [],  # Gagne la game avec le plus de k ou a
        "analyste": ["kda", "kad", "dka", "dak", "akd", "adk"],  # Son kda respecte un ordre croissant donné
        "réglo": [-1, 1],  # Doit soit mourir soit avoir un takedown toutes les 5 min au plus
        "radin": [],  # Ne garde jamais plus de 1200 gold sur lui
        "philosophe": [],  # Il fait durer la partie le plus longtemps que possible
        "gambler": []  # Il parie les positions des joueurs adverses pendant l'écran de chargement et obtient des points bonus pour les bons guess en fin de partie
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
        cursor.execute(f"INSERT INTO guildInfo VALUES (?, ?)", (guild.id, None))
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
    cursor.execute("INSERT INTO game VALUES (?, ?)", (player, team))
    con.commit()

    await ctx.respond(f"Tu joues maintenant dans l'**équipe de {'gauche' if team == 0 else 'droite'}**.")


@bot.slash_command(
    name="game",
    description="Pour voir l'état actuel de la partie."
)
async def game(ctx):
    await ctx.respond(embed=createTeamsEmbed())


@bot.slash_command(
    name="start",
    description="A exécuter lorsque le host lance la partie sur le jeu !"
)
async def start(ctx):
    # Recense les joueurs des deux équipes
    cursor.execute("SELECT * FROM game WHERE teamId = ?", (0,))
    team1 = cursor.fetchall()
    team1Count = len(team1)
    cursor.execute("SELECT * FROM game WHERE teamId = ?", (1,))
    team2 = cursor.fetchall()
    team2Count = len(team2)

    # Randomise les rôles des deux équipes
    impostorIdx = random.randint(0, team1Count - 1)
    for i, tup in enumerate(team1):
        player = await bot.fetch_user(tup[0])

        if impostorIdx == i:
            role = "imposteur"
        else:
            role = "joueur"

        await player.send(f"Tu es {role}.")


token = open("token.txt", "r").read()
bot.run(token)
