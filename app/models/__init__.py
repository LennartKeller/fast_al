from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .data_model import *
from .queries import *
