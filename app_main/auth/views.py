from flask import request, render_template, flash, redirect, url_for, session, Blueprint, g, current_app
from flask_admin import AdminIndexView, BaseView
from flask_admin.actions import ActionsMixin
from flask_admin.form import rules
from flask_login import current_user, login_user, logout_user, login_required

from app_main import db, login_manager, get_ldap_connection, admin, get_locale
from app_main.auth.models import User, CKTextAreaField
from app_main.auth.forms import *
from app_main.auth.decorators import admin_login_required

from flask_admin.contrib.sqla import ModelView
from flask_dance.contrib.google import make_google_blueprint, google
from werkzeug.security import generate_password_hash
from flask_babel import lazy_gettext as _
from flask_admin import expose

auth = Blueprint('auth', __name__)
google_blueprint = make_google_blueprint(
    scope=[
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'],
    redirect_to='auth.google_login')


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@auth.before_request
def get_current_user():
    g.user = current_user


@auth.route('/')
@auth.route('/<lang>/home')
def home():
    return render_template('home.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('username'):
        flash('You ae already logged in.', 'info')
        return redirect(url_for('auth.home'))

    form = RegistrationForm()

    if form.validate_on_submit():
        username = request.form.get('username')
        password = request.form.get('password')
        existing_username = User.query.filter(
            User.username.like('%' + username + '%')).first()
        if existing_username:
            flash(
                'This name username has been already taken.'
                'Try another one.', 'warning'
            )
            return render_template('auth/register.html', form=form)
        user = User(username, password)
        db.session.add(user)
        db.session.commit()
        flash('You are now registered. Please login.', 'success')
        return redirect(url_for('auth.login'))

    if form.errors:
        flash(form.errors, 'danger')

    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('auth.home'))

    form = LoginForm()

    if form.validate_on_submit():
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()

        if not (existing_user and existing_user.check_password(password)):
            flash('Invalid username or password. Please try again.', 'warning')
            return render_template('auth/login.html', form=form)

        login_user(existing_user)
        flash('You have successfully logged in.', 'success')
        return redirect(url_for('auth.home'))

    if form.errors:
        flash(form.errors, 'danger')

    return render_template('auth/login.html', form=form)


@auth.route('/google-login')
def google_login():
    # if not google.authorized:
    #     return redirect(url_for('google.login'))
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('auth.home'))

    resp = google.get('/oauth2/v1/userinfo')
    user = User.query.filter_by(username=resp.json()['email']).first()
    if not user:
        user = User(resp.json()['name'], '')
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash(
        'Logged in using Google account', 'success'
    )
    return redirect(request.args.get('next', url_for('auth.home')))


@auth.route('/ldap-login', methods=['GET', 'POST'])
def ldap_login():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for('auth.home'))

    form = LoginForm()

    if form.validate_on_submit():
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_ldap_connection(username, password)
        if not conn:
            flash('Invalid username or password. Please try again.', 'danger')
            return render_template('auth/login.html', form=form)

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username, password)
            db.session.add(user)
            db.session.commit()

        login_user(user)
        flash('Logged in using LDAP', 'success')

    if form.errors:
        flash(form.errors, 'danger')

    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.home'))


@auth.route('/<lang>/admin')
@login_required
@admin_login_required
def home_admin():
    return render_template('auth/admin-home.html')


@auth.route('/<lang>/admin/users-list')
@login_required
@admin_login_required
def users_list_admin():
    users = User.query.all()
    return render_template('auth/users-list-admin.html', users=users)


@auth.route('/<lang>/admin/create-user', methods=['GET', 'POST'])
@login_required
@admin_login_required
def user_create_admin():
    form = AdminUserCreateForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        admin = form.admin.data
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash('This username has been already taken. Try another one.', 'warning')
            return render_template('auth/register.html', form=form)
        user = User(username, password, admin)
        db.session.add(user)
        db.session.commit()
        flash('New user created.', 'info')
        return redirect(url_for('auth.users_list_admin'))

    if form.errors:
        flash(form.errors, 'danger')

    return render_template('auth/user-create-admin.html', form=form)


@auth.route('/<lang>/admin/update-user/<id>', methods=['GET', 'POST'])
@login_required
@admin_login_required
def user_update_admin(id):
    user = User.query.get(id)
    form = AdminUserUpdateForm(
        username=user.username,
        admin=user.admin
    )

    if form.validate_on_submit():
        username = form.username.data
        admin = form.admin.data

        User.query.filter_by(id=id).update({
            'username': username,
            'admin': admin,
        })

        db.session.commit()
        flash('User updated.', 'info')
        return redirect(url_for('auth.users_list_admin'))

    if form.errors:
        flash(form.errors, 'danger')

    return render_template('auth/user-update-admin.html', form=form, user=user)


@auth.route('/<lang>/admin/delete-user/<id>')
@login_required
@admin_login_required
def user_delete_admin(id):
    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'info')
    return redirect(url_for('auth.users_list_admin'))




class UserAdminView(ModelView, ActionsMixin):
    # column_labels = {
    #     'username': _('Имя пользователя'),
    #     'admin': _('Администратор'),
    #     'roles': _('Роли'),
    #     'notes': _('Примечания'),
    #     'password': _('Пароль'),
    #     'new_password': _('Новый пароль'),
    #     'confirm': _('Подтвердите пароль')
    # }
    column_searchable_list = ('username',)
    column_sortable_list = ('username', 'admin')
    column_exclude_list = ('pwdhash',)
    form_excluded_columns = ('pwdhash',)
    form_edit_rules = (
        'username', 'admin', 'roles', 'notes',
        rules.Header('Reset password'),
        'new_password', 'confirm'
    )
    form_create_rules = (
        'username', 'admin', 'roles', 'notes', 'password'
    )
    form_overrides = dict(notes=CKTextAreaField)
    create_template = 'auth/edit.html'
    edit_template = 'auth/edit.html'

    # @expose('/')
    # @expose('/<lang>')
    # def index(self):
    #     return self.render('admin/index.html')

    # def get_url(self, endpoint, **kwargs):
    #     # Получаем текущий язык из контекста приложения
    #     lang = get_locale()
    #     # Добавляем его в качестве префикса к URL
    #     return super().get_url(f"{lang}/{endpoint}", **kwargs)
    # def __init__(self, *args, **kwargs):
    #     super(UserAdminView, self).__init__(*args, **kwargs)
    #     self.add_translation('ru', 'translations')

    # def get_url(self, endpoint, **kwargs):
    #     # Получаем текущий язык из контекста приложения
    #     lang = get_locale()
    #     # Добавляем его в качестве аргумента URL
    #     kwargs['lang'] = lang
    #     return super().get_url(endpoint, **kwargs)
    # def __init__(self, **kwargs):
    #     super(UserAdminView, self).__init__(**kwargs)

    # def get_url(self, endpoint, **kwargs):
    #     if endpoint != 'admin.static':
    #         lang = get_locale() # Получаем значение переменной lang из kwargs
    #         # kwargs['lang'] = lang  # Добавляем значение переменной lang обратно в kwargs
    #         url = super(UserAdminView, self).get_url(endpoint, **kwargs)
    #         if url.startswith('/'):
    #             url = url[1:]  # Удалить начальный слеш
    #         return f'/{lang}/{url}'
    #     return super(UserAdminView, self).get_url(endpoint, **kwargs)

    # def get_url(self, endpoint, **kwargs):
    #     lang = get_locale() # Получаем значение переменной lang из kwargs
    #     url = super(UserAdminView, self).get_url(endpoint, **kwargs)
    #     if url.startswith('/'):
    #         url = url[1:]  # Удалить начальный слеш
    #     return f'/{lang}/{url}'


    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin()

    def scaffold_form(self):
        form_class = super(UserAdminView, self).scaffold_form()
        form_class.password = PasswordField('Password')
        form_class.new_password = PasswordField('New password')
        form_class.confirm = PasswordField('Confirm new password')
        return form_class

    def create_model(self, form):
        if 'C' not in current_user.roles:
            flash('You are not allowed to create users.', 'warning')
            return
        model = self.model(
            form.username.data,
            form.password.data,
            form.admin.data
        )
        form.populate_obj(model)
        self.session.add(model)
        self._on_model_change(form, model, True)
        self.session.commit()
        flash('User created.', 'info')

    def update_model(self, form, model):
        if 'U' not in current_user.roles:
            flash('You are not allowed to edit users.', 'warning')
            return
        form.populate_obj(model)
        if form.new_password.data:
            if form.new_password.data != form.confirm.data:
                flash('Password must match')
                return
            model.pwdhash = generate_password_hash(form.new_password.data)
        self.session.add(model)
        self._on_model_change(form, model, False)
        self.session.commit()
        # flash('Password updated', 'success')

    def delete_model(self, model):
        if 'D' not in current_user.roles:
            flash('You are not allowed to delete users.', 'warning')
            return
        super(UserAdminView, self).delete_model(model)

    def is_action_allowed(self, name):
        if name == 'delete' and 'D' not in current_user.roles:
            flash('You are not allowed to delete users.', 'warning')
            return False
        return True

# class HomeAdminView(AdminIndexView):
#     def get_url(self, endpoint, **kwargs):
#         lang = get_locale() # Получаем значение переменной lang из kwargs
#         url = super(HomeAdminView, self).get_url(endpoint, **kwargs)
#         if url.startswith('/'):
#             url = url[1:]  # Удалить начальный слеш
#         return f'/{lang}/{url}'
#
#     def is_accessible(self):
#         return current_user.is_authenticated and current_user.is_admin()


# class LangView(BaseView):
#     @expose('/')
#     @expose('/<lang>')
#     def index(self):
#         # Получаем текущий язык из параметра в адресной строке
#         lang = request.args.get('lang', 'ru')
#         g.current_lang = lang  # Сохраняем текущий язык в глобальном контексте
#         return self.render('auth/users-list-admin.html', lang=lang)
#
#
# class MyAdminIndexView(AdminIndexView):
#     def __init__(self, **kwargs):
#         super(MyAdminIndexView, self).__init__(**kwargs)
#
#     @expose('/')
#     def index(self):
#         lang = get_locale()  # Здесь задайте значение переменной
#         return self.render('admin/index.html', lang=lang)

# if 'username' in session:
#     session.pop('username')
#     flash('You have successfully logged out.', 'success')


# @auth.route('/ldap-login', methods=['GET', 'POST'])
# def ldap_login():
#     if current_user.is_authenticated:
#         flash('You ae already logged in.', 'info')
#         return redirect(url_for('auth.home'))
#
#     form = LoginForm()
#
#     if form.validate_on_submit():
#         username = request.form.get('username')
#         password = request.form.get('password')
#         try:
#             conn = get_ldap_connection()
#             conn.simple_bind_s(
#                 'cn=%s,dc=example,dc=org' %username, password
#             )
#         except ldap.INVALID_CREDENTIALS:
#             flash('Invalid username or password.'
#                   'Please try again.', 'danger')
#             return render_template('auth/login.html', form=form)
#
#         user = User.query.filter_by(username=username).first()
#         if not user:
#             user = User(username, password)
#             db.session.add(user)
#             db.session.commit()
#
#         login_user(user)
#         flash('Logged in using LDAP', 'success')
#
#     if form.errors:
#         flash(form.errors, 'danger')
#
#     return render_template('auth/login.html', form=form)
# class HomeAdminView(AdminIndexView):
#     @expose('/')
#     def index(self):
#         return self.render('admin/index.html')
#
#     def get_url(self, endpoint, **kwargs):
#         lang = get_locale() # Получаем значение переменной lang из kwargs
#         url = super(HomeAdminView, self).get_url(endpoint, **kwargs)
#         if url.startswith('/'):
#             url = url[1:]  # Удалить начальный слеш
#         return f'/{lang}/{url}'
#
#     def is_accessible(self):
#         return current_user.is_authenticated and current_user.is_admin()