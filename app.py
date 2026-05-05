import os
from flask import Flask, jsonify, send_from_directory
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from models import db
from config import config


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config[config_name])

    # Handle Railway postgres URL (postgres:// -> postgresql://)
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    if db_url and db_url.startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace('postgres://', 'postgresql://', 1)

    # Extensions
    db.init_app(app)
    JWTManager(app)
    CORS(app, supports_credentials=True)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.projects import projects_bp
    from routes.tasks import tasks_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)

    # Health check
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'message': 'TaskFlow API is running'})

    # Serve frontend for all non-API routes (SPA)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_spa(path):
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.template_folder, 'index.html')

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    with app.app_context():
        db.create_all()

    return app
