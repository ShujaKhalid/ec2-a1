from flask import render_template, redirect, url_for, request, session, g
from app import webapp
from wand.image import Image
from wand.display import display
import sys

import boto3

import mysql.connector

import re

from app.config import db_config


def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'])


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@webapp.route('/s3_upload/<id>', methods=['GET'])
# Display details about a specific bucket.
def s3_view(id):
    s3 = boto3.resource('s3')

    bucket = s3.Bucket(id)

    for key in bucket.objects.all():
        k = key

    keys = bucket.objects.all()
    userId = session['username']

    cnx = get_db()
    cursor = cnx.cursor()
    url_s3 = 'http://s3.amazonaws.com/'
    bucket = str(str(id))

    query_thumb = "SELECT DISTINCT key1 FROM images WHERE userId = %s"
    cursor.execute(query_thumb, (userId,))

    return render_template("s3upload/view.html", title="S3 Bucket Contents", id=id, keys=keys, userId=userId, cursor=cursor, url_s3=url_s3)


@webapp.route('/s3_upload/upload/<id>', methods=['GET', 'POST'])
# Upload a new file to an existing bucket
def s3_upload(id):
    key1 = ''
    key2 = ''
    key3 = ''
    key4 = ''
    # check if the post request has the file part
    if 'new_file' not in request.files:
        return redirect(url_for('s3_view', id=id))

    new_file = request.files['new_file']

    # if user does not select file, browser also
    # submit a empty part without filename
    if new_file.filename == '':
        return redirect(url_for('s3_view', id=id))

    # After the checks are complete, proceed to
    # compute the various transformations of the uploaded image
    # using Wand
    with Image(blob=new_file) as image1:
        with image1.clone() as transformation1:
            transformation1.rotate(90)
            filename1 = 'im1_' + str(new_file.filename)
            transformation1.save(filename=filename1)
        with image1.clone() as transformation2:
            transformation2.rotate(180)
            filename2 = 'im2_' + str(new_file.filename)
            transformation2.save(filename=filename2)
        with image1.clone() as transformation3:
            transformation3.rotate(270)
            filename3 = 'im3_' + str(new_file.filename)
            transformation3.save(filename=filename3)
        with image1.clone() as transformation4:
            transformation4.rotate(0)
            filename4 = 'im4_' + str(new_file.filename)
            transformation4.save(filename=filename4)

    s3 = boto3.client('s3')

    # The image along with 3 pre-computed transformations will
    # be uploaded to S3
    # s3.upload_file(new_file, id, new_file.filename)
    s3.upload_file(str(filename1), str(id), str(filename1))
    s3.upload_file(str(filename2), str(id), str(filename2))
    s3.upload_file(str(filename3), str(id), str(filename3))
    s3.upload_file(str(filename4), str(id), str(filename4))

    key1 = filename4
    key2 = filename1
    key3 = filename2
    key4 = filename3

    # Find the S3 keys for each of the images and upload them to
    # the SQL Database
    cnx = get_db()
    cursor = cnx.cursor()
    userId = session['username']

    query = ''' INSERT INTO images (userId,key1,key2,key3,key4)
                       VALUES (%s,%s,%s,%s,%s)
    '''

    cursor.execute(query, (userId, key1, key2, key3, key4))
    cnx.commit()

    cnx = get_db()
    cursor = cnx.cursor()
    url_s3 = 'http://s3.amazonaws.com/'
    id = str(str(id))

    query_thumb = "SELECT DISTINCT key1 FROM images WHERE userId = %s"
    cursor.execute(query_thumb, (userId,))

    s3 = boto3.resource('s3')

    bucket = s3.Bucket(id)

    for key in bucket.objects.all():
        k = key

    keys = bucket.objects.all()
    userId = session['username']

    return render_template("s3upload/view.html", title="S3 Bucket Contents", id=id, keys=keys, userId=userId, cursor=cursor, url_s3=url_s3)


@webapp.route('/detailed_view/<string:buckId>/<string:id>', methods=['GET'])
# Detailed View of the thumbnails
def detailed_view(buckId, id):
    # buckId = request.args.get("buckId")
    # url_s3 = request.args.get("id")
    url_s3 = 'http://s3.amazonaws.com/'
    cnx = get_db()
    cursor = cnx.cursor()
    userId = session['username']
    imId = id
    # query_thumb = "SELECT DISTINCT * FROM images WHERE userId = %s AND key1 = %s"
    query_thumb = "SELECT DISTINCT key1, key2, key3, key4 FROM images WHERE userId = %s AND key1 = %s"
    cursor.execute(query_thumb, (userId, imId))
    return render_template("display_details.html", cursor=cursor, bucket=buckId, url_s3=url_s3)


@webapp.route('/s3_view_test/<id>', methods=['GET'])
# Display details about a specific bucket.
def s3_view_test(id, uploadedfile):
    s3 = boto3.resource('s3')

    bucket = s3.Bucket(id)

    for key in bucket.objects.all():
        k = key

    keys = bucket.objects.all()
    userId = session['username']

    cnx = get_db()
    cursor = cnx.cursor()
    url_s3 = 'http://s3.amazonaws.com/'
    bucket = str(str(id))

    query_thumb = "SELECT DISTINCT key1 FROM images WHERE userId = %s"
    cursor.execute(query_thumb, (userId,))

    return render_template("s3upload/view.html", title="S3 Bucket Contents", id=id, keys=keys, userId=userId, cursor=cursor, url_s3=url_s3)


@webapp.route('/s3_upload_test/', methods=['GET','POST'])
# Upload a new file to an existing bucket
def s3_upload_test():
    key1 = ''
    key2 = ''
    key3 = ''
    key4 = ''

    new_file = request.files['new_file']
    # new_file = session['uploadedfile']
    # uploadedfile = session['uploadedfile']
    # id = session['name']
    buckId = session['name']

    # After the checks are complete, proceed to
    # compute the various transformations of the uploaded image
    # using Wand
    with Image(blob=new_file) as image1:
        with image1.clone() as transformation1:
            transformation1.rotate(90)
            filename1 = 'im1_' + str(new_file.filename)
            transformation1.save(filename=filename1)
        with image1.clone() as transformation2:
            transformation2.rotate(180)
            filename2 = 'im2_' + str(new_file.filename)
            transformation2.save(filename=filename2)
        with image1.clone() as transformation3:
            transformation3.rotate(270)
            filename3 = 'im3_' + str(new_file.filename)
            transformation3.save(filename=filename3)
        with image1.clone() as transformation4:
            transformation4.rotate(0)
            filename4 = '' + str(new_file.filename)
            transformation4.save(filename=filename4)

    s3 = boto3.client('s3')

    # The image along with 3 pre-computed transformations will
    # be uploaded to S3
    # s3.upload_file(new_file, buckId, new_file.filename)
    s3.upload_file(str(filename1), str(buckId), str(filename1))
    s3.upload_file(str(filename2), str(buckId), str(filename2))
    s3.upload_file(str(filename3), str(buckId), str(filename3))
    s3.upload_file(str(filename4), str(buckId), str(filename4))

    key1 = filename4
    key2 = filename1
    key3 = filename2
    key4 = filename3

    # Find the S3 keys for each of the images and upload them to
    # the SQL Database
    cnx = get_db()
    cursor = cnx.cursor()
    userId = session['username']

    query = ''' INSERT INTO images (userId,key1,key2,key3,key4)
                       VALUES (%s,%s,%s,%s,%s)
    '''

    cursor.execute(query, (userId, key1, key2, key3, key4))
    cnx.commit()

    s3 = boto3.resource('s3')

    bucket = s3.Bucket(id)

    for key in bucket.objects.all():
        k = key

    keys = bucket.objects.all()
    userId = session['username']

    url_s3 = 'http://s3.amazonaws.com/'
    cnx1 = get_db()
    cursor1 = cnx1.cursor()
    imId = uploadedfile
    # query_thumb = "SELECT DISTINCT * FROM images WHERE userId = %s AND key1 = %s"
    query_thumb = "SELECT DISTINCT key1, key2, key3, key4 FROM images WHERE userId = %s AND key1 = %s"
    cursor1.execute(query_thumb, (userId, imId))
    


    return render_template("display_details.html", cursor=cursor1, bucket=buckId, url_s3=url_s3)
