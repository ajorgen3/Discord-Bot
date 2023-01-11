from datetime import datetime, timedelta, timezone
import time
import discord
from discord.ext.commands import Bot
from discord import Intents
import statistics
import matplotlib as MPL
import matplotlib.pyplot as plt
import matplotlib.dates as MPLDates
import sqlite3
import os

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
#database name. Set to test server by default
DBName = "951979508649562162.db"
#sqlite3 connection
conn = sqlite3.connect(DBName, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

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

@bot.command(name='test3')
async def test3(context):
    channel = context.message.channel
    user = getUser(context)
    global conn, DBName

    await getServer(context)

    cursor = conn.execute("SELECT DATE, MESSAGECOUNT FROM MessageCounts WHERE ID=?;", (user.id,))
    for row in cursor:
        print("date: ", row[0], " message count: ", row[1])

@bot.command(name='DBTest')
async def DBTest(context):
    global conn
    conn.close()
    filepath = "C:\\Users\\mangu\\PycharmProjects\\Discord Bot\\test.db"
    os.remove(filepath)

    conn = sqlite3.connect('test.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS COMPANY
             (ID INT PRIMARY KEY    NOT NULL,
             NAME           TEXT    NOT NULL,
             AGE            INT     NOT NULL,
             ADDRESS        CHAR(50),
             SALARY         REAL);''')
    print("Table created successfully");

    conn.execute("INSERT INTO COMPANY (ID,NAME,AGE,ADDRESS,SALARY) \
                VALUES (0, 'Bob', 40, 'bob str', 4.0 )")
    conn.execute("INSERT INTO COMPANY (ID,NAME,AGE,ADDRESS,SALARY) \
                VALUES (1, 'bill', 41, 'bill str', 4 )")

    conn.execute("INSERT INTO COMPANY (ID,NAME,AGE,ADDRESS,SALARY) \
          VALUES (2, 'Paul', 32, 'California', 20000.00 )");
    conn.execute("INSERT INTO COMPANY (ID,NAME,AGE,ADDRESS,SALARY) \
          VALUES (3, 'Allen', 25, 'Texas', 15000.00 )");
    conn.execute("INSERT INTO COMPANY (ID,NAME,AGE,ADDRESS,SALARY) \
          VALUES (4, 'Teddy', 23, 'Norway', 20000.00 )");
    conn.execute("INSERT INTO COMPANY (ID,NAME,AGE,ADDRESS,SALARY) \
          VALUES (5, 'Mark', 25, 'Rich-Mond ', 65000.00 )");

    conn.commit()
    print("values added")

    cursor = conn.execute("SELECT id, name, address, salary FROM COMPANY;")
    for row in cursor:
        print("ID = ", row[0])
        print("NAME = ", row[1])
        print("ADDRESS = ", row[2])
        print("SALARY = ", row[3], "\n")

    print("select successful")

##############################
##### Message Statistics #####
##############################

# Prints the total number of messages for the server in the channel the command was sent in.
@bot.command(name='totalservermessages')
async def totalServerMessages(context):
    global totalMessages, conn

    await getServer(context)
    cursor = conn.execute("SELECT SUM(MESSAGECOUNT) FROM MessageCounts;")

    await context.message.channel.send("Total server messages: " + str(cursor.fetchone()[0]))


# Prints the total number of messages for the target in the channel the command was sent in.
# The target is determined by getUser()
@bot.command(name='totalmessages')
async def totalUserMessages(context):
    message = context.message
    user = getUser(context)

    await getServer(context)
    cursor = conn.execute("SELECT SUM(MESSAGECOUNT) FROM MessageCounts WHERE ID=?;", (user.id,))

    await message.channel.send(user.display_name + "'s total message count: " + str(cursor.fetchone()[0]))


# Prints the percent of the total messages in the server that were sent by the target in the channel the command was sent in.
# The target is determined by getUser()
@bot.command(name='percenttotal')
async def percentTotal(context):
    global totalMessages
    user = getUser(context)
    channel = context.message.channel

    await getServer(context)
    cursorT = conn.execute("SELECT SUM(MESSAGECOUNT) FROM MessageCounts;")
    cursorU = conn.execute("SELECT SUM(MESSAGECOUNT) FROM MessageCounts WHERE ID=?;", (user.id,))

    percent = int(cursorU.fetchone()[0] / cursorT.fetchone()[0] * 10000) / 100

    await channel.send(user.display_name + " has sent " + str(percent) + "% of the server's total messages")


# Prints a list of stats about the target in the channel the command was sent in.
# The target is determined by getUser()
# Stats: total messages sent, mean, median, mode, range, min, max, standard deviation, number of days active
@bot.command(name='stats') # fix stats eventually to add median, mode, and standard deviation (if possible)
async def stats(context):
    message = context.message
    user = getUser(context)
    global conn

    await getServer(context)

    cursorTotal = conn.execute("SELECT SUM(MESSAGECOUNT) FROM MessageCounts WHERE ID=?;", (user.id,))
    cursorMean = conn.execute("SELECT AVG(MESSAGECOUNT) FROM MessageCounts WHERE ID=?;", (user.id,))
    cursorMax = conn.execute("SELECT MAX(MESSAGECOUNT) FROM MessageCounts WHERE ID=?", (user.id,))
    cursorMin = conn.execute("SELECT MIN(MESSAGECOUNT) FROM MessageCounts WHERE ID=?", (user.id,))
    cursorNumDays = conn.execute("SELECT COUNT(*) FROM MessageCounts WHERE ID = ?;", (user.id,))

    total = cursorTotal.fetchone()[0]
    mean = cursorMean.fetchone()[0]
    max = cursorMax.fetchone()[0]
    min = cursorMin.fetchone()[0]
    numDays = cursorNumDays.fetchone()[0]

    await message.channel.send(user.display_name + "'s statistics:"
                                + "\nTotal message count: "+ str(total)
                                + "\nMean daily messages: " + str(mean)
                                + "\nMax messages in 1 day: " + str(max)
                                + "\nMin messages in 1 day: " + str(min)
                                + "\nRange: " + str(min) + " - " + str(max)
                                + "\nNumber of days since joining: " + str(numDays))


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
    place = 1
    global conn

    await getServer(context)
    cursor = conn.execute("SELECT ID, SUM(MESSAGECOUNT) FROM MessageCounts GROUP BY ID ORDER BY 2 DESC")

    for row in cursor:
        if (row[0] == user.id):
            toPrint += "**" + str(place) + ") " + (await bot.fetch_user(row[0])).display_name + " - " + str(row[1]) + "**\n"
        else:
            toPrint += str(place) + ") " + (await bot.fetch_user(row[0])).display_name + " - " + str(row[1]) + "\n"
        place += 1


    await channel.send(toPrint)


##################
##### Graphs #####
##################

# Graphs a users total messages sent over time. Can print for 1 or multiple users.
@bot.command(name="messageovertimegraph")
async def messageovertimegraph(context):
    channel = context.message.channel
    users = getUserGraphs(context)
    dateList = {}
    totalMessages = {}
    longestPeriod = 0
    global conn

    await getServer(context)

    for user in users:
        cursor = conn.execute("SELECT DATE, MESSAGECOUNT FROM MessageCounts WHERE ID=?", (user.id,))
        i = 0
        dateListT = []
        totalMessagesT = []
        for row in cursor:
            dateListT.append(row[0])
            if (i == 0):
                totalMessagesT.append(row[1])
            else:
                totalMessagesT.append(row[1] + totalMessagesT[i - 1])
            i += 1
        dateList[user] = dateListT
        totalMessages[user] = totalMessagesT
        currentPeriod = len(dateListT)
        if (currentPeriod > longestPeriod):
            longestPeriod = currentPeriod

    plt.gca().xaxis.set_major_formatter(MPLDates.DateFormatter('%m/%d/%Y'))
    plt.gca().xaxis.set_major_locator(MPLDates.DayLocator(interval=int(longestPeriod / 4)))

    for user in users:
        plt.plot(dateList[user], totalMessages[user])

    plt.gcf().autofmt_xdate()
    plt.savefig("messageovertimegraph.png")

    with open('messageovertimegraph.png', 'rb') as img:
        await channel.send(file=discord.File(img))

    plt.clf()
    plt.cla()

#
@bot.command(name="dailymessagesgraph")
async def dailymessagesgraph(context):
    channel = context.message.channel
    user = getUser(context)
    dateList = []
    messageCounts = []
    global conn

    await getServer(context)

    cursor = conn.execute("SELECT DATE, MESSAGECOUNT FROM MessageCounts WHERE ID=?", (user.id,))
    for row in cursor:
        dateList.append(row[0])
        messageCounts.append(row[1])

    cursor = conn.execute("SELECT COUNT(*) FROM MessageCounts WHERE ID=?", (user.id,))
    plt.gca().xaxis.set_major_formatter(MPLDates.DateFormatter('%m/%d/%Y'))
    plt.gca().xaxis.set_major_locator(MPLDates.DayLocator(interval=int((cursor.fetchone())[0] / 4)))
    plt.plot(dateList, messageCounts)
    plt.gcf().autofmt_xdate()
    plt.savefig("messageovertimegraph.png")

    with open('messageovertimegraph.png', 'rb') as img:
        await channel.send(file=discord.File(img))

    plt.clf()
    plt.cla()


@bot.command(name="dailymessagesgraphserver")
async def dailymessagesgraphserver(context):
    channel = context.message.channel
    dateList = {}
    messageCounts = {}
    global conn

    await getServer(context)

    for user in context.message.guild.members:
        cursor = conn.execute("SELECT DATE, MESSAGECOUNT FROM MessageCounts WHERE ID=?", (user.id,))
        dateListT = []
        messageCountsT = []
        for row in cursor:
            dateListT.append(row[0])
            messageCountsT.append(row[1])
        dateList[user] = dateListT
        messageCounts[user] = messageCountsT

    cursorNumDays = conn.execute("SELECT COUNT(*) FROM MessageCounts GROUP BY ID ORDER BY COUNT(*) DESC LIMIT 1;")

    plt.gca().xaxis.set_major_formatter(MPLDates.DateFormatter('%m/%d/%Y'))
    plt.gca().xaxis.set_major_locator(MPLDates.DayLocator(interval=int((cursorNumDays.fetchone())[0] / 4)))

    for user in context.message.guild.members:
        plt.plot(dateList[user], messageCounts[user])

    plt.gcf().autofmt_xdate()
    plt.savefig("messageovertimegraph.png")

    with open('messageovertimegraph.png', 'rb') as img:
        await channel.send(file=discord.File(img))

    plt.clf()
    plt.cla()


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
    global totalMessages, conn, DBName

    if (isAristocrat(user)):
        await messageOriginal.channel.send("Welcome, Aristocrat. Starting update...")
        members = guild.members

        conn.close()
        DBName = str(guild.id) + ".db"
        filepath = "C:\\Users\\mangu\\PycharmProjects\\DiscordBot\\" + DBName
        os.remove(filepath)
        conn = sqlite3.connect(DBName, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.execute('''CREATE TABLE IF NOT EXISTS MessageCounts
                    (ID             INT             NOT NULL,
                    DATE            TIMESTAMP,
                    MESSAGECOUNT    INT DEFAULT 0);''')
        await messageOriginal.channel.send("Message count table created.")

        for user in members:
            messageCountDatabase[user] = {}

        # index all messages
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

        for user in guild.members:
            # Get their earliest message date, or the date they joined, whichever is oldest.
            dateTemp = datetime(user.joined_at.year, user.joined_at.month, user.joined_at.day)
            for date in list(messageCountDatabase[user].keys()):
                if (date < dateTemp):
                    dateTemp = datetime(date.year, date.month, date.day)

            # for each date since the user joined, fill in the database.
            while (dateTemp <= datetime.today()):
                if dateTemp in messageCountDatabase[user].keys():
                    conn.execute("INSERT INTO MessageCounts (ID, DATE, MESSAGECOUNT) \
                                VALUES (?, ?, ?);", (user.id, dateTemp, messageCountDatabase[user][dateTemp]))
                else:
                    conn.execute("INSERT INTO MessageCounts (ID, DATE) \
                                VALUES (?, ?);", (user.id, dateTemp))
                dateTemp = dateTemp + timedelta(days=1)

        conn.commit()

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

def getUserGraphs(context):
    content = context.message.content
    mentions = []

    if (content.find("all") != -1):
        return context.message.guild.members
    elif (len(context.message.mentions) != 0):
        mentions = context.message.mentions
    else:
        mentions.append(context.author)

    return mentions

# Function obtained on stack overflow.
# https://stackoverflow.com/questions/4563272/how-to-convert-a-utc-datetime-to-a-local-datetime-using-only-standard-library
# Converts datetime objects from utc to the local timezone.
def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


# Intializes the aristocrats list with authorized users.
async def initializeAristocrats():
    global aristocrats
    aristocrats = [await bot.fetch_user(121007634714329089), await bot.fetch_user(237353382229049345)]


async def getServer(context):
    global conn, DBName

    DBName = str(context.message.guild.id) + ".db"
    conn = sqlite3.connect(DBName, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

bot.run('MTAxNTA3MjU0MTA0NTQ0MDUyMw.G_i4l4.v91kz0-7QX5NsGzs3EZGiuW3BD3z2Dp6C3QIEc')