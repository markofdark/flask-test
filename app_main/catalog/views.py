import os
from flask import (request, jsonify, Blueprint, render_template, redirect,
                   url_for as flask_url_for, flash, g, abort, current_app)
from flask_wtf import csrf
from app_main import db, ALLOWED_EXTENSIONS, app, cache, mail, celery
from app_main.catalog.decorators import template_or_json
from app_main.catalog.models import (Product, Category, ProductForm, CategoryForm,
                                     product_created, category_created)
from sqlalchemy.orm import join
from werkzeug.utils import secure_filename
from flask_mail import Message
from threading import Thread

from flask_babel import gettext as _
import geoip2.database, geoip2.errors


catalog = Blueprint('catalog', __name__)


@catalog.before_request
def before():
    if request.view_args and 'lang' in request.view_args:
        g.current_lang = request.view_args['lang']
        request.view_args.pop('lang')


@catalog.context_processor
def inject_url_for():
    return {
        'url_for': lambda endpoint, **kwargs: flask_url_for(
            endpoint, lang=g.get('current_lang', 'en'), **kwargs
        )
    }


url_for = inject_url_for()['url_for']

@celery.task()
def send_mail(category_id, category_name):
    with app.app_context():
        category = Category(category_name)
        category.id = category_id
        message = Message(
            "New category added",
            recipients=['customer00@inbox.ru']
        )
        message.body = render_template(
            "category-create-email-text.html",
            category=category
        )
        message.html = render_template(
            "category-create-email-html.html",
            category=category
        )
        mail.send(message)

def allowed_file(filename):
    return '.' in filename and \
            filename.lower().rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@catalog.route('/')
@catalog.route('/<lang>/home')
@template_or_json('home.html')
def home():
    products = Product.query.all()
    current_app.logger.info('Home page with total of %d products' % len(products))
    return {'count': len(products)}
    # return render_template('home.html', product=product)


@catalog.route('/<lang>/product/<id>')
@cache.memoize(60)
def product(id):
    product = Product.query.filter_by(id=id).first()
    if not product:
        current_app.logger.warning('Requested product not found.')
        abort(404)
    return render_template('catalog/product.html', product=product)


@catalog.route('/<lang>/products')
@catalog.route('/<lang>/products/<int:page>')
def products(page=1):
    products = Product.query.paginate(page=page, per_page=10)
    # import pdb; pdb.set_trace()
    return render_template('catalog/products.html', products=products)


# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# @catalog.route('/<lang>/product-create', methods=['GET', 'POST'])
# def create_product():
#     form = ProductForm()
#
#     categories = [(c.id, c.name) for c in Category.query.all()]
#     form.category.choices = categories
#
#     if form.validate_on_submit():
#         name = form.name.data
#         price = form.price.data
#         category = Category.query.get_or_404(form.category.data)
#         image = form.image.data
#         filename = None
#         if image:
#             filename = secure_filename(image.filename)
#             image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
#         product = Product(name, price, category, filename)
#         db.session.add(product)
#         db.session.commit()
#         flash('The product %s has been created' % name, 'success')
#         return redirect(url_for('catalog.product', id=product.id))
#
#     if form.errors:
#         for field, errors in form.errors.items():
#             for error in errors:
#                 flash(error, 'danger')
#
#     return render_template('catalog/product-create.html', form=form)
@catalog.route('/<lang>/product-create', methods=['GET', 'POST'])
def create_product():
    form = ProductForm()

    # categories = [(c.id, c.name) for c in Category.query.all()]
    # form.category.choices = categories

    if form.validate_on_submit():
        name = form.name.data
        price = form.price.data
        category = Category.query.get_or_404(
            form.category.data
        )
        image = form.image.data
        filename = secure_filename(image.filename)
        if allowed_file(filename):
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        reader = geoip2.database.Reader(
            'GeoLite2-City.mmdb'
        )
        try:
            match = reader.city(request.remote_addr)
        except geoip2.errors.AddressNotFoundError:
            match = None
        product = Product(
            name, price, category, filename,
            match and match.location.time_zone or 'Localhost'
        )
        db.session.add(product)
        db.session.commit()
        # product.add_index_to_es()
        product_created.send(app, product=product)
        flash('The product %s has been created' % name, 'success')
        return redirect(url_for('catalog.product', id=product.id))

    if form.errors:
        flash(form.errors, 'danger')

    return render_template('catalog/product-create.html', form=form)


@catalog.route('/<lang>/product-delete/<id>', methods=['GET', 'POST'])
def delete_product(id):
    product = Product.query.filter_by(id=id).first()
    db.session.delete(product)
    db.session.commit()
    flash('The product {} has been deleted'.format(product.name), 'success')
    return redirect(url_for('catalog.products'))
    # return ':)'


# def send_mail(message):
#     with app.app_context():
#         mail.send(message)



# @catalog.route('/category-create', methods=['POST',])
# def create_category():
#     name = request.form.get('name')
#     category = Category(name)
#     db.session.add(category)
#     db.session.commit()
#     category_created.send(app, category=category)
#     #category.add_index_to_es()
#     #mail.send(message)
#     send_mail.apply_async(args=[category.id, category.name])
#     return render_template('catalog/category.html', category=category)


@catalog.route('/<lang>/category-create', methods=['GET', 'POST'])
def create_category():
    form = CategoryForm()

    if form.validate_on_submit():
        name = form.name.data
        category = Category(name)
        db.session.add(category)
        db.session.commit()
        # category_created.send(app, category=category)
        flash('The category %s has been created' % name, 'success')

        # message = Message('New category added', recipients=['customer00@inbox.ru'])
        # # message.body = 'New category "%s" has been created' % category.name
        # message.body = render_template(
        #     'category-create-email-text.html',
        #     category=category
        # )
        # message.html = render_template(
        #     'category-create-email-html.html',
        #     category=category
        # )
        # t = Thread(target=send_mail, args=(message,))
        # t.start()
        send_mail.apply_async(args=[category.id, category.name])
        return redirect(url_for('catalog.category', id=category.id))

    if form.errors:
        flash(form.errors['name'][0], 'danger')

    return render_template('catalog/category-create.html', form=form)


@catalog.route('/<lang>/category/<id>')
def category(id):
    category = Category.query.get_or_404(id)
    return render_template('catalog/category.html', category=category)


@catalog.route('/<lang>/categories')
@cache.cached(timeout=60)
def categories():
    categories = Category.query.all()
    return render_template('catalog/categories.html', categories=categories)


@catalog.route('/<lang>/product-search')
@catalog.route('/<lang>/product-search/<int:page>')
def product_search(page=1):
    name = request.args.get('name')
    price = request.args.get('price')
    category = request.args.get('category')
    products = Product.query
    if name:
        products = products.filter(Product.name.like('%' + name + '%'))
    if price:
        products = products.filter(Product.price == price)
    if category:
        products = products.select_from(join(Product, Category)).filter(
            Category.name.like('%' + category + '%')
        )

    return render_template(
        'catalog/products.html', products=products.paginate(page=page, per_page=10)

    )


# @catalog.route('/product-search-es')
# @catalog.route('/product-search-es/<int:page>')
# def product_search_es(page=1):
#     q = request.args.get('q')
#     products = es.search(index='catalog', query={
#         'query_string': {
#             'query': '*' + q + '*'
#         }
#     })
#     return products['hits']

# from flask_restful import Resource
# from current_app_main import api
#
# class ProductApi(Resource):
#
#     def get(self, id=None):
#         return 'This is a GET response'
#
#     def post(self):
#         return 'This is a POST response'
#
#     def put(self, id):
#         return 'This is a PUT response'
#
#     def delete(self, id):
#         return 'This is a DELETE response'
#
#
# api.add_resource(
#     ProductApi,
#     '/api/product',
#     '/api/product/<int:id>'
# )


