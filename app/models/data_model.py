from . import db

class Corpus(db.Model):
    __tablename__ = 'Corpus'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)

    def __repr__(self):
        return f'Corpus {self.name}'

class Text(db.Model):
    __tablename__ = 'Text'
    id = db.Column(db.Integer, primary_key=True)
    corpus = db.Column(db.Integer, db.ForeignKey('Corpus.id'), nullable=False)
    index = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text(), nullable=False)

    def __repr__(self):
        return f'Text {self.text[:20]} from Corpus {self.corpus}'