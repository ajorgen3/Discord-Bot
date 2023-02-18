from datetime import datetime, timedelta, timezone
import time
import discord
from discord.ext.commands import Bot
from discord import Intents
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
@bot.command(name='TotalServerMessages')
async def totalServerMessages(context):
    global totalMessages, conn

    await getServer(context)
    cursor = conn.execute("SELECT SUM(MESSAGECOUNT) FROM MessageCounts;")

    await context.message.channel.send("Total server messages: " + str(cursor.fetchone()[0]))


# Prints the total number of messages for the target in the channel the command was sent in.
# The target is determined by getUser()
@bot.command(name='TotalMessages')
async def totalUserMessages(context):
    message = context.message
    user = getUser(context)

    await getServer(context)
    cursor = conn.execute("SELECT SUM(MESSAGECOUNT) FROM MessageCounts WHERE ID=?;", (user.id,))

    await message.channel.send(user.display_name + "'s total message count: " + str(cursor.fetchone()[0]))


# Prints the percent of the total messages in the server that were sent by the target in the channel the command was sent in.
# The target is determined by getUser()
@bot.command(name='PercentTotal')
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
# Stats: total messages sent, mean, range, max, min, number of days active
@bot.command(name='Stats')
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
@bot.command(name='ActivityLeaderboard')
async def messageChart(context):
    channel = context.message.channel
    users = getUserGraphs(context)
    map = {}
    toPrint = "Top message chart:\n"
    place = 1
    global conn

    await getServer(context)
    cursor = conn.execute("SELECT ID, SUM(MESSAGECOUNT) FROM MessageCounts GROUP BY ID ORDER BY 2 DESC")
    for user in users:
        map[user.id] = True

    for row in cursor:
        if (map.get(row[0])):
            toPrint += "**" + str(place) + ") " + (await bot.fetch_user(row[0])).display_name + " - " + str(row[1]) + "**\n"
        else:
            toPrint += str(place) + ") " + (await bot.fetch_user(row[0])).display_name + " - " + str(row[1]) + "\n"
        place += 1


    await channel.send(toPrint)


##################
##### Graphs #####
##################

# Graphs a users total messages sent over time. Can print for 1 or multiple users.
@bot.command(name="TotalMessagesGraph")
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

# Graphs the users messages sent per day over time to show activity variance
@bot.command(name="DailyMessagesGraph")
async def dailymessagesgraphserver(context):
    channel = context.message.channel
    users = getUserGraphs(context)
    dateList = {}
    messageCounts = {}
    global conn

    await getServer(context)

    for user in users:
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

    for user in users:
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
@bot.command(name="Joined")
async def joinDate(context):
    message = context.message
    user = getUser(context)

    await message.channel.send(user.mention + " joined on: " + str(user.joined_at))


@bot.command(name="Help")
async def help(context):
    await context.message.channel.send("**Commands:**\n"
                               "__Info__\n"
                               "By default, a command will target the user who used it. For certain commands, tag one "
                               "other user to use the command on them.\n"
                               "Graphs and leaderboards default to the user who used the command. You may tag as many\n"
                               "users as you want, and each will be added to the graph. You will need to tag yourself to\n"
                               "add yourself to the graph with the others. Add \"all\" to include every user.\n"
                               "__Message Statistics__\n"
                               "*TotalServerMessages:* Prints the total number of messages for the server\n"
                               "*TotalMessages:* Prints the total number of messages for the target user.\n"
                               "*PercentTotal:* Prints what percent of total messages sent were sent by the target user.\n"
                               "*Stats:* Prints a few statistics about the target user\n"
                               "__Leaderboards__\n"
                               "*ActivityLeaderboard:* Prints a leaderboard of all users in the server in order of number "
                               "of messages sent, descending. The target user will be bolded\n"
                               "__Graphs__\n"
                               "*TotalMessagesGraph:* Graphs total messages sent over time for targeted users\n"
                               "*DailyMessagesGraph:* Graphs messages sent per day over time for targeted users\n"
                               "__Misc__\n"
                               "*Joined:* Prints the join date of the target user\n")


##########################
##### Administrative #####
##########################

# Updates the bot's knowledge of the guild. messageCountDatabase is recreated and totalMessages is recounted.
# initializeStats() is called near the end of the function to recalculate user stats based on the knew information.
# The time it took to run the command will be printed along with a message informing the user that the command has completed.
# update will only run if the user is in the aristocrat list. Otherwise, 'Permission denied.' will be printed.
@bot.command(name='Update')
async def update(context):  # remakes the database of message counts
    startTime = time.time()
    messageOriginal = context.message
    guild = context.guild
    user = messageOriginal.author
    messageCountDatabase = {}
    totalMessages = 0
    global conn, DBName

    if (isAristocrat(user)):
        await messageOriginal.channel.send("Welcome, Aristocrat. Starting update...")
        members = guild.members

        conn.close()
        DBName = str(guild.id) + ".db"
        filepath = "C:\\Users\\mangu\\PycharmProjects\\Discord Bot\\" + DBName
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

bot.run('MTAxNTA3MjU0MTA0NTQ0MDUyMw.GAmSoS.OcbWXqCPfhMaFHFQjoP1N2Cx9ysizLh5mSFpK0')