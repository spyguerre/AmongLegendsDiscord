# Among Legends Discord Bot

Among Legends est un concept pensé par [Solary](https://www.solary.fr/p/among-legends)
pour mélanger Among Us et LoL en custom game. J'ai décidé de librement
adapter ce concept en bot discord, alors chargé de distribuer les rôles
et d'analyser les comportements des joueurs leur rapportant des points.

## Règles

Le concept est simple ; à chaque partie, chaque joueur se voit attribuer un [rôle](https://docs.google.com/spreadsheets/d/1h4MqdhN2jlFHlRbDWdUmKNg2IzVHtMiJueRRBWmQWag/edit?gid=0#gid=0),
pouvant lui rapporter des points s'il accomplit secrètement une ou plusieurs missions.
A la fin de la partie, les joueurs essaient de deviner les rôles de leurs
alliés.

En particulier, un imposteur se cache dans chaque équipe.
Il doit faire perdre son équipe, sans se faire repérer.

Lorsque les joueurs devinent le rôle d'un allié, ils gagnent
des points ; mais en perdent lorsqu'ils se font démasquer.

## Installation

```bash
git clone https://github.com/spyguerre/AmongLegendsDiscord

cd AmongLegendsDiscord

pip install -r /path/to/requirements.txt

touch riotKey.txt
touch token.txt
```

Enter your riot api token in `riotKey.txt` along with
your discord bot's token in `token.txt`.

Then run the bot with:

```bash
python main.py
```

## Mise en place sur Discord

Afin de lancer la première partie correctement,
un peu de setup est nécessaire :

Le bot doit être en ligne lorsque qu'il rejoint un serveur.

Indiquez au bot quel est le channel que vous utiliserez pour jouer
à Among Legends avec :
```
/set_play_channel
```

Chaque joueur participant doit ensuite renseigner son riot id (nomInGame#tag)
grâce à la commande suivante : (évitez les espaces non nécessaires :')

```
/profile <nom#tag>
```

## Déroulé d'une partie :

Pour commencer une partie :

Lorsque tous les joueurs sont dans le lobby de la custom game,
chaque joueur doit entrer la commande suivante pour
être enregistré comme participant ; en fonction de son équipe :

```
/play <gauche|droite>
```

Lorsque tout les joueurs se sont inscrits, l'un d'entre eux
exécute :

```
/roles
```

Les rôles sont alors distribués à tous les joueurs successivement.

Puis, lorsque la partie commence, c'est-à-dire à 00:00 secondes
de la partie, lorsque les champions spawnent, un joueur exécute :


```
/start
```

Cette commande doit absolument être exécutée dans les temps,
sans quoi les potentiels droïdes ne recevront pas leurs ordres, ou trop tard.

Lorsque la partie se termine, i.e. l'écran des stats s'affiche
depuis quelques secondes (éviter avant, au cas où...), un des joueurs
exécute cette commande :

```
/end
```

Cela demande alors à tous les joueurs d'utiliser la commande 
`/report <allié 1> ... <allié 4>` afin de tenter de deviner
leur rôle.

Lorsque tous les joueurs ont exécuté la commande au moins une fois,
les statistiques de la partie sont alors calculées et affichées dans
le channel de jeu.

Afin de réinitialiser la partie pour en commencer une autre,
un joueur doit exécuter la commande :

```
/play reset
```

## Autres commandes

### /game

Permet d'afficher dans un embed les équipes formées à tout moment.

### /position \<position\>

Commande pour que les droïdes indiquent leur position (top, jgl...)
dans la partie afin de recevoir des challenges un minimum appropriés.

*A exécuter entre le /roles et 30 après le début de la partie EN MP pour ne pas dévot... c'est mieux en général...*

### /scoreboard

Affiche les 10 joueurs ayant le plus de points sur le serveur,
et éventuellement le classement de l'auteur du message
s'il ne figure pas dans cette liste.

### /gs \<gameState\>

Pour changer l'avancement de la partie au cas où il y ait un problème.
- 0 > Les joueurs sont en train de se répartir dans les équipes
- 1 > Les rôles ont été distribués
- 2 > La partie vient de commencer
- 3 > La partie a commencé depuis plus de 30 secondes
- 4 > La partie est terminée, les joueurs sont en train de deviner les rôles de leurs alliés
- 5 > Tous les joueurs ont guess, le récap des scores est affiché, la partie est en attente de reset

## LCU
This program uses this [python interface](https://github.com/spyguerre/AmongLegendsDiscord)
of the LCU (an unofficial API working through the League Client).
It is *needed* to access custom games' data, since these are not public.

Also, [this](https://github.com/BlossomiShymae/Needlework.Net)
is a fantastic tool to tinker with the LCU!


###### You've just README :p
