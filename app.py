from flask import Flask, render_template, request, jsonify

import psycopg2
import psycopg2.extras
import psycopg2.extensions
import logging
import sys
import json
import requests
from urllib.parse import urlparse
from PushySDK import Pushy
import os
import geopy
from geopy.distance import geodesic
from math import radians, cos, sin, asin, sqrt
import uuid
from pusher_chatkit import PusherChatKit
from pusher_chatkit.backends import RequestsBackend

class LoggingCursor(psycopg2.extensions.cursor):
    def execute(self, sql, args=None):
        logger = logging.getLogger('sql_debug')
        logger.info(self.mogrify(sql, args))

        try:
            psycopg2.extensions.cursor.execute(self, sql, args)
        except Exception as exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))
            raise

class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y


def adapt_point(point):
    x = psycopg2.extensions.adapt(point.x).getquoted()
    y = psycopg2.extensions.adapt(point.y).getquoted()
    return psycopg2.extensions.AsIs("'(%s, %s)'" % (x,y))

psycopg2.extensions.register_adapter(Point, adapt_point)


app = Flask(__name__)
app.config['DATABASE_URL'] = os.environ['DATABASE_URL']

chatkit = PusherChatKit(
    'v1:us1:2a275666-6587-43bb-badc-5ad580835adb',
    '46a04e29-2073-456c-aac9-6dc4c4c6d7f7:Oswqk13zzdrd3uZl0qEyEqOikot07IGUjZ29nLda+6Q=',
    RequestsBackend
)
pushy=Pushy('2917b380f7d027b7659997a46e420c51c9eed6054e563f0180c5aa8181e24497')

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
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371 * c
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

            cursor.execute(sql, (data["userid"],))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getEventFeed', methods=['GET', 'POST'])
def getEventFeed():
    data = request.json
    currenttimestamp = float(data["currenttimestamp"])

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM events INNER JOIN followings ON events.userid = followings.followingid WHERE followings.userid = %s AND CAST(events.starttimestamp as decimal) >= %s"

            cursor.execute(sql, (data["userid"],currenttimestamp))

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
            sql = '''SELECT post.*,exists(select 1 from likes  where likes.postId = post.postid and likes.userid = %s limit 1) as liked FROM post 
            INNER JOIN followings ON post.userid = followings.followingid 
            INNER JOIN users on post.userid = users.userid 
            WHERE followings.userid = %s
            GROUP BY post.userid,post.ismedia,post.text,post.postid,post.photos,
            post.tags,post.datecreated,post.geom,post.longitude,post.latitude
            '''

            cursor.execute(sql, (data["userid"],data["userid"]))

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
            radius = float(data["radius"])
            latitude = float(data["latitude"])
            longitude = float(data["longitude"])

            sql = "SELECT * FROM post WHERE ST_Distance_Sphere(post.geom, ST_MakePoint(%s,%s)) <= %s"


            cursor.execute(sql, (longitude,latitude,radius))

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
            sql = '''
            SELECT distinct post.*, COUNT(likes.postid) AS like_count,COUNT(comments.postid) AS comment_count,users.devicetoken AS devicetoken
FROM post
    LEFT JOIN likes ON post.postid = likes.postid
    LEFT JOIN "comments" ON post.postid = "comments".postid
    INNER JOIN users ON post.userid = users.userid
    
    where post.userid = %s
GROUP BY post.postid,post.userid,post."text",post.ismedia,post.photos,post.tags,
post.datecreated,post.geom,devicetoken
            '''
            cursor.execute(sql, (data["userid"],))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getUserEvents', methods=['GET', 'POST'])
def getUserEvents():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = '''
                        SELECT distinct events.*, COUNT(likes.postid) AS like_count,COUNT(comments.postid) AS comment_count
            FROM events
                LEFT JOIN likes ON events.eventid = likes.postid
                LEFT JOIN "comments" ON events.eventid = "comments".postid
                where events.userid = %s
            GROUP BY events.eventid,events.userid,events.photos,
            events.datecreated,events.geom,events.longitude,events.latitude,events.eventname,events.city,events.company,
            events.starttime,events.endtime,events.eventlink,events.country,events.address,events.state,events.description,
            events.datenum,events.starttimestamp,events.endtimestamp
            '''
            cursor.execute(sql, (data["userID"],))

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
            cursor.execute(sql, (data["userid"],))

            result = cursor.fetchall()
            print(result)

            connection.commit()
    finally:
        connection.close()
    return jsonify(result)

@app.route('/getNearbyEvents', methods=['GET', 'POST'])
def getNearbyEvents():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM events WHERE ST_DWithin(geom, ST_MakePoint(%s,%s)::geography, %s);"
            cursor.execute(sql, (data["longitude"],data["latitude"],data["radius"]))

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

            cursor.execute(sql, (data["state"],))

            result = cursor.fetchall()
            print(result)
            userLocation = (data["latitude"], data["longitude"])
            for event in result:
                eventLocation = (float(event["latitude"]), float(event["longitude"]))
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

@app.route('/updatePostImage', methods=['GET', 'POST'])
def updatePostImage():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:

            sql = "UPDATE post SET photos = %s, ismedia = %s WHERE postid =  %s"
            cursor.execute(sql, (data["photos"],data["ismedia"], data["postid"]))

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

    chatkit.create_user(data["userid"], data["name"])
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO users (userid, email, name, username,profileimageurl,radius) VALUES (%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql, (
            data["userid"], data["email"], data["name"], data["username"], data["profileimageurl"], data["radius"]))

            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/registerToken', methods=['GET', 'POST'])
def registerToken():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json


    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO users (userid, devicetoken) VALUES (%s,%s)"
            cursor.execute(sql, (
            data["userid"], data["devicetoken"]))

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
            for key, value in data.items():
                if key == "userid":
                    continue
                elif key == "profileImageURL":
                    chatkit.update_user(data["userid"], data["name"], data["profileImageURL"])
                    print("updated %s" % (key.lower()))

                    sql = "UPDATE users SET {column} = %s WHERE userid =  %s".format(column=key)
                    cursor.execute(sql, (value, data["userid"]))

                    connection.commit()
                else:

                    print("updated %s" % (key.lower()))

                    sql = "UPDATE users SET {column} = %s WHERE userid =  %s".format(column=key)
                    cursor.execute(sql, (value, data["userid"]))

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

    extensionCur = connection.cursor(cursor_factory=LoggingCursor)

    try:
        with extensionCur as cursor:

            latitude = float(data["latitude"])
            longitude = float(data["longitude"])
            print(latitude)
            location = Point(longitude, latitude)
            print(location.x)
            locationTuple = '(%s,%s)' % (longitude,latitude)
            geom = "ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)"
            updateGeom = "UPDATE events SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) WHERE events.eventid = %s"

            sql = "INSERT INTO events (eventname,pricedescription,company,eventlink,userid,eventid,starttimestamp,endtimestamp,endtime,starttime,latitude,longitude,address,location) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["eventname"],data["price"] ,data["description"], data["company"], data["eventlink"],data["userid"], data["eventid"],
                                 data["starttimestamp"], data["endtimestamp"], data["endtime"], data["starttime"],
                                 data["latitude"], data["longitude"], data["address"],
                                 locationTuple))
            cursor.execute(updateGeom, (data["eventid"],))
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


            #locationTuple = '(%s,%s)' % (longitude, latitude)
            #updateGeom = "UPDATE post SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) WHERE post.postid = %s"

            sql = "INSERT INTO post (text,userid,postid,ismedia) VALUES (%s,%s,%s,%s)"
            cursor.execute(sql, (
            data["text"], data["userid"], data["postid"], data["ismedia"]))
            #cursor.execute(updateGeom, (data["postid"],))
            print(cursor)
            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/likePost', methods=['GET', 'POST'])
def likePost():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    print(data)
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        with dict_cur as cursor:

            sql = "select post.postid,post.ismedia,post.photos,post.text,post.datecreated,post.userid, count(likedpost.postid) as numberoflikes from post left join likedpost on post.postid = likedpost.postid group by post.postid,post.ismedia,post.photos,post.text,post.datecreated,post.userid"

            cursor.execute(sql, (data["userid"], data["postid"]))

            print(cursor)
            connection.commit()


            data = {'message': "%s liked your post." % data["username"]}
            if data["selfdevicetoken"] == data["otherdevicetoken"]:
                pass
            else:
                pushy.push(data["otherdevicetoken"], data)

    finally:


        connection.close()

    return "success"

@app.route('/unlikePost', methods=['GET', 'POST'])
def unlikePost():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    print(data)
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        with dict_cur as cursor:

            sql = "DELETE FROM likes WHERE userid = %s and postid = %s"

            cursor.execute(sql, (data["userid"], data["postid"]))

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
                sql = "UPDATE post SET %s = %s WHERE postid = %s"

                cursor.execute(sql, (data["key"], data["value"], data["postid"]))

                connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/updateEvent', methods=['GET', 'POST'])
def updateEvent():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            for key in data:
                sql = "UPDATE events SET %s = %s WHERE eventid = %s"

                cursor.execute(sql, (data["key"], data["value"], data["eventid"]))

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
            sql = '''SELECT comments.*,COUNT(likes.postid) AS like_count,exists(select 1 from likes  where likes.postId = post.postid and likes.userid = %s limit 1) as liked FROM comments 
            LEFT JOIN likes ON comments.commentid = likes.postid
            WHERE comments.postid = %s
            GROUP BY comments.postid,comments.text,comments.commentid,comments.datecreated,comments.userid
            '''
            cursor.execute(sql, (data["postid"],data["userid"],data["postid"]))

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
            sql = "INSERT INTO comments (text,userid,postid,commentid) VALUES (%s,%s,%s,%s)"
            cursor.execute(sql, (data["text"], data["userid"], data["id"],data["commentid"]))

            connection.commit()
    finally:
        connection.close()
    return "success"

@app.route('/likeComment', methods=['GET', 'POST'])
def likeComment():
    data = request.json
    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "INSERT INTO likes (postid,userid,type) VALUES (%s,%s,%s)"
            cursor.execute(sql, (data["id"], data["userid"], "comment"))

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
            cursor.execute(sql, (data["query"] + "%",))
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
            cursor.execute(sql, (
            data["text"], data["sendinguserid"], data["receivinguserid"], data["sendinguserprofileimageurl"],
            data["sendingname"], data["conversationid"], identifier))
            cursor.execute(updateConversationQuery, (identifier, data["conversationid"]))

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
            cursor.execute(sql, (data["text"], data["sendinguserid"], data["receivinguserid"], conversationIdentifier))
            cursor.execute(conversationQuery, (conversationIdentifier, data["users"], data["isgroupchat"]))
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
            cursor.execute(sql, (data["conversationid"],))

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
            cursor.execute(sql, (data["userid"], data["userid"]))

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
            sql = "INSERT INTO followings (userID, followingID) VALUES ('{userID}','{followingID}')".format(
                userID=data["userID"], followingID=data["followingID"])
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
            sql = "DELETE FROM followings WHERE userID = '{userID}' AND followingID = '{followingID}'".format(
                userID=data["userID"], followingID=data["followingID"])
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

@app.route('/getLikeCount', methods=['GET', 'POST'])
def getLikeCount():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT COUNT(*) FROM liked_post WHERE followings.userid = %s"
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
            cursor.execute(sql, (data["name"], data["state"]))
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
