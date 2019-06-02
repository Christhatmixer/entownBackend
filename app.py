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

@app.route('/registerUser', methods=['GET', 'POST'])
def registerUser():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO users (userid, email, name, username, radius) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["userid"], data["email"],data["name"],data["username"], data["radius"]))

            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/updateUser', methods=['GET', 'POST'])
def updateUser():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    try:
        with connection.cursor() as cursor:
            for key in data:

                sql = "UPDATE users ({column}) VALUES (%s)".format(column=key)
                cursor.execute(sql, (data[key],))

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


            sql = "INSERT INTO events (name,description,company,userid,eventid,datenum,endtime,latitude,longitude,address,photos,location) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["name"], data["description"], data["company"], data["userid"], data["eventid"],data["datenum"],data["endtime"],
                                 data["latitude"],data["longitude"],data["address"],
                                 data["photos"],
                                 Point(longitude,
                                       latitude)))
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

@app.route('/sendMessage', methods=['GET', 'POST'])
def sendMessage():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO messages (text,sendinguserid,receivinguserid, conversationid) VALUES (%s,%s,%s,%s)"
            updateConversationQuery = "UPDATE conversations SET lastupdated = current_timestamp WHERE conversationid = %s"
            cursor.execute(sql, (data["text"], data["sendinguserid"], data["receivinguserid"],data["conversationid"]))
            cursor.execute(updateConversationQuery,(data["conversationid"],))

            print(sql)
            connection.commit()
    finally:
        connection.close()

    return "success"

@app.route('/createNewThread', methods=['GET', 'POST'])
def createNewThread():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO messages (text,sendinguserid,receivinguserid, conversationid) VALUES (%s,%s,%s,%s)"
            conversationQuery = "INSERT INTO conversations (conversationid, users, isgroupchat) VALUES (%s, %s, %s)"
            cursor.execute(sql, (data["text"], data["sendinguserid"], data["receivinguserid"],data["conversationid"]))
            cursor.execute(conversationQuery, (data["conversationid"],data["users"],data["isgroupchat"]))
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
            sql = "select * from messages inner join users on users.userid = messages.sendinguserid where messages.conversationid = 5s"
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
            sql = "select distinct on (messages.conversationid) * from messages " \
                  "inner join conversations on messages.conversationid = conversations.conversationid  where %s = ANY(conversations.users)"
            cursor.execute(sql, (data["userid"],))

            result = cursor.fetchall()
            print(result)

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


if __name__ == '__main__':
    app.run()
