from datetime import datetime

from . import db


class Collection(db.Model):
    __tablename__ = 'Collection'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)

    def __repr__(self):
        return f'Corpus {self.name}'

    def get_tasks(self):
        all_tasks = {}
        # 1. Search for sequence classification tasks.
        seq_class_tasks = SequenceClassificationTask.query.filter_by(collection=self.id)
        all_tasks['SequenceClassification'] = list(seq_class_tasks)
        return all_tasks

    def get_unannotated_texts(self):
        all_texts = set(Text.query.filter_by(discarded=False, collection=self.id))
        annotated_texts = set(self.get_annotated_texts())
        unannotated_texts = all_texts - annotated_texts
        return list(sorted(unannotated_texts, key=lambda t: t.index))

    def get_annotated_texts(self):
        # TODO Make this stable
        all_tasks = self.get_tasks()
        annotated_texts = set()
        for task_type, tasks in all_tasks.items():
            if task_type == 'SequenceClassification':
                for task in tasks:
                    task_texts = list(
                        Text.query.join(
                            SequenceClassificationAnnotation,
                            Text.id == SequenceClassificationAnnotation.text and SequenceClassificationAnnotation.seq_task == task.id
                        )
                    )

                    task_texts = set(task_texts)
                    annotated_texts.update(task_texts)
            # More Tasks here
        return list(sorted(annotated_texts, key=lambda t: t.index))


class Text(db.Model):
    __tablename__ = 'Text'
    id = db.Column(db.Integer, primary_key=True)
    collection = db.Column(db.Integer, db.ForeignKey('Collection.id'), nullable=False)
    index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text(), nullable=False)
    discarded = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'Text {self.content[:20]} from Collection {self.collection}'


class SequenceClassificationTask(db.Model):
    __tablename__ = "SequenceClassificationTask"
    id = db.Column(db.Integer, primary_key=True)
    al_config = db.Column(db.Integer, db.ForeignKey('ActiveLearningConfigForSequenceClassification.id'))
    collection = db.Column(db.Integer, db.ForeignKey('Collection.id'), nullable=False)

    def get_class_labels(self):
        cls_entries = SeqClassificationTaskToClasses.query.filter_by(seq_class_task=self.id)
        return [c.class_label for c in cls_entries]

    def get_class_label(self, label_id):
        query = list(SeqClassificationTaskToClasses.query.filter_by(seq_class_task=self.id, id=label_id))
        if query:
            return query[0]
        return None

    def get_annotation(self, text):
        query = list(SequenceClassificationAnnotation.query.filter_by(seq_task=self.id, text=text.id))
        if query:
            return self.get_class_label(query[0].class_label)
        return None


class ActiveLearningConfigForSequenceClassification(db.Model):
    __tablename__ = "ActiveLearningConfigForSequenceClassification"
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.Integer, default=1, nullable=False)
    model_name = db.Column(db.String, nullable=False)


class SeqClassificationTaskToClasses(db.Model):
    __tablename__ = "SeqClassificationTaskToClasses"
    id = db.Column(db.Integer, primary_key=True)
    seq_class_task = db.Column(db.Integer, db.ForeignKey('SequenceClassificationTask.id'), nullable=False)
    class_label = db.Column(db.String(120), nullable=False)


class SequenceClassificationAnnotation(db.Model):
    __tablename__ = "SequenceClassificationAnnotation"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Integer, db.ForeignKey('Text.id'))
    seq_task = db.Column(db.Integer, db.ForeignKey('SequenceClassificationTask.id'), nullable=False)
    class_label = db.Column(db.Integer, db.ForeignKey('SeqClassificationTaskToClasses.id'), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class TextQueue(db.Model):
    __tablename__ = "TextQueque"
    id = db.Column(db.Integer, primary_key=True)
    collection = db.Column(db.Integer, db.ForeignKey('Collection.id'), nullable=False)
    text = db.Column(db.Integer, db.ForeignKey('Text.id'), unique=True)
