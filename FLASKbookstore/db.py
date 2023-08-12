import psycopg2
from psycopg2 import extras
from flask import current_app, g
from flask import Flask
from flask.cli import with_appcontext
import click
# Connect to your postgres DB
def connect_db(): 
    if 'conn' not in g:
        try:
            g.conn = psycopg2.connect(
        cursor_factory = psycopg2.extras.DictCursor,
        database='flask_db', 
        user='postgres',
        password='Lr31415926', 
        host='127.0.0.1', 
        port="5432")
            
        except(Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL", error)
    
    return g.conn
#删除数据库
def drop_db():
    conn = psycopg2.connect(
        database='flask_db', 
        user='postgres',
        password='Lr31415926', 
        host='127.0.0.1', 
        port="5432"
    )
    cursor = conn.cursor()
    cursor.execute("DROP DATABASE IF EXISTS flask_db")
    conn.commit()
    cursor.close()
    conn.close()

#创建数据库，如果数据库不在pg_database中
def create_db():
    conn = psycopg2.connect(
        database='flask_db', 
        user='postgres',
        password='Lr31415926', 
        host='127.0.0.1', 
        port="5432"
    )
    conn.autocommit = True # 自动提交事务，不需要回滚，只在函数内生效
    cursor = conn.cursor()
    cursor.execute("SELECT u.datname FROM pg_catalog.pg_database u WHERE u.datname='flask_db'")
    if cursor.fetchone() == None :
        cursor.execute("CREATE DATABASE flask_db")
    conn.autocommit = False
    cursor.close()
    conn.close()

def close_db(e=None): # 从 Flask 应用上下文的 g 对象中取出键名为 'conn' 的值，并从 g 对象中删掉
    conn = g.pop('conn',None)
    if conn is not None:
        conn.commit()
        conn.close()


# #def init_db():
#     create_db()
#     conn = connect_db()
#     with current_app.open_resource('schema.sql') as f:
#         query = f.read().decode('utf8')
#         cursor = conn.cursor()
#         cursor.execute(query)
#         cursor.close()
#         conn.commit()

def init_db():
    create_db()
    conn = connect_db()
    with current_app.open_resource('schema.sql') as f:
        conn.cursor().execute(f.read().decode('utf8'))


conn = psycopg2.connect(
        database='flask_db', 
        user='postgres',
        password='Lr31415926', 
        host='127.0.0.1', 
        port="5432"
    )

@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Database Initialized!')

    
def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

