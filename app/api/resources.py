"""
REST API Resource Routing
http://flask-restplus.readthedocs.io
TODO Refactor into a fully fledged REST-API
"""
import os
import tempfile
import time

from flask import current_app, send_file
from flask import request
from flask_restx import Resource

from . import api_rest
from .security import require_auth
from ..active_learning import init_active_learning_component
from ..schemes import *


class SecureResource(Resource):
    """ Calls require_auth decorator on all requests """
    method_decorators = [require_auth]


@api_rest.route('/resource/<string:resource_id>')
class ResourceOne(Resource):
    """
    Unsecure Resource Class: Inherit from Resource
    Only used for debugging.
    """
    def get(self, resource_id):
        timestamp = datetime.utcnow().isoformat()
        return {'timestamp': timestamp, 'id': resource_id}

    def post(self, resource_id):
        json_payload = request.json
        return {'timestamp': json_payload}, 201


@api_rest.route('/secure-resource/<string:resource_id>')
class SecureResourceOne(SecureResource):
    """
    Secure Resource Class: Inherit from Resource
    Only used for debugging.
    """

    def get(self, resource_id):
        timestamp = datetime.utcnow().isoformat()
        return {'timestamp': timestamp}


@api_rest.route('/test/<string:id>')
class TestResource(Resource):
    """
    Only used for debugging.
    """
    def get(self, id):
        timestamp = datetime.utcnow().isoformat()
        return {
            'hello': 'world',
            'timestamp': timestamp,
            'id': id
        }


@api_rest.route('/text')
class AllTexts(Resource):
    """
    GET Endpoint: Query a list of all texts in the database.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_schema = TextSchema(many=True)

    def get(self):
        all_texts = Text.query.all()
        return self.text_schema.dump(all_texts)


@api_rest.route('/text/<int:id>')
class SingleText(Resource):
    """
    GET Endpoint: Query a single text by its Database-ID.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_schema = TextSchema()

    def get(self, id):
        text = Text.query.get(id)
        return self.text_schema.dump(text)


@api_rest.route('/text/<int:text_id>/discard')
class DiscardText(Resource):
    """
    GET Endpoint:  Discard a single text (given by its Database-ID)
    Discarding a text means excluding it for the annotation process.
    """
    def get(self, text_id):
        text = Text.query.get(text_id)
        text.discarded = True
        db.session.add(text)
        db.session.commit()
        return {'success': True}, 200


@api_rest.route('/collection')
class AllCollectionsResource(Resource):
    """
    GET Endpoint: Query a list of all collections.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection_schema = CollectionSchema(many=True)

    def get(self):
        collections = Collection.query.all()
        return self.collection_schema.dump(collections)


# TODO Remove ASAP
@api_rest.route('/collection/<int:collection_id>/text-index/<int:text_index>')
class TextFromProjectByIndex(Resource):
    """
    GET Endpoint: (Not used anymore) Query a text from a distinct collection by its index in the Database-Order.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_schema = TextSchema()

    def get(self, collection_id, text_index):
        text = list(Text.query.filter_by(collection=collection_id))[text_index]
        return self.text_schema.dump(text)


@api_rest.route("/text/<int:text_id>/seq-class-task/<int:task_id>/annotation")
class SingleAnnotationEndpoint(Resource):
    """
    GET Endpoint: Query an existing annotation for a distinct task for a single text.
    POST Endpoint: Add an annotation to the database. Overwrites existing ones.
    Both Tasks and Texts are identified by their Database-IDs
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seq_class_to_class_schema = SequenceClassificationTaskSchema()

    def get(self, text_id, task_id):
        annotation = list(SequenceClassificationAnnotation.query.filter_by(text=text_id, seq_task=task_id))
        if not annotation:
            return None, 200
        annotation = annotation[0]
        class_label_entry = SeqClassificationTaskToClasses.query.get(annotation.class_label)
        return self.seq_class_to_class_schema.dump(class_label_entry)

    def post(self, text_id, task_id):
        data = request.json
        class_label = data['class']
        task = SequenceClassificationTask.query.get(task_id)
        possible_classes = SeqClassificationTaskToClasses.query.filter_by(seq_class_task=task.id)
        possible_classes = [c.class_label for c in possible_classes]
        if class_label not in possible_classes:
            return {'error': 'Invalid class label'}, 500

        existing_annotation = list(SequenceClassificationAnnotation.query.filter_by(text=text_id, seq_task=task_id))
        if existing_annotation:
            db.session.delete(existing_annotation[0])
            db.session.commit()

        class_label_obj = list(
            SeqClassificationTaskToClasses.query.filter_by(class_label=class_label, seq_class_task=task_id)
        )[0]
        annotation = SequenceClassificationAnnotation(
            text=text_id,
            seq_task=task_id,
            class_label=class_label_obj.id
        )
        try:
            db.session.add(annotation)
            db.session.commit()
            return {'success': True}, 200
        except Exception as e:
            return {"error": e}, 500


@api_rest.route('/collection/<int:collection_id>/tasks')
class TasksOfCollectionResource(Resource):
    """
    GET Endpoint: Query a list of all tasks associated the the current collection.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seq_task_schema = SequenceClassificationTaskSchema(many=True)

    def get(self, collection_id):
        tasks_dumps = []
        # Get sequence classification tasks
        seq_class_tasks = SequenceClassificationTask.query.filter_by(collection=collection_id)
        seq_class_tasks_dumps = self.seq_task_schema.dump(seq_class_tasks)
        for t in seq_class_tasks_dumps:
            t['type'] = "SequenceClassification"
            tasks_dumps.append(t)
        return tasks_dumps


@api_rest.route('/sequence-classification/<int:task_id>')
class SequenceClassificationConfigurationResource(Resource):
    """
    GET Endpoint: Returns a list of possible class labels for the given seq-class task.
    """
    def get(self, task_id):
        # get classes
        classes = [
            c.class_label for c in SeqClassificationTaskToClasses.query.filter_by(seq_class_task=task_id)
        ]
        return {'classLabels': classes}


@api_rest.route('/collection/<int:collection_id>/next')
class NextTextResource(Resource):
    """
    GET Endpoint: Multipurpose Endpoint to get the next resource during annotation.
    If active learning is enabled for a one the tasks the active learning component will be initiated and used
    for querying the next instances.

    TODO: This one should carefully be refactored as soon as new task-types are added.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_schema = TextSchema(many=True)
        self.al_components = {}

    def get(self, collection_id):
        queue = []
        # 0. Get collection
        collection = Collection.query.get(collection_id)
        if collection is None:
            return {'error': 'Invalid collection id'}, 400

        # 1. Get tasks
        all_tasks = collection.get_tasks()
        for task_type, tasks in all_tasks.items():
            if task_type == 'SequenceClassification':
                for seq_task in tasks:
                    if (al_config_id := seq_task.al_config) is not None:
                        # Check if enabled task al comp is not already loaded
                        if f'SeqClass-{al_config_id}' not in self.al_components:
                            al_config = ActiveLearningConfigForSequenceClassification.query.get(al_config_id)
                            component = init_active_learning_component(al_config)
                            self.al_components[f'SeqClass-{al_config_id}'] = component

                        # Load component fit it and let it rank
                        pool_texts_query = list(collection.get_unannotated_texts())
                        pool_texts = [t.content for t in pool_texts_query]
                        if not pool_texts:
                            return {'error': 'All texts are annotated', 'finished': True}, 404
                        train_text_query = list(collection.get_annotated_texts())
                        train_labels = [seq_task.get_annotation(t).class_label for t in train_text_query]
                        if len(set(train_labels)) < 2:
                            break
                        train_texts = [t.content for t in train_text_query]
                        if len(train_texts) < 2:
                            break


                        component = self.al_components[f'SeqClass-{al_config_id}']
                        start = time.time()
                        component.fit(train_texts, train_labels)
                        idx = component.rank(pool_texts)[0]
                        queue.append(pool_texts_query[idx])
                        time_delta = time.time() - start
                        current_app.logger.info(f'Querying using active learning. Took {time_delta} seconds')

        if not queue:
            unannotated_texts = collection.get_unannotated_texts()
            if not unannotated_texts:
                return {'error': 'All texts are annotated', 'finished': True}, 404
            queue.append(unannotated_texts[0])

        return list(set([entry['id'] for entry in self.text_schema.dump(queue)]))


@api_rest.route('/collection/add')
class UploadCollectionResource(Resource):
    """
    POST Endpoint: Upload a new collection configuration json file.
    TODO: Using a terminal emulation process to invoke the cli-tool for processing the config file yields more
    disadvantages than advantages. Should be refactored as soon as the cli is moved into the web application itself.
    """
    def post(self):
        """
        TODO it would yield multiple advantages to further refactor the cli tool
        and to call the creation function directly from here but for now it works quite well...
        """
        file = request.files['file']
        with tempfile.NamedTemporaryFile('wb') as tmp:
            tmp.write(file.read())
            cli_stream = os.popen(f'python cli.py from-json {tmp.name}')
            output = cli_stream.read()
            return {'message': output}, 200


@api_rest.route('/collection/<int:collection_id>/download')
class DownloadCollectionResource(Resource):
    """
    GET Endpoint: Download as json file of the given collection with all its configurations and annotations.
    """
    def get(self, collection_id):
        collection = Collection.query.get(collection_id)
        if collection is None:
            return {'error': f'{collection_id} is not a valid CollectionID'}, 404
        with tempfile.NamedTemporaryFile('w') as tmp:
            collection_name = collection.name
            stream = os.popen(f'python cli.py to-json -n {collection_name} {tmp.name}')
            _ = stream.read()
            current_app.logger.info(f'Wrote JSON data for collection {collection_name} to temp file {tmp.name}')
            return send_file(
                tmp.name,
                as_attachment=True,
                attachment_filename=f'{"-".join(collection_name.split())}.json'
            )


@api_rest.route('/collection/<int:collection_id>/progress')
class CollectionProgressResource(Resource):
    """
    GET Endpoint: Returns the number of annotated resources and the number of pending resources for the
    given endpoint.
    """
    def get(self, collection_id):
        collection = Collection.query.get(collection_id)
        if collection is None:
            return {'error': f'{collection_id} is not a valid CollectionID'}, 404
        n_annotated = len(collection.get_annotated_texts())
        n_unannotated = len(collection.get_unannotated_texts())
        return {'annotated': n_annotated, 'unannotated': n_unannotated}, 200
