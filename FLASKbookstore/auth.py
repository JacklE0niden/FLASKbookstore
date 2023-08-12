from flask import Flask, render_template, request, redirect, url_for, flash, g, session
from flask import Blueprint

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import abort
from db import connect_db
import functools
# 数据库连接信息
# DATABASE = 'flask_db'
# DB_USER = 'username'
# DB_PASSWORD = 'Lr31415926'
# DB_HOST = 'localhost'
# DB_PORT = '5432'

bp = Blueprint('auth', __name__, url_prefix='/auth')

def login_required(view):
    @functools.wraps(view) # 装饰器
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.admin_login'))

        return view(**kwargs)

    return wrapped_view

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.is_admin = session.get('is_admin')
    g.is_Super = session.get('is_Super')

    if user_id is None:
        g.user = None
    else:
        cur = connect_db().cursor()
        if(g.is_admin):
            cur.execute(
                'SELECT * FROM administrator WHERE aid = %s', (user_id,)
            )

        else:
            cur.execute(
                'SELECT * FROM reader WHERE rid = %s', (user_id,)
            )
        g.user = cur.fetchone()

@bp.route('/reader_register', methods=('GET', 'POST'))
def reader_register():
    #未输入用户名和密码
    #用户名已被占用
    #成功，跳转login
    conn = connect_db()

    if request.method == 'POST':
        # 从表单获取用户名和密码
        username = request.form.get('username')
        password = request.form.get('password')
        check_password = request.form.get('check_password')
        cur = conn.cursor()
        error = None

        if username is None:
            error = ("请输入用户名")
        elif password is None:
            error = ("请输入密码")
        # 检查用户名是否已被占用
        else:
            cur.execute("SELECT * FROM reader WHERE rname = %s ",(username,)) 
            if cur.fetchone() is not None:
                error = ("用户名已被占用，请重新设置用户名")
            elif check_password != password:
                error = ('密码确认错误')
        # 创建新reader到数据库
        if error is None:
            cur.execute(
                'INSERT INTO reader (rname, password) VALUES (%s, %s)',
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash('注册成功，请登录')
            # 重定向到登录页面
            return redirect(url_for('auth.reader_login'))

        flash(error)

    return render_template("auth/reader_register.html")

@bp.route('/admin_register', methods=('GET', 'POST'))
def admin_register():
    conn = connect_db()
    if not g.is_Super:
        flash("无权限")
        abort(403)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        check_password = request.form.get('check_password')
        realname = request.form.get('realname')
        workno = request.form.get('workno')
        gender = request.form.get('gender')
        age = request.form.get('age')
        cur = conn.cursor()
        error = None 

        if username is None:
            error = ("请输入用户名")
        elif password is None:
            error = ("请输入密码")
        # 检查用户名是否已被占用
        else:
            cur.execute("SELECT * FROM administrator WHERE aname = %s ",(username,)) 
            if cur.fetchone() is not None:
                error = ("用户名已被占用，请重新设置用户名")
            elif check_password != password:
                error = ('密码确认错误')
         # 创建新reader到数据库
        if error is None:
            cur.execute(
                'INSERT INTO administrator (aname, password,realname,workno, gender, age) VALUES (%s, %s, %s, %s, %s, %s)',
                (username, generate_password_hash(password), realname, workno, gender, age)
            )
            conn.commit()
            flash('注册成功')
            return redirect(url_for('auth.admin_list'))

        flash(error)

    return render_template('auth/admin_register.html')

@bp.route('/reader_login', methods=('GET', 'POST'))
def reader_login():
    conn = connect_db()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        cur = conn.cursor()
        error = None
        if username is None:
            error = ("请输入用户名")
        elif password is None:
            error = ("请输入密码")
        # 检查用户名密码是否正确
        else:
            cur.execute("SELECT * FROM reader WHERE rname = %s",(username,)) # 这种传值方式可以防止sql注入的风险  
            user = cur.fetchone()
            if user is None:
                error = '用户名错误'
            elif not check_password_hash(user['password'], password):
                error = '密码错误'

            if error is None:
                session.clear()
                session['user_id'] = user['rid'] #user_id用来表示当前会话的对象
                session['is_admin'] = False
                session['is_Super'] = False
                return redirect(url_for('index'))

        flash(error)

    return render_template('auth/reader_login.html')

@bp.route('/admin_login', methods=('GET', 'POST'))
def admin_login():
    #未输入用户名和密码
    #用户名错误
    #密码错误
    conn = connect_db()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        cur = conn.cursor()
        error = None
        if username is None:
            error = ("请输入用户名")
        elif password is None:
            error = ("请输入密码")
        # 检查用户名密码是否正确
        else:
            cur.execute("SELECT * FROM administrator WHERE aname = %s",(username,)) # 这种传值方式可以防止sql注入的风险  
            user = cur.fetchone()

            if user is None:
                error = '用户名错误'
            elif not check_password_hash(user['password'], password):
                error = '密码错误'

            if error is None:
                session.clear()
                session['user_id'] = user['aid'] #user_id用来表示当前会话的对象
                session['is_admin'] = True
                session['is_Super'] = user['issuper']

                return redirect(url_for('index'))
            
        flash(error)

    return render_template('auth/admin_login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@bp.route('/admin_list', methods=('GET', 'POST'))
def admin_list():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    conn = connect_db()
    if not g.is_Super:
        flash("无权限")
        abort(403)

    cur = conn.cursor()
    cur.execute('SELECT * FROM administrator ORDER BY aid')
    admins = cur.fetchall()

    return render_template('auth/admin_list.html', admins=admins)

@bp.route('/reader_list', methods=('GET', 'POST'))
def reader_list():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    conn = connect_db()
    if not g.is_admin:
        flash("无权限")
        abort(403)

    cur = conn.cursor()
    cur.execute('SELECT * FROM reader ORDER BY rid')
    rds = cur.fetchall()

    return render_template('auth/reader_list.html', rds=rds)

@bp.route('/<int:id>/reader_update', methods=('GET', 'POST'))
@login_required
def reader_update(id):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reader WHERE rid = %s", (id,))
    rd = cur.fetchone()

    if rd is None:
        abort(404, "账户ID {0} 不存在.".format(id))

    #password TEXT NOT NULL,
    #gender TEXT,
    #age INTEGER

    if request.method == 'POST':
        username = request.form.get('username')
        gender = request.form.get('gender')
        age = request.form.get('age')
        error = None

        if not username:
            error = '请输入用户名'
        elif username != rd['rname']:
            cur.execute("SELECT * FROM reader WHERE username = %s " ,(username, ))
            if cur.fetchone() is not None:
                error = '用户名 {} 已被注册'.format(username)
    
        if error is not None:
            flash(error)
            return redirect(url_for('index'))
    
        else:
            cur.execute('UPDATE reader'
                        ' SET rname = %s, gender = %s, age = %s'
                        ' WHERE rid = %s',
                        (username, gender, age, id))
    
        conn.commit()
        return redirect(url_for('index'))
    
    return render_template('auth/reader_update.html',rd = rd)

@bp.route('/<int:id>/admin_update', methods=('GET', 'POST'))
@login_required
def admin_update(id):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM administrator WHERE aid = %s", (id,))

    admin = cur.fetchone()
    if admin is None:
        abort(404, "账户ID {0} 不存在.".format(id))
        #aname TEXT NOT NULL,
        #password TEXT NOT NULL,
        #realname TEXT,
        #gender TEXT,
        #age INTEGER,
        #isSuper BOOLEAN NOT NULL DEFAULT false 


    if request.method == 'POST':
        username = request.form.get('username')
        realname = request.form.get('realname')
        workno = request.form.get('workno')
        gender = request.form.get('gender')
        age = request.form.get('age')
        error = None

        if username is None:
            error = '请输入用户名'
        elif username != admin['aname']:
            cur.execute("SELECT * FROM administrator WHERE aname = %s ", (username,))
            if cur.fetchone() is not None:
                error = '用户名 {} 已被注册'.format(username)

        if error is not None:
            flash(error)
            return redirect(url_for('index'))
    
        else:
            cur.execute('UPDATE administrator'
                            ' SET aname = %s, realname = %s,workno = %s, gender = %s, age = %s'
                            ' WHERE aid = %s',
                            (username, realname, workno, gender, age, id))
    
        conn.commit()
        return redirect(url_for('index'))

    return render_template('auth/admin_update.html',admin = admin)

@bp.route('/reader_change_password', methods=('GET', 'POST'))
def reader_change_password():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    id = session.get('user_id')
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM reader WHERE rid = %s", (id,))

    post = cur.fetchone()
    if post is None:
        abort(404, "读者账户ID {0} 不存在".format(id))

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        check_new_password = request.form.get('check_new_password')
        error = None
        if not check_password_hash(post['password'], old_password):
            error = '原始密码错误'
        
        if error is None:
            if new_password != check_new_password:
                error = ('密码确认错误')
            
            if error is None:
                cur.execute(
                    'UPDATE reader SET password = %s WHERE rid = %s',
                    (generate_password_hash(new_password), id)
                    )
                conn.commit()
                session.clear()
                flash('密码更改成功,请重新登录')
                return redirect(url_for('auth.reader_login'))
            
        flash(error)

    return render_template('auth/administrator_change_password.html',post = post)

@bp.route('/administrator_change_password', methods=('GET', 'POST'))
def administrator_change_password():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    id = session.get('user_id')
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM administrator WHERE aid = %s", (id,))

    admin = cur.fetchone()
    # if admin is None:
    #     abort(404, "账户ID {0} 不存在.".format(id))

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        check_new_password = request.form.get('check_new_password')
        error = None
        if not check_password_hash(admin['password'], old_password):
            error = '原始密码错误'
        
        if error is None:
            if new_password != check_new_password:
                error = ('密码确认错误')
            
            if error is None:
                cur.execute(
                    'UPDATE administrator SET password = %s WHERE aid = %s',
                    (generate_password_hash(new_password), id)
                    )
                conn.commit()
                session.clear()
                flash('密码更改成功,请重新登录')              
                return redirect(url_for('auth.admin_login'))
            
        flash(error)

    return render_template('auth/administrator_change_password.html',post = admin)

@bp.route('/<int:id>/delete_reader', methods=('GET', 'POST'))
@login_required
def delete_reader(id):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    if not g.is_admin:
        flash("无权限")
        abort(403)
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM reader WHERE rid = %s", (id,))
    conn.commit()
    flash("操作成功")
    return redirect(url_for('auth.reader_list'))

@bp.route('/<int:id>/delete_administrator', methods=('GET', 'POST'))
@login_required
def delete_administrator(id):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    if not g.is_Super:
        flash("无权限")
        abort(403)
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM administrator WHERE aid = %s", (id,))
    admin = cur.fetchone()
    error = None
    if admin['issuper'] == True:
        error = ('不可删除超级管理员')

    if error is None:    
        cur.execute("DELETE FROM administrator WHERE aid = %s", (id,))
        conn.commit()
        flash("操作成功")
    else:
        flash(error)
    return redirect(url_for('auth.admin_list'))
