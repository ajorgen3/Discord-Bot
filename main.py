from datetime import datetime, date, timezone
import time
import discord
from discord.ext.commands import Bot
from discord import Intents
import statistics
import matplotlib as MPL
import matplotlib.pyplot as plot
import matplotlib.dates as MPLDates
import sqlite3

#####################
##### Variables #####
#####################

# Intents to be used by the bot. Necessary for the discord API
intents = Intents.all()
# The bot client. Use '~' to start a command
bot = Bot(intents=intents, command_prefix='~')
# A list of users authorized to use the administrative commands
aristocrats = []
# Maps users to another map that maps datetime objects to a message count.
messageCountDatabase = {}
# The total number of messages in the guild
totalMessages = 0
# Maps users to another map that maps names of statistics (string) to that statistic for the user.
userStatsMap = {}
# Maps the name of the ranking chart (string) to a sorted list of tuples. Each tuple contains the user being ranked (index 0)
# and the data being ranked by (index 1). The data is sorted by index 1.
rankingsMap = {}
#sqlite3 connection
conn = sqlite3.connect('test.db')

###################
###### Events #####
###################

# Code that runs when the bot is ready for use. Initializes the arisocrats list, then prints 'Bot connected' to the console.
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game('Rocket League'))
    await initializeAristocrats()

    print('Bot connected')


#########################
##### Test Commands #####
#########################

@bot.command(name='test')
async def test(context):
    message = context.message
    user = getUser(context)

    await message.channel.send(len(messageCountDatabase))
    await message.channel.send(len(messageCountDatabase[user]))

    await message.channel.send("completed for user: " + user.mention)
    await message.channel.send("command complete")


@bot.command(name='test2')
async def test2(context):
    channel = context.message.channel
    user = getUser(context)

    messageCountList = list(messageCountDatabase[user].values())
    for count in messageCountList:
        print(str(count) + "\n")

@bot.command(name='DBTest')
async def DBTest(context):


##############################
##### Message Statistics #####
##############################

# Prints the total number of messages for the server in the channel the command was sent in.
@bot.command(name='totalservermessages')
async def totalServerMessages(context):
    global totalMessages
    await context.message.channel.send("Total server messages: " + str(totalMessages))


# Prints the total number of messages for the target in the channel the command was sent in.
# The target is determined by getUser()
@bot.command(name='totalmessages')
async def totalUserMessages(context):
    message = context.message
    user = getUser(context)

    await message.channel.send(user.mention + "'s total message count: " + str(userStatsMap[user]["total messages"]))


# Prints the percent of the total messages in the server that were sent by the target in the channel the command was sent in.
# The target is determined by getUser()
@bot.command(name='percenttotal')
async def percentTotal(context):
    global totalMessages
    user = getUser(context)
    channel = context.message.channel
    percent = int(userStatsMap[user]["total messages"] / totalMessages * 10000) / 100

    await channel.send(user.mention + " has sent " + str(percent) + "% of the server's total messages")


# Prints a list of stats about the target in the channel the command was sent in.
# The target is determined by getUser()
# Stats: total messages sent, mean, median, mode, range, min, max, standard deviation, number of days active
@bot.command(name='stats')
async def stats(context):
    message = context.message
    user = getUser(context)

    await message.channel.send("Note: All stats are based exclusively on days the user sent messages.")

    await message.channel.send(user.mention+ "'s statistics:"
                                + "\nTotal message count: "+ str(userStatsMap[user]["total messages"])
                                + "\nMean daily messages: " + str(userStatsMap[user]["mean"])
                                + "\nMedian daily messages: "+ str(userStatsMap[user]["median"])
                                + "\nMode daily messages: " + str(userStatsMap[user]["mode"])
                                + "\nMax messages in 1 day: " + str(userStatsMap[user]["maximum"])
                                + "\nMin messages in 1 day: " + str(userStatsMap[user]["minimum"])
                                + "\nRange: " + str(userStatsMap[user]["minimum"]) + " - " + str(userStatsMap[user]["maximum"])
                                + (("\nStandard Deviation: " + str(userStatsMap[user]["SD"])) if (userStatsMap[user]["days active"] >= 2) else "")
                                + "\nNumber of days active: " + str(userStatsMap[user]["days active"]))


########################
##### Leaderboards #####
########################

# Prints a leaderboard of all members of the guild based on their message count in descending order. The target's place
# on the leaderboard is printed in bold text. The leaderboard is printed in the channel the command was sent in.
# The target is determined by getUser()
@bot.command(name='messagechart')
async def messageChart(context):
    channel = context.message.channel
    user = getUser(context)
    toPrint = "Top message chart:\n"

    for idx, pair in enumerate(rankingsMap["most message chart"]):
        if (pair[0] == user):
            toPrint += "**" + str(idx + 1) + ") " + pair[0].name + " - " + str(pair[1]) + "**\n"
        else:
            toPrint += str(idx + 1) + ") " + pair[0].name + " - " + str(pair[1]) + "\n"

    await channel.send(toPrint)


##################
##### Graphs #####
##################

@bot.command(name="messageovertimegraph")   # bugged, see general for thoughts yesterday. instead of making a line graph, try doing a scatterplot instead
async def messageovertimegraph(context):
    channel = context.message.channel
    user = getUser(context)
    dateList = []
    totalMessageDates = []

    for dateT in list(messageCountDatabase[user].keys()):
        dateList.append(dateT.date())

    i = 0
    for count in list(messageCountDatabase[user].values()):
        if (i == 0):
            totalMessageDates.append(count)
        else:
            totalMessageDates.append(count + totalMessageDates[i - 1])
        i += 1

    plot.gca().xaxis.set_major_formatter(MPLDates.DateFormatter('%m/%d/%Y'))
    plot.gca().xaxis.set_major_locator(MPLDates.DayLocator(interval=int(len(dateList)/4))) # use difference between first and last date instead of length. length only works for active people
    plot.plot(dateList, totalMessageDates)
    plot.gcf().autofmt_xdate()
    plot.savefig("messageovertimegraph.png")

    with open('messageovertimegraph.png', 'rb') as img:
        await channel.send(file=discord.File(img))

    plot.clf()
    plot.cla()


@bot.command(name='messageovertimegraphserver')
async def messageovertimegraph(context):
    channel = context.message.channel
    dateList = {}
    totalMessageDates = {}
    longestLength = 0

    for user in context.message.guild.members:
        tempList = []
        for dateT in list(messageCountDatabase[user].keys()):
            tempList.append(dateT.date())
        dateList[user] = tempList

        if (len(tempList) > longestLength):
            longestLength = len(tempList)

        i = 0
        tempList = []
        for count in list(messageCountDatabase[user].values()):
            if (i == 0):
                tempList.append(count)
            else:
                tempList.append(count + tempList[i - 1])
            i += 1
        totalMessageDates[user] = tempList

    plot.gca().xaxis.set_major_formatter(MPLDates.DateFormatter('%m/%d/%Y'))
    plot.gca().xaxis.set_major_locator(MPLDates.DayLocator(interval=int(longestLength / 4)))

    for user in context.message.guild.members:
        plot.plot(dateList[user], totalMessageDates[user])

    plot.gcf().autofmt_xdate()
    plot.savefig("messageovertimegraph.png")

    with open('messageovertimegraph.png', 'rb') as img:
        await channel.send(file=discord.File(img))

    plot.clf()
    plot.cla()


#####################################
##### Miscellaneous Information #####
#####################################

# prints the date on which the target joined the guild in the channel the command was sent in. If the target had previously
# left the guild but rejoined, their most recent join date is sent.
# The target is determined by getUser()
@bot.command(name="joindate")
async def joinDate(context):
    message = context.message
    user = getUser(context)

    await message.channel.send(user.mention + " joined on: " + str(user.joined_at))


##########################
##### Administrative #####
##########################

# Updates the bot's knowledge of the guild. messageCountDatabase is recreated and totalMessages is recounted.
# initializeStats() is called near the end of the function to recalculate user stats based on the knew information.
# The time it took to run the command will be printed along with a message informing the user that the command has completed.
# update will only run if the user is in the aristocrat list. Otherwise, 'Permission denied.' will be printed.
@bot.command(name='update')
async def update(context):  # remakes the database of message counts
    startTime = time.time()
    messageOriginal = context.message
    guild = context.guild
    user = messageOriginal.author
    global totalMessages

    if (isAristocrat(user)):
        await messageOriginal.channel.send("Welcome, Aristocrat. Starting update...")
        members = guild.members

        for user in members:
            messageCountDatabase[user] = {}

        for channel in guild.channels:  # for each channel
            if (isinstance(channel, discord.CategoryChannel) or isinstance(channel, discord.VoiceChannel)):
                continue

            messages = channel.history(limit=None, oldest_first=True)

            async for message in messages:  # for each message in that channel
                sentTime = utc_to_local(message.created_at)
                sentTime = datetime(sentTime.year, sentTime.month, sentTime.day)
                try:
                    if (messageCountDatabase[message.author].get(sentTime) == None):
                        messageCountDatabase[message.author][sentTime] = 1
                        totalMessages += 1
                    else:
                        messageCountDatabase[message.author][sentTime] += 1
                        totalMessages += 1
                except:
                    print(
                        "problem encountered for user: " + message.author.name + ". Message link: " + message.jump_url)
                if (totalMessages % 1000 == 0):
                    print(str(totalMessages) + " messages indexed.")
        initializeStats(guild)
        endTime = time.time()

        seconds = int(endTime - startTime)
        hours = int(seconds / 3600)
        seconds %= 3600
        minutes = int(seconds / 60)
        seconds %= 60

        await messageOriginal.channel.send("Updated!\nUpdate took " + str(hours) + ":" + str(minutes) + ":" + str(seconds))
    else:
        await messageOriginal.channel.send("Permission denied.")


###################
##### Helpers #####
###################

# Calculates a variety of statistics for each member of the guild and places it in userStatsMap. It also calculates
# leaderboards and places them in rankingsMap
def initializeStats(guild):
    global userStatsMap, rankingsMap

    rankingsMap = {
        "most message chart": []
    }

    # general stats
    for user in guild.members:
        messageCountList = list(messageCountDatabase[user].values())
        print("user: " + user.name);
        print(messageCountList);
        userStatsMap[user] = {
            "total messages": sum(messageCountList),
            "mean": statistics.mean(messageCountList),
            "median": statistics.median(messageCountList),
            "mode": statistics.mode(messageCountList),
            "maximum": max(messageCountList),
            "minimum": min(messageCountList),
            "days active": len(messageCountDatabase[user])
        }
        if (userStatsMap[user]["days active"] >= 2):
            userStatsMap[user]["SD"] = statistics.stdev(messageCountList)

        # a map that maps strings describing the ranking category to lists of maps that map users to their message count
        # sort the list by their map values
        rankingsMap["most message chart"].append((user, userStatsMap[user]["total messages"]))

    # stats requiring all users to be defined
    rankingsMap["most message chart"] = sorted(rankingsMap["most message chart"], key=lambda x: x[1], reverse=True)


# Returns True if the argument is in aristocrats, False otherwise
def isAristocrat(user):
    global aristocrats

    for aristocrat in aristocrats:
        if (aristocrat == user):
            return True

    return False


# Returns the command's author by default. If the command mentions another user, the first user mentioned is returned.
def getUser(context):
    mentions = context.message.mentions

    if (len(mentions) != 0):
        return mentions[0]
    else:
        return context.author


# Function obtained on stack overflow.
# https://stackoverflow.com/questions/4563272/how-to-convert-a-utc-datetime-to-a-local-datetime-using-only-standard-library
# Converts datetime objects from utc to the local timezone.
def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


# Intializes the aristocrats list with authorized users.
async def initializeAristocrats():
    global aristocrats
    aristocrats = [await bot.fetch_user(1), await bot.fetch_user(2)]

bot.run('')