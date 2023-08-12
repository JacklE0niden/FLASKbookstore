--schema

DROP TABLE IF EXISTS administrator CASCADE;
DROP TABLE IF EXISTS reader CASCADE;
DROP TABLE IF EXISTS book CASCADE;
DROP TABLE IF EXISTS list CASCADE;
DROP TABLE IF EXISTS income CASCADE;
DROP TABLE IF EXISTS expenses CASCADE;
DROP TABLE IF EXISTS borrow_list CASCADE;
DROP VIEW IF EXISTS income_view;
DROP VIEW IF EXISTS expenses_view;

CREATE TABLE administrator (
    aid SERIAL PRIMARY KEY,
    workno INTEGER,
    aname TEXT NOT NULL,
    password TEXT NOT NULL,
    realname TEXT,
    gender TEXT DEFAULT '未知',
    age INTEGER,
    issuper BOOLEAN NOT NULL DEFAULT false
    -- bool是否为超级管理员
);

INSERT INTO administrator(aid,workno,aname,password,realname,gender,age, isSuper)
VALUES (0, 1, 'postgres', 'pbkdf2:sha256:260000$QENguD6goNgHSXiI$edb06ec782886710165b3f7c173507d5e5da2e5739858774b81d84854abf2fe5', 'LR', '未知', 20, True);
--Lr31415926密码

CREATE TABLE reader (
    rid SERIAL PRIMARY KEY,
    rname TEXT NOT NULL ,
    password TEXT NOT NULL,
    gender TEXT DEFAULT '未知',
    age INTEGER
);

CREATE TABLE book (
    bid SERIAL PRIMARY KEY,
    isbn TEXT NOT NULL,
    bookname TEXT NOT NULL,
    author TEXT NOT NULL,
    publisher TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0,
    available BOOLEAN NOT NULL DEFAULT false,
    available_to_borrow BOOLEAN NOT NULL DEFAULT false,
    unit_price INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0
    -- 出售单价
);

INSERT INTO book(bid,isbn,bookname,author,publisher,amount,available,available_to_borrow,unit_price)
VALUES (0, '9787544270779', '二十首诗和一首绝望的歌', '巴勃罗·聂鲁达', '南海出版公司', 2000 ,True, True, 20);

CREATE TABLE list ( -- 进货清单
    oid SERIAL PRIMARY KEY,  -- 序号
    bid INTEGER NOT NULL,
    amount INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0,  -- 数量
    unit_price INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0,  -- 进货单价
    isRefund BOOLEAN NOT NULL DEFAULT false,  -- 退货
    isPaid BOOLEAN NOT NULL DEFAULT false,  -- 已付款？
    isArrived BOOLEAN NOT NULL DEFAULT false,  -- 到货上架？
    FOREIGN KEY (bid) REFERENCES book (bid)
);

CREATE TABLE income( -- 收入账单
    inno SERIAL PRIMARY KEY, -- 序号
    bid INTEGER NOT NULL,
    time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0, -- 数量
    unit_price INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0, -- 书的单价
    -- total_income INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0, -- 这一笔的总收入
    isbookrefund BOOLEAN NOT NULL DEFAULT false, -- 是否退货
    FOREIGN KEY (bid) REFERENCES book (bid)
);

CREATE VIEW income_view AS
SELECT *,
       amount * unit_price AS total_income
FROM income;

CREATE TABLE expenses( --支出账单
    exno SERIAL PRIMARY KEY, -- 序号
    bid INTEGER NOT NULL,
    time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0, -- 数量
    unit_price INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0, -- 书的单价
    -- total_expenses INTEGER NOT NULL CHECK (amount >= 0) DEFAULT 0, -- 这一笔的总收入
    source TEXT NOT NULL, --来源是进货还是买书退货
    FOREIGN KEY (bid) REFERENCES book (bid)
);

CREATE VIEW expenses_view AS
SELECT *,
       amount * unit_price AS total_expenses
FROM expenses;

CREATE TABLE borrow_list(  -- 借出书单 默认一本一本借
    brno SERIAL PRIMARY KEY, -- 序号
    bid INTEGER NOT NULL,
    rid INTEGER NOT NULL,
    br_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    isReturn BOOLEAN NOT NULL DEFAULT false, -- 是否归还
    FOREIGN KEY (bid) REFERENCES book (bid),
    FOREIGN KEY (rid) REFERENCES reader (rid)
)