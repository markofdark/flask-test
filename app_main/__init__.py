from flask import Flask, render_template, request, g, url_for as flask_url_for, Blueprint, send_from_directory
from flask_admin.menu import MenuLink
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, current_user
from flask_restful import Api
from flask_admin import Admin, AdminIndexView, expose
from flask_babel import Babel
from flask_caching import Cache
from flask_mail import Mail
from celery import Celery, Task

from elasticsearch import Elasticsearch

from app_main.catalog.moment import momentjs
from ldap3 import Server, Connection, ALL, SIMPLE, SYNC, ALL_ATTRIBUTES, ALL_OPERATIONAL_ATTRIBUTES
import os
import ccy
import sentry_sdk
from datetime import datetime

# sentry_sdk.init(
#     dsn="https://4e0a17cd2b02b29b9ad2abb76982acde@o4506309851217920.ingest.sentry.io/4506309853511680",
#     # traces_sample_rate=1.0,
#     # profiles_sample_rate=1.0,
# )

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy()
migrate = Migrate()

def full_name_filter(product):
    return '{0} / {1}'.format(product.category.name, product.name)


def page_not_found(e):
    app.logger.error(e)
    return render_template('404.html'), 404


def get_locale():
    return g.get('current_lang', 'en')


def get_ldap_connection(username, password):
    server = Server(app.config['LDAP_PROVIDER_URL'], get_info=ALL)
    conn = Connection(server,
                      user=app.config['LDAP_BIND_USER_DN'] % username,
                      password=password,
                      authentication=SIMPLE)
    return conn.bind()

def staticfiles(app):
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(app.config['STATIC_FOLDER'], filename)


# def make_celery(app):
#     celery = Celery(
#         app.import_name,
#         broker=app.config['CELERY_BROKER_URL'],
#         # backend=app.config['CELERY_RESULT_BACKEND']
#     )
#     # celery.conf.update(app.config)
#     TaskBase = celery.Task
#
#     class ContextTask(TaskBase):
#         abstract = True
#
#         def __call__(self, *args, **kwargs):
#             with app.app_context():
#                 return TaskBase.__call__(self, *args, **kwargs)
#
#     celery.Task = ContextTask
#     return celery


def create_app(alt_config={}):

    app = Flask(__name__, template_folder=alt_config.get('TEMPLATE_FOLDER', 'templates'))

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'db.sqlite3')
    app.config['UPLOAD_FOLDER'] = os.path.realpath('.') + '/app_main/static/uploads'
    app.config['WTF_CSRF_SECRET_KEY'] = 'key for form'
    app.config['LOG_FILE'] = 'application.log'

    app.config["GOOGLE_OAUTH_CLIENT_ID"] = "526743848755-05lvpcv4gp4inp7ok89spkv43e5n2s5p.apps.googleusercontent.com"
    app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = "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"
    app.config["OAUTHLIB_RELAX_TOKEN_SCOPE"] = True

    app.config['LDAP_PROVIDER_URL'] = 'ldap://localhost'
    app.config['LDAP_PROTOCOL_VERSION'] = 3
    app.config['LDAP_BIND_USER_DN'] = 'cn=%s,dc=example,dc=org'
    app.config['LDAP_BIND_USER_PWD'] = 'password'

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'markofdark9'
    app.config['MAIL_PASSWORD'] = 'vachpjpujdcanxjz'
    app.config['MAIL_DEFAULT_SENDER'] = ('app_main', 'markofdark9@gmail.com')

    app.config['SERVER_NAME'] = '127.0.0.1:5000'
    app.config.update(
        CELERY_BROKER_URL='redis://127.0.0.1:6379',
        CELERY_RESULT_BACKEND='redis://127.0.0.1:6379',
    )
    # app.config['CELERY_BROKER_URL'] = 'redis://127.0.0.1:6379'
    # app.config['CELERY_RESULT_BACKEND'] = 'redis://127.0.0.1:6379'

    app.config.update(alt_config)

    app.secret_key = 'secret_key'
    app.jinja_env.filters['full_name'] = full_name_filter
    app.register_error_handler(404, page_not_found)

    staticfiles(app)

    if not app.debug:
        import logging
        from logging import FileHandler, Formatter
        from logging.handlers import SMTPHandler
        file_handler = FileHandler(app.config['LOG_FILE'])
        app.logger.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        # mail_handler = SMTPHandler(
        #     ('smtp.gmail.com', 587),
        #     'markofdark9@gmail.com',
        #     'customer00@inbox.ru',
        #     'Error occurred in your application',
        #     ('markofdark9@gmail.com', 'vachpjpujdcanxjz'), secure=())
        # mail_handler.setLevel(logging.ERROR)
        # app.logger.addHandler(mail_handler)
        file_handler.setFormatter(Formatter(
            '%(asctime)s %(levelname)s: %(message)s'
            '[in %(pathname)s:%(lineno)d'
        ))

    return app


def create_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

    return db


def create_admin(app):
    return Admin(app, template_mode='bootstrap4')


app = create_app()
babel = Babel(app)
babel.init_app(app, locale_selector=get_locale)

# es = Elasticsearch('https://localhost:9200/',
#                    ca_certs='C:/elasticsearch/elasticsearch-8.11.3/config/certs/http_ca.crt',
#                    verify_certs=False,
#                    basic_auth=('elastic', 'zxKDcXJIEuuE+BKEUwp0')
#                    )
# es.indices.create(index='catalog', ignore=400)
def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        # backend=app.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

celery = make_celery(app)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})
admin = create_admin(app)
restapi = Api(app)
mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

from app_main.catalog.views import catalog, url_for
app.register_blueprint(catalog)

from app_main.api.views import api_blueprint
app.register_blueprint(api_blueprint)



import app_main.auth.views as views
app.register_blueprint(views.auth)
app.register_blueprint(views.google_blueprint)

admin.add_view(views.UserAdminView(views.User, db.session))

db = create_db(app)
migrate.init_app(app, db)

# for lang in ['en', 'ru']:  # добавьте сюда все языки, которые вы хотите поддерживать
#     bp = Blueprint(f'{lang}_admin', __name__, url_prefix=f'/{lang}/admin')
#     admin.init_app(app, bp)

# with app.app_context():
#     db.create_all()

# app.jinja_env.globals['momentjs'] = momentjs

# @app.template_filter('format_currency')
# def format_currency_filter(amount):
#     currency_code = ccy.countryccy(request.accept_languages.best[-2:])
#     return '{0} {1}'.format(currency_code, amount)
# , index_view=views.MyAdminIndexView

# @app.context_processor
# def inject_variables():
#     return {'timestamp': datetime.now()}

