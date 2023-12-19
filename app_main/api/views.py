import json

from flask import Blueprint, abort, request
from flask.views import MethodView
from flask_wtf.csrf import validate_csrf

from app_main.catalog.models import Product, Category
from flask_restful import Resource, reqparse
from app_main import restapi, db

api_blueprint = Blueprint('api', __name__)

parser = reqparse.RequestParser()
parser.add_argument('name', type=str)
parser.add_argument('price', type=float)
parser.add_argument('category', type=dict)
parser.add_argument('image', type=str)


class ProductApi(Resource):

    def get(self, id=None, page=1):
        if not id:
            products = Product.query.paginate(page=page, per_page=10).items
        else:
            products = [Product.query.get(id)]
        if not products:
            abort(404)
        res = {}
        for product in products:
            res[product.id] = {
                'name': product.name,
                'price': product.price,
                'category': product.category.name,
                'image': product.image_path
            }
        return json.dumps(res)

    def post(self):
        args = parser.parse_args()
        name = args['name']
        price = args['price']
        category_name = args['category']['name']
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            category = Category(category_name)
        image = args['image']
        product = Product(name, price, category, image)
        db.session.add(product)
        db.session.commit()
        res = {product.id: {
            'name': product.name,
            'price': product.price,
            'category': product.category.name,
            'image': product.image_path
        }}
        return json.dumps(res)

    def put(self, id):
        args = parser.parse_args()
        name = args['name']
        price = args['price']
        category_name = args['category']['name']
        category = Category.query.filter_by(name=category_name).first()
        image = args['image']
        Product.query.filter_by(id=id).update({
            'name': name,
            'price': price,
            'category_id': category.id,
            'image_path': image
        })
        db.session.commit()
        product = Product.query.get_or_404(id)
        res = {product.id: {
            'name': product.name,
            'price': product.price,
            'category': product.category.name,
            'image': product.image_path
        }}
        return json.dumps(res)

    def delete(self, id):
        product = Product.query.filter_by(id=id)
        product.delete()
        db.session.commit()
        return json.dumps({'response': 'Success'})


restapi.add_resource(
    ProductApi,
    '/<lang>/api/product',
    '/<lang>/api/product/<int:id>'
)

# def csrf_exempt(view_func):
#     def decorated(*args, **kwargs):
#         if request.method == 'POST':
#             return view_func(*args, **kwargs)
#         else:
#             validate_csrf(request.cookies.get('csrf_token'))
#             return view_func(*args, **kwargs)
#
#     return decorated


# class ProductView(MethodView):
#
#     def get(self, id=None, page=1):
#         if not id:
#             products = Product.query.paginate(page=page, per_page=10).items
#             res = {}
#             for product in products:
#                 res[product.id] = {
#                     'name': product.name,
#                     'price': product.price,
#                     'category': product.category.name
#                 }
#         else:
#             product = Product.query.filter_by(id=id).first()
#             if not product:
#                 abort(404)
#             res = json.dumps({
#                 'name': product.name,
#                 'price': product.price,
#                 'category': product.category.name
#             })
#         return res
#
#     def post(self):
#         name = request.form.get('name')
#         price = request.form.get('price')
#         category_name = request.form.get('category')
#         category = Category.query.filter_by(name=category_name).first()
#         if not category:
#             category = Category(category_name)
#         image = request.form.get('image')
#         product = Product(name, price, category, image)
#         db.session.add(product)
#         db.session.commit()
#         return 'Product %s created' % name
#
#
# product_view = ProductView.as_view('product_view')
# api_blueprint.add_url_rule('/api/products', view_func=product_view, methods=['GET', 'POST'])
# api_blueprint.add_url_rule('/api/products/<int:id>', view_func=product_view,
#                            methods=['GET', 'PUT', 'DELETE'])
