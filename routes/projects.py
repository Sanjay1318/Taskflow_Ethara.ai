from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Project, ProjectMember, User, Task
from datetime import datetime, timezone

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')


def get_user_role(project_id, user_id):
    """Get user's role in a project, or None if not a member."""
    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    return member.role if member else None


@projects_bp.route('', methods=['GET'])
@jwt_required()
def list_projects():
    user_id = int(get_jwt_identity())
    memberships = ProjectMember.query.filter_by(user_id=user_id).all()
    projects = []
    for m in memberships:
        p = m.project.to_dict(include_stats=True)
        p['my_role'] = m.role
        projects.append(p)
    return jsonify({'projects': projects})


@projects_bp.route('', methods=['POST'])
@jwt_required()
def create_project():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    if not name or len(name) < 2:
        return jsonify({'error': 'Project name must be at least 2 characters'}), 400

    project = Project(
        name=name,
        description=data.get('description', '').strip()
    )
    db.session.add(project)
    db.session.flush()

    # Creator becomes admin
    member = ProjectMember(project_id=project.id, user_id=user_id, role='admin')
    db.session.add(member)
    db.session.commit()

    result = project.to_dict(include_members=True, include_stats=True)
    result['my_role'] = 'admin'
    return jsonify({'project': result}), 201


@projects_bp.route('/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    user_id = int(get_jwt_identity())
    role = get_user_role(project_id, user_id)
    if not role:
        return jsonify({'error': 'Access denied'}), 403

    project = Project.query.get_or_404(project_id)
    result = project.to_dict(include_members=True, include_stats=True)
    result['my_role'] = role
    return jsonify({'project': result})


@projects_bp.route('/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    user_id = int(get_jwt_identity())
    role = get_user_role(project_id, user_id)
    if role != 'admin':
        return jsonify({'error': 'Only admins can update projects'}), 403

    project = Project.query.get_or_404(project_id)
    data = request.get_json()

    if 'name' in data:
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Project name cannot be empty'}), 400
        project.name = name
    if 'description' in data:
        project.description = data['description'].strip()
    if 'status' in data and data['status'] in ('active', 'archived'):
        project.status = data['status']

    project.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'project': project.to_dict(include_members=True, include_stats=True)})


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    user_id = int(get_jwt_identity())
    role = get_user_role(project_id, user_id)
    if role != 'admin':
        return jsonify({'error': 'Only admins can delete projects'}), 403

    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'})


# --- Member Management ---

@projects_bp.route('/<int:project_id>/members', methods=['GET'])
@jwt_required()
def list_members(project_id):
    user_id = int(get_jwt_identity())
    if not get_user_role(project_id, user_id):
        return jsonify({'error': 'Access denied'}), 403

    members = ProjectMember.query.filter_by(project_id=project_id).all()
    return jsonify({'members': [m.to_dict() for m in members]})


@projects_bp.route('/<int:project_id>/members', methods=['POST'])
@jwt_required()
def add_member(project_id):
    user_id = int(get_jwt_identity())
    role = get_user_role(project_id, user_id)
    if role != 'admin':
        return jsonify({'error': 'Only admins can add members'}), 403

    data = request.get_json()
    email = data.get('email', '').strip().lower()
    new_role = data.get('role', 'member')

    if not email:
        return jsonify({'error': 'Email is required'}), 400
    if new_role not in ('admin', 'member'):
        return jsonify({'error': 'Role must be admin or member'}), 400

    target_user = User.query.filter_by(email=email).first()
    if not target_user:
        return jsonify({'error': 'User not found with that email'}), 404

    existing = ProjectMember.query.filter_by(project_id=project_id, user_id=target_user.id).first()
    if existing:
        return jsonify({'error': 'User is already a member'}), 409

    member = ProjectMember(project_id=project_id, user_id=target_user.id, role=new_role)
    db.session.add(member)
    db.session.commit()
    return jsonify({'member': member.to_dict()}), 201


@projects_bp.route('/<int:project_id>/members/<int:target_user_id>', methods=['PUT'])
@jwt_required()
def update_member_role(project_id, target_user_id):
    user_id = int(get_jwt_identity())
    if get_user_role(project_id, user_id) != 'admin':
        return jsonify({'error': 'Only admins can change roles'}), 403

    if user_id == target_user_id:
        return jsonify({'error': 'Cannot change your own role'}), 400

    data = request.get_json()
    new_role = data.get('role')
    if new_role not in ('admin', 'member'):
        return jsonify({'error': 'Role must be admin or member'}), 400

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=target_user_id).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    member.role = new_role
    db.session.commit()
    return jsonify({'member': member.to_dict()})


@projects_bp.route('/<int:project_id>/members/<int:target_user_id>', methods=['DELETE'])
@jwt_required()
def remove_member(project_id, target_user_id):
    user_id = int(get_jwt_identity())
    role = get_user_role(project_id, user_id)

    # Admins can remove anyone except themselves; members can only remove themselves
    if role != 'admin' and user_id != target_user_id:
        return jsonify({'error': 'Access denied'}), 403

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=target_user_id).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    db.session.delete(member)
    db.session.commit()
    return jsonify({'message': 'Member removed successfully'})
