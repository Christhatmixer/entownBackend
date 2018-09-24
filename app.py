from flask import Flask, render_template, request, jsonify

import psycopg2
import psycopg2.extras
import sys
import json
import requests
from urllib.parse import urlparse
import os






app = Flask(__name__)
app.config['DATABASE_URL'] = os.environ['DATABASE_URL']

# RETRIEVE POST
@app.route('/getFeed', methods=['GET', 'POST'])
def getFeedPost():
    data = request.json

    connection = psycopg2.connect(app.config["DATABASE_URL"])
    dict_cur = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with dict_cur as cursor:
            sql = "SELECT * FROM post INNER JOIN followings ON post.userid = followings.followingid WHERE followings.userid = %s"


            cursor.execute(sql, (data["userID"], ))

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

@app.route('/registerUser', methods=['GET', 'POST'])
def registerUser():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO users (userid, email, name,username,profileimageurl) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["userid"], data["email"],data["name"],data["username"],data["profileimageurl"]))

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

                sql = "INSERT INTO users ({column}) VALUES (%s)".format(column=key)
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

@app.route('/newPost', methods=['GET', 'POST'])
def newPost():
    connection = psycopg2.connect(app.config["DATABASE_URL"])

    data = request.json
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO post (name,description,category,userid,eventid) VALUES (%s,%s,%s,%s,%s)"
            cursor.execute(sql, (data["name"], data["description"], data["category"], data["userid"], data["eventid"]))
            print(sql)
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

if __name__ == '__main__':
    app.run()
