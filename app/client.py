""" Client App """

from flask import Blueprint

client_bp = Blueprint('client_app', __name__,
                      url_prefix='',
                      static_url_path='',
                      static_folder='./dist/static/',
                      template_folder='./dist/',
                      )
