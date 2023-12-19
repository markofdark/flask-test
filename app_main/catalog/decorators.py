from functools import wraps
from flask import request, jsonify, render_template


def template_or_json(template=None):
    """Return a dict from your view and this will either
    pass it to a template or render json"""

    def decorated(f):
        @wraps(f)
        def decorated_fn(*args, **kwargs):
            ctx = f(*args, **kwargs)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(ctx)
            else:
                return render_template(template, **ctx)
        return decorated_fn
    return decorated
