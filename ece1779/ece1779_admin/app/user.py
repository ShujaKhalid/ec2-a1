from flask import render_template, redirect, url_for, request, g
from app import webapp

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


@webapp.route('/user', methods=['GET'])
# Display an HTML list of all students.
def user_list():
    cnx = get_db()

    cursor = cnx.cursor()

    query = "SELECT * FROM users"

    cursor.execute(query)

    return render_template("user/list.html", title="User List", cursor=cursor)


@webapp.route('/user/create', methods=['GET'])
# Display an empty HTML form that allows users to define new student.
def user_create():
    return render_template("user/new.html", title="New user")


@webapp.route('/user/create', methods=['POST'])
# Create a new user and save them in the database.
def user_create_save():
    login = request.form.get('login', "")
    password = request.form.get('password', "")
    password_reenter = request.form.get('password_reenter', "")

    error = False

    if login == "" or password == "":
        error = True
        error_msg = "Error: All fields are required!"

    if password != password_reenter:
        error = True
        error_msg = "Entered passwords do not match"

    if error:
        return render_template("user/new.html", title="New user", error_msg=error_msg,
                               login=login, password=password)

    cnx = get_db()
    cursor = cnx.cursor()

    query = ''' INSERT INTO users (login,password)
                       VALUES (%s,%s)
    '''

    cursor.execute(query, (login, password))
    cnx.commit()

    # return redirect(url_for('user_list'))
    return redirect(url_for('login'))


@webapp.route('/user/delete/<int:id>', methods=['POST'])
# Deletes the specified user from the database.
def user_delete(id):
    cnx = get_db()
    cursor = cnx.cursor()

    query = "DELETE FROM users WHERE id = %s"

    cursor.execute(query, (id,))
    cnx.commit()

    return redirect(url_for('user_list'))
