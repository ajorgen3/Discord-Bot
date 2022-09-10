from datetime import datetime
import discord
from discord.ext.commands import Bot
from discord import Intents
from datetime import timezone
import statistics

intents = Intents.all()
bot = Bot(intents=intents, command_prefix='~')
aristocrats = []
messageCountDatabase = {}
totalMessages = 0
userStatsMap = {}
# Maps the name of the ranking chart (string) to a sorted list of tuples. Each tuple contains the user being ranked (index 0)
# and the data being ranked by (index 1). The data is sorted by index 1.
rankingsMap = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game('Rocket League'))
    await initializeAristocrats()

    print('Bot connected')

@bot.command(name='test2')
async def test2(context):
    channel = context.message.channel
    user = getUser(context)

    messageCountList = list(messageCountDatabase[user].values())
    for count in messageCountList:
        print(str(count) + "\n")


@bot.command(name='totalmessages')
async def totalUserMessages(context):
    message = context.message
    user = getUser(context)

    await message.channel.send(user.mention + "'s total message count: " + str(userStatsMap[user]["total messages"]))

@bot.command(name='totalservermessages')
async def totalServerMessages(context):
    global totalMessages
    await context.message.channel.send("Total server messages: " + str(totalMessages))

@bot.command(name='test')                                                                                               # TEST COMMAND
async def test(context):
    message = context.message
    user = getUser(context)

    await message.channel.send(len(messageCountDatabase))
    await message.channel.send(len(messageCountDatabase[user]))

    await message.channel.send("completed for user: " + user.mention)
    await message.channel.send("command complete")

# Stats: total messages sent, mean, median, mode, range, min, max, standard deviation, number of days active
@bot.command(name='stats')
async def stats(context):
    message = context.message
    user = getUser(context)

    await message.channel.send("Note: All stats are based exclusively on days the user sent messages.")

    await message.channel.send(user.mention + "'s statistics:\nTotal message count: " + str(userStatsMap[user]["total messages"]) + "\nMean daily messages: " + str(userStatsMap[user]["mean"]) + "\nMedian daily messages: "
                               + str(userStatsMap[user]["median"]) + "\nMode daily messages: " + str(userStatsMap[user]["mode"]) + "\nMax messages in 1 day: " + str(userStatsMap[user]["maximum"])
                               + "\nMin messages in 1 day: " + str(userStatsMap[user]["minimum"]) + "\nRange: " + str(userStatsMap[user]["minimum"]) + " - " + str(userStatsMap[user]["maximum"]) +
                               "\nStandard Deviation: " + str(userStatsMap[user]["SD"]) + "\nNumber of days active: " + str(userStatsMap[user]["days active"]))

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

@bot.command(name="joindate")
async def joinDate(context):
    message = context.message
    user = getUser(context)

    await message.channel.send(user.mention + "joined on: " + str(user.joined_at))

@bot.command(name='update')
async def update(context):  # remakes the database of message counts
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
                    print("problem encountered for user: " + message.author.name + ". Message link: " + message.jump_url)
                if (totalMessages % 1000 == 0):
                    print(str(totalMessages) + " messages indexed.")
        initializeStats(guild)
        await messageOriginal.channel.send("Updated!")
    else:
        await messageOriginal.channel.send("Permission denied.")

def initializeStats(guild):
    global userStatsMap, rankingsMap

    rankingsMap = {
        "most message chart": []
    }

    # general stats
    for user in guild.members:
        messageCountList = list(messageCountDatabase[user].values())

        userStatsMap[user] = {
            "total messages": sum(messageCountList),
            "mean": statistics.mean(messageCountList),
            "median": statistics.median(messageCountList),
            "mode": statistics.mode(messageCountList),
            "maximum": max(messageCountList),
            "minimum": min(messageCountList),
            "SD": statistics.stdev(messageCountList),
            "days active": len(messageCountDatabase[user])
        }
        # a map that maps strings describing the ranking category to lists of maps that map users to their message count
        # sort the list by their map values
        rankingsMap["most message chart"].append((user, userStatsMap[user]["total messages"]))

    # stats requiring all users to be defined
    rankingsMap["most message chart"] = sorted(rankingsMap["most message chart"], key=lambda x: x[1], reverse=True)

def isAristocrat(user):
    global aristocrats

    for aristocrat in aristocrats:
        if (aristocrat == user):
            return True

    return False

def getUser(context):
    mentions = context.message.mentions

    if (len(mentions) != 0):
        return mentions[0]
    else:
        return context.author

 # Function obtained on stack overflow.
 # https://stackoverflow.com/questions/4563272/how-to-convert-a-utc-datetime-to-a-local-datetime-using-only-standard-library
def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

async def initializeAristocrats():
    global aristocrats
    aristocrats = [await bot.fetch_user(121007634714329089), await bot.fetch_user(237353382229049345)]

bot.run('MTAxNTA3MjU0MTA0NTQ0MDUyMw.GF3g7h.HMWRDE7m3qFsN4gWevg3LBw75DRdmPaPmySYyw')
