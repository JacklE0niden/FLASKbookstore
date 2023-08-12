from flask import Flask, render_template
import db
import auth
import book

def create_app():
    app = Flask(__name__)
    app.debug = True  # 开启调试模式
    app.secret_key = b'1\x0fFSP%\x9f~"\x05Z\xc4v\x86\xda;'
    
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

   
    db.init_app(app)

    app.register_blueprint(auth.bp)

    
    app.register_blueprint(book.bp)
    app.add_url_rule('/', endpoint='index')

    return app
