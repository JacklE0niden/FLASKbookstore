from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from werkzeug.exceptions import abort

from db import connect_db
from auth import login_required

import psycopg2

bp = Blueprint('book', __name__)

# index page
@bp.route('/', methods=('GET', 'POST'))
def index():
    current_page = request.form.get('page',1)
    error = None
    if not current_page:
        current_page = 1
    else:
        current_page = int(current_page) 
    try:
        db = connect_db()
        cur = db.cursor()
        # 已到货的书籍
        cur.execute(
            'SELECT bid, isbn, bookname, author, publisher, amount, unit_price, available,available_to_borrow'
            ' FROM book'
            ' WHERE unit_price > 0'
            ' ORDER BY bid'
            )
        books = cur.fetchall()
        num_books = len(books)
    except (Exception,psycopg2.Error) as e:
        # Handle the error gracefully
        flash(e)  
    else:
        if current_page > num_books//2 + 1:
            current_page = 1
            error = '页数无效,跳转回第一页'
        if error is not None:
            flash(error)
        return render_template('book/index.html', posts=books, num_books=num_books, i=current_page)


@bp.route('/search', methods=('GET', 'POST'))
@login_required
def search():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    current_page = request.form.get('page',1)
    search = request.args.get('search')
    type = request.args.get('type')
    error = None
    if not current_page:
        current_page = 1
    else:
        current_page = int(current_page) 
    db = connect_db()
    cur = db.cursor()
    books = []
    try:
        if g.is_admin:
            if type=="ID":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE bid = %s'
                    ' ORDER BY bid',
                    (search,)
                )
            elif type=="ISBN":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE isbn = %s'
                    ' ORDER BY bid',
                    (search,)
                )
            elif type=="书名":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE bookname ILIKE %s'
                    ' ORDER BY bid',
                    ('%'+search+'%',)
                )
            elif type=="作者":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE author ILIKE %s'
                    ' ORDER BY bid',
                    ('%'+search+'%',)
                )
            elif type=="出版社":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE publisher ILIKE %s'
                    ' ORDER BY bid',
                    ('%'+search+'%',)
                )
        else:
            if type=="ID":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE available = true AND bid = %s'
                    ' ORDER BY bid',
                    (search,)
                )
            elif type=="ISBN":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE available = true AND isbn = %s'
                    ' ORDER BY bid',
                    (search,)
                )
            elif type=="书名":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE available = true AND bookname ILIKE %s'
                    ' ORDER BY bid',
                    ('%'+search+'%',)
                )
            elif type=="作者名":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE available = true AND author ILIKE %s'
                    ' ORDER BY bid',
                    ('%'+search+'%',)
                )
            elif type=="出版社":
                cur.execute(
                    'SELECT *'
                    ' FROM book'
                    ' WHERE available = true AND publisher ILIKE %s'
                    ' ORDER BY bid',
                    ('%'+search+'%',)
                )
        books = cur.fetchall()
        num_books = len(books)
    except:
        books = []
        num_books = 0
    
    if request.method == 'POST':
        type = request.form['type']
        search = request.form['search']
        if g.user is None:
            error = "请先登录"
        if current_page > num_books//10 + 1:
            current_page = 1
            error = '页数无效,跳转回第一页'
        if error is not None:
            flash(error)
        else:
            return redirect(url_for('book.search',type=type,search=search))

    return render_template('book/index.html', posts=books, type=type, search=search, num_books=num_books, i=current_page)


# 销售
@bp.route('/sell', methods=('GET', 'POST'))
@login_required
def sell():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    if request.method == 'POST':
        bid = request.form['bid']
        sell_amount = request.form['sell_amount']
        error = None
        if not sell_amount:
            error = '请输入购买量'
        if error is not None:
            flash(error)
        else:
            db = connect_db()
            cur = db.cursor()
            cur.execute(
                'SELECT amount'
                ' FROM book'
                ' WHERE bid = %s',
                (bid,)
            )
            books = cur.fetchone() # 库存书籍数量
            amount = books['amount'] 
            if amount == None:
                error = 'BID not exist.'
            else:
                if amount < int(sell_amount):
                    error = 'Not enough books.'
                else: # 库存足够，执行销售
                    cur.execute(
                        'UPDATE book'
                        ' SET amount = amount - %s'
                        ' WHERE bid = %s',
                        (sell_amount, bid)
                    )
                    cur.execute(
                        'SELECT *'
                        ' FROM book'
                        ' WHERE bid = %s',
                        (bid,)
                    )
                    book = cur.fetchone()
                    this_bid = book['bid']
                    sell_unit_price = int(book['unit_price'])
                    sell_total_price = int(sell_unit_price) * int(sell_amount)
                    # 在income中添加记录
                    cur.execute(
                        'INSERT INTO income (bid, amount, unit_price, total_income)'
                        ' VALUES (%s, %s, %s, %s)',
                        (this_bid, sell_amount, sell_unit_price, sell_total_price)
                    )
        db.commit()

    return redirect(url_for('book.index'))

# 图书退货
@bp.route('/<int:inno>/bookrefund', methods=('GET', 'POST'))
@login_required
def bookrefund(inno):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    conn = connect_db()
    cur = conn.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
            'UPDATE income'
            ' SET isbookrefund = true '
            ' WHERE inno = %s',
            (inno,)
            )
    cur.execute(
                    ' SELECT * '
                    ' FROM income '
                    ' WHERE inno = %s',
                    (inno, )
                    )
    post = cur.fetchone()
    cur.execute(
            'UPDATE book'
            ' SET amount = amount + %s'
            ' WHERE bid = %s',
            (post['amount'], post['bid'])
        )
    cur.execute(
        'INSERT INTO expenses (bid, amount, unit_price, source)'
        ' VALUES (%s, %s, %s, %s)',
        (post['bid'], post['amount'], post['unit_price'], '售后退货退款')
        )
    flash("操作成功")
    conn.commit()
    return redirect(url_for('book.list_expenses'))
    # return render_template('book/index.html',posts = bklst)

# List 进货清单
@bp.route('/list', methods=('GET', 'POST'))
@login_required
def list():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    if g.is_admin and g.is_Super:
        db = connect_db()
        cur = db.cursor()
        
        cur.execute(
            'SELECT oid, X.bid, X.amount, X.unit_price as jinjia, Y.unit_price as shoujia, isRefund, isPaid, isArrived'
            ' FROM list as X, book as Y'
            ' WHERE X.bid = Y.bid'
            ' ORDER BY oid'
        )
        books = cur.fetchall()
        return render_template('book/list.html', posts=books)
    else:
        abort(403)


# 进货
@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    # flag_new = 0
    if g.is_admin == False:
        abort(403)
    if request.method == 'POST':
        isbn = request.form['isbn']
        bookname = request.form['bookname']
        author = request.form['author']
        publisher = request.form['publisher']
        amount = request.form['amount']
        unit_price = request.form['unit_price']
        error = None

        if not isbn:
            error = '请输入ISBN'
        elif not amount:
            error = '请输入数量'
        elif not unit_price:
            error = '请输入零售价'

        if error is not None:
            flash(error)
        else:
            db = connect_db()
            cur = db.cursor()
            # if isbn doesn't exist in book, 创建新书
            cur.execute(
                'SELECT * FROM book WHERE isbn = %s',
                (isbn,)
            )
            if cur.fetchone() is None:
                # 进货单价不用insert到book表格里面
                # 创建新书
                cur.execute(
                    'INSERT INTO book (isbn, bookname, author, publisher, amount)'
                    ' VALUES (%s, %s, %s, %s, %s)',
                    (isbn, 'null', author, publisher, 0)
                )
                return render_template('book/create.html', flag_new = 1)
            
            cur.execute(
                'SELECT * FROM book WHERE isbn = %s',
                (isbn,)
            )
            book = cur.fetchone()
            tmp_bookname = book['bookname']
            # is new book
            if tmp_bookname == 'null':
                cur.execute(
                    'UPDATE book'
                    ' SET bookname = %s, author = %s, publisher = %s'
                    ' WHERE isbn = %s',
                    (bookname, author, publisher, isbn)
                )
            # add to 进货清单
            cur.execute(
                'SELECT bid'
                ' FROM book'
                ' WHERE isbn = %s',
                (isbn,)
            )
            result = cur.fetchone()
            this_bid = result[0]
            cur.execute(
                'INSERT INTO list (bid, amount, unit_price)'
                ' VALUES (%s, %s, %s)',
                (this_bid, amount, unit_price)
            )
            # cur.execute(
            #     'UPDATE book'
            #     ' SET amount = amount + %s'
            #     ' WHERE isbn = %s',
            #     (amount, isbn)
            # )
            db.commit()
            return redirect(url_for('book.index'))
        # return render_template('book/create.html', flag_new = 1)
    return render_template('book/create.html', flag_new = 0)

# 付款(给定order的id)
@bp.route('/<int:oid>/pay', methods=('GET', 'POST'))
@login_required
def pay(oid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
            'UPDATE list'
            ' SET isPaid = true'
            ' WHERE oid = %s',
            (oid,)
        )
    db.commit()
    cur.execute(
        'SELECT *'
        ' FROM list'
        ' WHERE oid = %s',
        (oid,)
    )
    order = cur.fetchone()
    bid = order['bid']
    pay_amount = order['amount']
    pay_unit_price = order['unit_price']
    cur.execute(
        'INSERT INTO expenses (bid, amount, unit_price, source)'
        ' VALUES (%s, %s, %s, %s)',
        (bid, pay_amount, pay_unit_price,  '进货')
    )
    db.commit()
    return redirect(url_for('book.list'))

# 退货(给定order的id)
@bp.route('/<int:oid>/refund', methods=('POST','GET'))
@login_required
def refund(oid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
        'UPDATE list'
        ' SET isRefund = true'
        ' WHERE oid = %s',
        (oid,)
    )
    db.commit()
    return redirect(url_for('book.list'))

# 到货+自动上架(给定order的id)
@bp.route('/<int:oid>/arrive', methods=('POST','GET'))
@login_required
def arrive(oid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
        'UPDATE list'
        ' SET isArrived = true'
        ' WHERE oid = %s',
        (oid,)
    )
    cur.execute(
        'SELECT *'
        ' FROM list'
        ' WHERE oid = %s',
        (oid,)
    )
    order = cur.fetchone()
    bid = order['bid']
    pay_amount = order['amount']
    cur.execute(
        'UPDATE book'
        ' SET amount = amount + %s'
        ' WHERE bid = %s',
        (pay_amount, bid)
    )
    # 自动上架
    cur.execute(
        'UPDATE book'
        ' SET available = true'
        ' WHERE bid = %s',
        (bid,)
    )
    db.commit()
    return redirect(url_for('book.list'))

# 设置零售价
@bp.route('/set_unit_price', methods=(['POST']))
@login_required
def set_unit_price():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db=connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    if request.method == 'POST':
        unit_price = request.form['unit_price']
        bid=request.form['bid']
        error = None
        if not unit_price:
            error = '请输入零售价'
        if error is not None:
            flash(error)
        else:
            cur.execute(
            'UPDATE book'
            ' SET unit_price = %s'
            ' WHERE bid = %s',
            (unit_price, bid)
            )
            db.commit()
            return redirect(url_for('book.index'))
        
    return redirect(url_for('book.list'))

# 更改书籍信息
@bp.route('/<int:bid>/update_book',methods=('POST','GET'))
@login_required
def update_book(bid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
        'SELECT *'
        ' FROM book'
        ' WHERE bid = %s',
        (bid,)
    )
    book = cur.fetchone()

    if request.method == 'POST':
        isbn = request.form['isbn']
        bookname = request.form['bookname']
        author = request.form['author']
        publisher = request.form['publisher']
        
        db = connect_db()
        cur = db.cursor()
        try:
            cur.execute(
                'UPDATE book SET isbn = %s, bookname = %s, author = %s, publisher = %s'
                ' WHERE bid = %s',
                (isbn, bookname, author, publisher, bid)
            )
            db.commit()
            return redirect(url_for('book.update_book'),post=book)

        except(Exception, psycopg2.Error) as error:
            flash(error)

    return render_template('book/update_book.html', book=book)



# 更改零售价
@bp.route('/change_unit_price', methods=(['POST']))
@login_required
def change_unit_price():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db=connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    if request.method == 'POST':
        unit_price = request.form['unit_price']
        bid=request.form['bid']
        error = None
        if not unit_price:
            error = 'Unit_price is required.'
        if error is not None:
            flash(error)
        else:
            cur.execute(
            'UPDATE book'
            ' SET unit_price = %s'
            ' WHERE bid = %s',
            (unit_price, bid)
            )
    db.commit()
    return redirect(url_for('book.index'))

# 上架(给定book的id)
@bp.route('/<int:bid>/puton', methods=('POST','GET'))
@login_required
def puton(bid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
        'UPDATE book'
        ' SET available = true'
        ' WHERE bid = %s',
        (bid,)
    )
    db.commit()
    return redirect(url_for('book.index'))

# 下架(给定book的id)
@bp.route('/<int:bid>/takeoff', methods=('POST','GET'))
@login_required
def takeoff(bid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
        'UPDATE book'
        ' SET available = false'
        ' WHERE bid = %s',
        (bid,)
    )
    db.commit()
    return redirect(url_for('book.index'))


@bp.route('/list_expenses', methods=['GET', 'POST'])
def list_expenses():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    if request.method == 'POST':
        db = connect_db()
        cur = db.cursor()
        error = None
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        if not start_date:
            error = '请输入起始日期'
        elif not end_date:
            error = '请输入终止日期'
        elif start_date > end_date:
            error = '起始日期应该在终止日期之前'
        if error is None:
            cur.execute(
            'SELECT *'
            ' FROM expenses_view'
            ' WHERE time BETWEEN %s AND %s'
            ' ORDER BY exno',
            (start_date, end_date)
            )
            bills = cur.fetchall()
            return render_template('book/list_expenses.html',posts = bills)
        else:
            flash(error)
        # return redirect(url_for('book.list_expenses',posts=bills))
        return render_template('book/list_expenses.html')

    # If the request method is GET, render the template without filtering
    db = connect_db()
    cur = db.cursor()
    cur.execute(
        'SELECT *'
        ' FROM expenses_view'
        ' ORDER BY exno',
    )
    bills = cur.fetchall()
    return render_template('book/list_expenses.html',posts=bills)

# 收入账单
@bp.route('/list_income', methods=['GET', 'POST'])
def list_income():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    if request.method == 'POST':
        db = connect_db()
        cur = db.cursor()
        error = None
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')
        if not start_date:
            error = '请输入起始日期'
        elif not end_date:
            error = '请输入终止日期'
        elif start_date > end_date:
            error = '起始日期应该在终止日期之前'
        if error is None:
            cur.execute(
            'SELECT *'
            ' FROM income_view'
            ' WHERE time BETWEEN %s AND %s'
            ' ORDER BY inno',
            (start_date, end_date)
            )
            bills = cur.fetchall()
            return render_template('book/list_income.html',posts = bills)
        else:
            flash(error)
        # return redirect(url_for('book.list_expenses',posts=bills))
        return render_template('book/list_income.html')

    # If the request method is GET, render the template without filtering
    db = connect_db()
    cur = db.cursor()
    cur.execute(
        'SELECT *'
        ' FROM income_view'
        ' ORDER BY inno',
    )
    bills = cur.fetchall()
    return render_template('book/list_income.html',posts=bills)

# 设为可出借
@bp.route('/<int:bid>/set_available_to_borrow', methods=('POST','GET'))
@login_required
def set_available_to_borrow(bid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
        'UPDATE book'
        ' SET available_to_borrow = true'
        ' WHERE bid = %s',
        (bid,)
    )
    # test
    cur.execute(
        'SELECT *'
        ' FROM book'
        ' WHERE bid = %s',
        (bid,)
    )
    book=cur.fetchone()
    print(book['available_to_borrow'])
    db.commit()
    return redirect(url_for('book.index'))

# 设为不可出借
@bp.route('/<int:bid>/set_unavailable_to_borrow', methods=('POST','GET'))
@login_required 
def set_unavailable_to_borrow(bid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    if g.is_admin == False:
        abort(403)
    cur.execute(
        'UPDATE book'
        ' SET available_to_borrow = false'
        ' WHERE bid = %s',
        (bid,)
    )
    # test
    cur.execute(
        'SELECT *'
        ' FROM book'
        ' WHERE bid = %s',
        (bid,)
    )
    book=cur.fetchone()
    print(book['available_to_borrow'])
    db.commit()
    return redirect(url_for('book.index'))


# 读者借书
@bp.route('/<int:bid>/borrow', methods=('POST','GET'))
@login_required
def borrow(bid):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    error = None
    if g.is_admin == True:
        abort(403)
    cur.execute(
        'SELECT *'
        ' FROM book'
        ' WHERE bid = %s',
        (bid,)
    )
    book = cur.fetchone()
    # if book['available'] == False:
    #     flash('The book is not available.')
    # elif book['amount'] < amount:
    #     flash('The amount is not enough.')
    # else:
    cur.execute(
        'INSERT INTO borrow_list (bid, rid)'
        ' VALUES (%s, %s)',
        (bid, g.user['rid'])
    )
    cur.execute(
        'UPDATE book'
        ' SET amount = amount - 1'
        ' WHERE bid = %s',
        (bid,)
    )
    cur.execute(
        'SELECT *'
        ' FROM book'
        ' WHERE bid = %s',
        (bid,)
    )
    book = cur.fetchone()
    # print(book['amount'])
    if (book['amount']) == 0:
        cur.execute(
            'UPDATE book'
            ' SET available_to_borrow = false'
            ' WHERE bid = %s',
            (bid,)
        )
    flash("操作成功")
    db.commit()
    return redirect(url_for('book.index'))
    # return render_template('book/borrow.html')

# 读者还书
@bp.route('/<int:brno>/return_book', methods=('POST','GET'))
@login_required
def return_book(brno):
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    error = None
    if g.is_admin == True:
        abort(403)
    
    # if book['available'] == False:
    #     flash('The book is not available.')
    # elif book['amount'] < amount:
    #     flash('The amount is not enough.')
    # else:
    cur.execute(
        'UPDATE borrow_list'
        ' SET isReturn = true'
        ' WHERE brno = %s',
        (brno,)
    )
    cur.execute(
        'SELECT *'
        ' FROM borrow_list'
        ' WHERE brno = %s',
        (brno,)
    )
    book = cur.fetchone()
    bid = book['bid']
    cur.execute(
        'UPDATE book'
        ' SET amount = amount + 1'
        ' WHERE bid = %s',
        (bid,)
    )
    cur.execute(
        'SELECT *'
        ' FROM book'
        ' WHERE bid = %s',
        (bid,)
    )
    book = cur.fetchone()
    # print(book['amount'])
    if (book['amount']) == 1:
        cur.execute(
            'UPDATE book'
            ' SET available_to_borrow = true'
            ' WHERE bid = %s',
            (bid,)
        )
    flash("操作成功")
    db.commit()
    cur.execute(
        ' SELECT brno, bid, br_time, (EXTRACT(DAY FROM (CURRENT_DATE - br_time)) + 1)::int AS days , isReturn '
        ' FROM borrow_list '
        ' WHERE rid = %s'
        ' ORDER BY brno',
        (g.user['rid'],)
    )
    borrow_list = cur.fetchall()
    # return redirect(url_for('book.borrow_list'))
    return render_template('book/borrow_list.html',posts = borrow_list)


# 借书清单
@bp.route('/borrow_list')
@login_required
def borrow_list():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db = connect_db()
    cur = db.cursor()
    cur.execute(
        ' SELECT brno, bid, br_time, (EXTRACT(DAY FROM (CURRENT_DATE - br_time)) + 1)::int AS days , isReturn '
        ' FROM borrow_list '
        ' WHERE rid = %s'
        ' ORDER BY brno',
        (g.user['rid'],)
    )
    borrow_list = cur.fetchall()
    posts = [dict(post) for post in borrow_list]
    return render_template('book/borrow_list.html', posts = posts)

# 超级管理员查看所有借阅清单
@bp.route('/all_borrow_list')
@login_required
def all_borrow_list():
    if g.user is None:
            return redirect(url_for('auth.admin_login'))
    db=connect_db()
    cur = db.cursor()
    if g.is_admin == False:  # or g.is_super == False
        abort(403)
    cur.execute(
        'SELECT brno, rid, bid, br_time, (EXTRACT(DAY FROM (CURRENT_DATE - br_time)) + 1)::int AS days , isReturn  '
        'FROM borrow_list '
        'ORDER BY brno',
    )
    borrow_list = cur.fetchall()
    posts = [dict(post) for post in borrow_list]
    return render_template('book/all_borrow_list.html', posts = posts)