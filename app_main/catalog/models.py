from wtforms.validators import InputRequired, NumberRange, ValidationError
from wtforms.widgets import html_params, Select
from markupsafe import Markup

from app_main import db, app
from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_babel import lazy_gettext as _
from blinker import Namespace

catalog_signals = Namespace()
product_created = catalog_signals.signal('product-created')
category_created = catalog_signals.signal('category-created')


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Category %d>' % self.id


# def add_category_index_to_es(sender, category):
#     es.index(index='catalog', document={
#         'name': category.name,
#     }, id=category.id)
#     es.indices.refresh(index='catalog')
#
#
# category_created.connect(add_category_index_to_es, app)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    price = db.Column(db.Float)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref=db.backref('products', lazy='dynamic'))
    image_path = db.Column(db.String(255))
    user_timezone = db.Column(db.String(255))

    def __init__(self, name, price, category, image_path, user_timezone=''):
        self.name = name
        self.price = price
        self.category = category
        self.image_path = image_path
        self.user_timezone = user_timezone

    def __repr__(self):
        return '<Product %d>' % self.id


# def add_product_index_to_es(sender, product):
#     es.index(index='catalog', document={
#         'name': product.name,
#         'category': product.category.name
#     }, id=product.id)
#     es.indices.refresh(index='catalog')
#
#
# product_created.connect(add_product_index_to_es, app)


class CustomCategoryInput(Select):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = []
        for val, label, selected in field.iter_choices():
            html.append(
                '<input type="radio" %s> %s' % (
                    html_params(name=field.name, value=val, checked=selected, **kwargs), label
                )
            )
        return Markup(' '.join(html))


class CategoryField(SelectField):
    widget = CustomCategoryInput()

    def iter_choices(self):
        categories = [(c.id, c.name) for c in Category.query.all()]
        for value, label in categories:
            selected = self.coerce(value) == self.data
            yield value, label, selected
            # yield value, label, selected, {}

    def pre_validate(self, form):
        for v, _ in [(c.id, c.name) for c in Category.query.all()]:
            if self.data == v:
                break
        else:
            raise ValueError(self.gettext('Not a valid choice'))


# class NameForm(FlaskForm):
#     name = StringField('Name', validators=[InputRequired()])


class ProductForm(FlaskForm):
    name = StringField(_('Name'), validators=[InputRequired()])
    price = DecimalField(_('Price'), validators=[
        InputRequired(), NumberRange(min=Decimal('0.0'))
    ])
    category = CategoryField(_('Category'), validators=[
        InputRequired()],  coerce=int)

    # image = FileField(_('Product Image'), validators=[FileAllowed(
    #         ['jpg', 'png', 'jpeg', 'gif'], 'Images only!')
    # ])
    image = FileField(_('Product Image'), validators=[FileRequired()])


def check_duplicate_category(case_sensitive=True):
    def _check_duplicate(form, field):
        if case_sensitive:
            res = Category.query.filter(Category.name.like('%' + field.data + '%')).first()
        else:
            res = Category.query.filter(Category.name.like('%' + field.data + '%')).first()
        if res:
            raise ValidationError(
                'Category name %s already exists' % field.data
            )

    return _check_duplicate


class CategoryForm(FlaskForm):
    name = StringField(_('Name'),
                       validators=[InputRequired(), check_duplicate_category()],
                       render_kw={},
                       )

