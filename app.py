from flask import Flask, render_template, request, jsonify

import psycopg2
import psycopg2.extras
import psycopg2.extensions
import sys
import json
import requests
from urllib.parse import urlparse
import os
import geopy
from geopy.distance import geodesic
from math import radians, cos, sin, asin, sqrt
import uuid
from pusher_chatkit import PusherChatKit
from pusher_chatkit.backends import RequestsBackend


class Point(object):
    def __init__(self, x, y):
      self.x = x
      self.y = y

def adapt_point(point):
     x = psycopg2.extensions.adapt(point.x).getquoted()
     y = psycopg2.extensions.adapt(point.y).getquoted()
     return psycopg2.extensions.AsIs("'(%s, %s)'" % (psycopg2.extensions.adapt(point.x), psycopg2.extensions.adapt(point.y)))


app = Flask(__name__)
app.config['DATABASE_URL'] = os.environ['DATABASE_URL']

chatkit = PusherChatKit(
    'v1:us1:2a275666-6587-43bb-badc-5ad580835adb',
    '46a04e29-2073-456c-aac9-6dc4c4c6d7f7:Oswqk13zzdrd3uZl0qEyEqOikot07IGUjZ29nLda+6Q=',
    RequestsBackend
)

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371* c
    return km

# RETRIEVE POST
@app.route('/getFeed', methods=['GET', 'POST'])
def getFeedPost():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM events INNER JOIN followings ON events.userid = followings.followingid WHERE followings.userid = %s"


            cursor.execute(sql, (data["userid"], ))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getPostFeed', methods=['GET', 'POST'])
def getPostFeed():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM post INNER JOIN followings ON post.userid = followings.followingid WHERE followings.userid = %s"


            cursor.execute(sql, (data["userid"], ))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getNearbyPost', methods=['GET', 'POST'])
def getNearbyPost():
    data = request.json



    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM post "


            cursor.execute(sql, (data["userid"], ))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getUserPost', methods=['GET', 'POST'])
def getUserPost():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM post WHERE userid = %s"
            cursor.execute(sql, (data["userID"], ))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getSavedEvents', methods=['GET', 'POST'])
def getSavedEvents():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM savedevents INNER JOIN events ON savedevents.eventid = events.eventid WHERE savedevents.userid = %s"
            cursor.execute(sql, (data["userid"], ))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

# RETRIEVE LOCAL POPULAR EVENTS
@app.route('/getStateEvents', methods=['GET', 'POST'])
def getStateEvents():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM events WHERE state = %s"


            cursor.execute(sql, (data["state"], ))

            result = cursor.fetchall()
            print(result)
            userLocation = (data["latitude"],data["longitude"])
            for event in result:
                eventLocation = (float(event["latitude"]),float(event["longitude"]))
                dist = geopy.distance.vincenty(userLocation, eventLocation)
                print(dist.miles)


            connection.commit()
    finally:
        connection.close()
    return jsonify(result)


@app.route('/updateEventImage', methods=['GET', 'POST'])
def updateEventImage():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:


            sql = "UPDATE events SET photos = %s WHERE eventid =  %s"
            cursor.execute(sql, (data["photos"], data["eventid"]))

            connection.commit()




    finally:
        connection.close()

    return "success"


@app.route('/createEvent', methods=['GET', 'POST'])
def createEvent():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:


            sql = "UPDATE events SET photos = %s WHERE eventid =  %s"
            cursor.execute(sql, (data["images"], data["eventid"]))

            connection.commit()




    finally:
        connection.close()

    return "success"




# USER MANAGEMENT

@app.route('/registerUser', methods=['GET', 'POST'])
def registerUser():
    connection = psycopg2.connect(app.config["DATABASE_URL"])


    data = request.json

    chatkit.create_user(data["userid"],data["name"])
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO users (userid, email, name, username,profileimageurl,radius) VALUES (%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["userid"], data["email"],data["name"],data["username"],data["profileimageurl"], data["radius"]))


            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/checkUsername', methods=['GET', 'POST'])
def checkUsername():
    data = request.json
    print(data)
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "select * FROM users WHERE username = %s LIMIT 1"
            print(sql)
            cursor.execute(sql, (data["username"],))
            result = cursor.fetchall()
            print(result)
            connection.commit()
    finally:
        connection.close()
    return jsonify(result)


@app.route('/updateUser', methods=['GET', 'POST'])
def updateUser():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            for key,value in data.items():
                if key == "userid":
                    continue
                elif key == "profileImageURL":
                    chatkit.update_user(data["userid"],data["name"],data["profileImageURL"])
                    print("updated %s" % (key.lower()))

                    sql = "UPDATE users SET {column} = %s WHERE userid =  %s".format(column=key)
                    cursor.execute(sql, (value, data["userid"]))

                    connection.commit()
                else:

                    print("updated %s" % (key.lower()))

                    sql = "UPDATE users SET {column} = %s WHERE userid =  %s".format(column=key)
                    cursor.execute(sql, (value,data["userid"]))

                    connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/getUserInfo', methods=['GET', 'POST'])
def getUserInfo():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM users WHERE userid = %s"

            cursor.execute(sql, (data["userID"],))
            result = cursor.fetchone()

            print(result)

            connection.commit()
    finally:
        connection.close()

    return jsonify(result)


# EDIT AND ADD POST

@app.route('/newEvent', methods=['GET', 'POST'])
def newEvent():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    print(data)
    psycopg2.extensions.register_adapter(Point, adapt_point)
    try:
        with connection.cursor() as cursor:


            latitude = float(data["latitude"])
            longitude = float(data["longitude"])
            print(latitude)


            sql = "INSERT INTO events (name,description,company,userid,eventid,starttimestamp,endtimestamp,endtime,latitude,longitude,address,location) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["name"], data["description"], data["company"], data["userid"], data["eventid"],
                                 data["starttimestamp"],data["endtimestamp"],data["endtime"],data["starttime"],
                                 data["latitude"],data["longitude"],data["address"],
                                 Point(data["longitude"],
                                       data["latitude"])))
            print(cursor)
            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/newPost', methods=['GET', 'POST'])
def newPost():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    print(data)
    psycopg2.extensions.register_adapter(Point, adapt_point)
    try:
        with connection.cursor() as cursor:




            sql = "INSERT INTO post (name,text,userid,postid,ismedia,postpictureurl,tags) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["name"],data["text"],data["userid"],data["postid"],data["ismedia"],data["postpictureurl"],
                                 data["tags"]))
            print(cursor)
            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/updatePost', methods=['GET', 'POST'])
def updatePost():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            for key in data:

                sql = "UPDATE post SET %s = %s WHERE eventid = %s"

                cursor.execute(sql, (data["key"],data["value"],data["eventid"]))

                connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/saveEvent', methods=['GET', 'POST'])
def saveEvent():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:

                sql = "INSERT INTO savedevents (userid, eventid) VALUES ('{userid}','{eventid}')".format(
                    userid=data["userid"], eventid=data["eventid"])

                cursor.execute(sql, (data["userid"], data["eventid"]))

                connection.commit()
    finally:
        connection.close()

    return "success"

# COMMENTS

@app.route('/getComments', methods=['GET', 'POST'])
def getComments():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM comments INNER JOIN users ON comments.userid = events.eventid WHERE eventid = %s"
            cursor.execute(sql, (data["userID"], ))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/postComment', methods=['GET', 'POST'])
def postComment():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "INSERT INTO comments (text,userid,eventid) VALUES (%s,%s,%s)"
            cursor.execute(sql, (data["text"],data["userid"], data["eventid"]))



            connection.commit()
    finally:
        connection.close()
    return "success"

# SEARCHING
@app.route('/searchUsers', methods=['GET', 'POST'])
def searchUsers():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM users WHERE userName ILIKE %s LIMIT 10"
            print(sql)
            cursor.execute(sql, (data["query"] + "%", ))
            result = cursor.fetchall()
            print(result)
            connection.commit()
    finally:
        connection.close()
    return jsonify(result)


# MESSAGING

@app.route('/generateChatKitToken', methods=['GET', 'POST'])
def generateChatKitToken():
    # The information sent from the app is a URL Query
    userid = request.args.get("userid")

    token = chatkit.authenticate_user(user_id=userid)
    print(token)
    return jsonify(token)


@app.route('/sendMessage', methods=['GET', 'POST'])
def sendMessage():
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    # Generate UUID server side instead of in database in case of database migration
    identifier = str(uuid.uuid1())


    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO messages (text,sendinguserid,receivinguserid,sendinguserprofileimageurl,sendingname,conversationid,messageid) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            updateConversationQuery = "UPDATE conversations SET lastupdated = current_timestamp,lastmessageid = %s  WHERE conversationid = %s"
            cursor.execute(sql, (data["text"], data["sendinguserid"], data["receivinguserid"],data["sendinguserprofileimageurl"],data["sendingname"],data["conversationid"],identifier))
            cursor.execute(updateConversationQuery,(identifier,data["conversationid"]))

            print(sql)
            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/createNewThread', methods=['GET', 'POST'])
def createNewThread():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    conversationIdentifier = str(uuid.uuid4())

    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO messages (text,sendinguserid,receivinguserid, conversationid) VALUES (%s,%s,%s,%s)"
            conversationQuery = "INSERT INTO conversations (conversationid, users, isgroupchat) VALUES (%s, %s, %s)"
            cursor.execute(sql, (data["text"], data["sendinguserid"], data["receivinguserid"],conversationIdentifier))
            cursor.execute(conversationQuery, (conversationIdentifier,data["users"],data["isgroupchat"]))
            print(sql)
            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/getMessages', methods=['GET', 'POST'])
def getMessages():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "select * from messages inner join users on users.userid = messages.sendinguserid where messages.conversationid = %s"
            cursor.execute(sql, (data["conversationid"], ))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getMessagePreviews', methods=['GET', 'POST'])
def getMessagePreviews():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = '''select * from users INNER join
(select lastmessageid,sendinguserid,isgroupchat from messages inner join conversations on messages.conversationid = conversations.conversationid  where %s = ANY(conversations.users) and %s != messages.sendinguserid limit 1) as query
on users.userid = query.sendinguserid
INNER JOIN
messages on messages.messageid = query.lastmessageid'''
            cursor.execute(sql, (data["userid"],data["userid"]))

            result = cursor.fetchall()


            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

# RELATIONSHOP MANAGEMENT
@app.route('/checkFollow', methods=['GET', 'POST'])
def checkFollow():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "select 1 FROM followings WHERE userID = '{userID}' AND followingID = '{otherUserID}'".format(
                userID=data["userID"], otherUserID=data["otherUserID"])
            print(sql)
            cursor.execute(sql)
            result = cursor.fetchall()
            print(result)
            connection.commit()
    finally:
        connection.close()
    return jsonify(result)



@app.route('/followUser', methods=['GET', 'POST'])
def followUser():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO followings (userID, followingID) VALUES ('{userID}','{followingID}')".format(userID=data["userID"], followingID=data["followingID"])
            print(sql)
            cursor.execute(sql)

            connection.commit()
    finally:
        connection.close()
    return "success"

@app.route('/unfollowUser', methods=['GET', 'POST'])
def unfollowUser():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM followings WHERE userID = '{userID}' AND followingID = '{followingID}'".format(userID=data["userID"], followingID=data["followingID"])
            print(sql)
            cursor.execute(sql)

            connection.commit()
    finally:
        connection.close()
    return "success"

@app.route('/getFollowersCount', methods=['GET', 'POST'])
def getFollowersCount():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT COUNT(*) FROM followings WHERE followings.followingid = %s"
            print(sql)
            cursor.execute(sql, (data["userid"],))
            result = cursor.fetchall()

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getFollowingCount', methods=['GET', 'POST'])
def getFollowingCount():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT COUNT(*) FROM followings WHERE followings.userid = %s"
            print(sql)
            cursor.execute(sql, (data["userid"],))
            result = cursor.fetchall()

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getSubscribers', methods=['GET', 'POST'])
def getSubscribers():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM users INNER JOIN followings ON users.userid = followings.followingid WHERE followings.followingid = %s"
            print(sql)
            cursor.execute(sql, (data["userid"],))
            result = cursor.fetchall()

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/checkLobbyStatus', methods=['GET', 'POST'])
def checkLobbyStatus():
    data = request.json
    print(data)
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "select * FROM lobbies WHERE cityname = %s AND state = %s LIMIT 1"
            print(sql)
            cursor.execute(sql, (data["name"],data["state"]))
            result = cursor.fetchall()
            print(result)
            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/createNewChat', methods=['GET', 'POST'])
def createNewChat():
    connection = psycopg2.connect(app.config["DATABASE_URL"])



    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO lobbies (cityname,id,state) VALUES (%s,%s,%s)"

            cursor.execute(sql, (data["name"], data["id"], data["state"]))

            print(sql)
            connection.commit()
    finally:
        connection.close()

    return "success"


if __name__ == '__main__':
    app.run()
