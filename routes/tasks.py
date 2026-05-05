from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Task, Project, ProjectMember, Comment, User
from datetime import datetime, timezone

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api')

VALID_STATUSES = ('todo', 'in_progress', 'review', 'done')
VALID_PRIORITIES = ('low', 'medium', 'high', 'critical')


def get_user_role(project_id, user_id):
    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    return member.role if member else None


def parse_due_date(date_str):
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f'Invalid date format: {date_str}')


# --- Tasks under a project ---

@tasks_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
@jwt_required()
def list_project_tasks(project_id):
    user_id = int(get_jwt_identity())
    if not get_user_role(project_id, user_id):
        return jsonify({'error': 'Access denied'}), 403

    q = Task.query.filter_by(project_id=project_id)

    # Filters
    status = request.args.get('status')
    priority = request.args.get('priority')
    assignee = request.args.get('assignee_id')

    if status and status in VALID_STATUSES:
        q = q.filter_by(status=status)
    if priority and priority in VALID_PRIORITIES:
        q = q.filter_by(priority=priority)
    if assignee:
        q = q.filter_by(assignee_id=int(assignee))

    tasks = q.order_by(Task.created_at.desc()).all()
    return jsonify({'tasks': [t.to_dict() for t in tasks]})


@tasks_bp.route('/projects/<int:project_id>/tasks', methods=['POST'])
@jwt_required()
def create_task(project_id):
    user_id = int(get_jwt_identity())
    role = get_user_role(project_id, user_id)
    if not role:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title = data.get('title', '').strip()
    if not title or len(title) < 2:
        return jsonify({'error': 'Task title must be at least 2 characters'}), 400

    status = data.get('status', 'todo')
    if status not in VALID_STATUSES:
        return jsonify({'error': f'Status must be one of: {", ".join(VALID_STATUSES)}'}), 400

    priority = data.get('priority', 'medium')
    if priority not in VALID_PRIORITIES:
        return jsonify({'error': f'Priority must be one of: {", ".join(VALID_PRIORITIES)}'}), 400

    # Validate assignee is a project member
    assignee_id = data.get('assignee_id')
    if assignee_id:
        if not get_user_role(project_id, assignee_id):
            return jsonify({'error': 'Assignee must be a project member'}), 400

    try:
        due_date = parse_due_date(data.get('due_date'))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    task = Task(
        title=title,
        description=data.get('description', '').strip(),
        status=status,
        priority=priority,
        project_id=project_id,
        assignee_id=assignee_id,
        creator_id=user_id,
        due_date=due_date
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({'task': task.to_dict()}), 201


@tasks_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    if not get_user_role(task.project_id, user_id):
        return jsonify({'error': 'Access denied'}), 403
    return jsonify({'task': task.to_dict(include_comments=True)})


@tasks_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    role = get_user_role(task.project_id, user_id)
    if not role:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Members can only update their own tasks (or if they're assigned)
    if role == 'member' and task.creator_id != user_id and task.assignee_id != user_id:
        return jsonify({'error': 'You can only edit tasks you created or are assigned to'}), 403

    if 'title' in data:
        title = data['title'].strip()
        if not title:
            return jsonify({'error': 'Title cannot be empty'}), 400
        task.title = title

    if 'description' in data:
        task.description = data['description'].strip()

    if 'status' in data:
        if data['status'] not in VALID_STATUSES:
            return jsonify({'error': f'Invalid status'}), 400
        task.status = data['status']

    if 'priority' in data:
        if data['priority'] not in VALID_PRIORITIES:
            return jsonify({'error': 'Invalid priority'}), 400
        task.priority = data['priority']

    if 'assignee_id' in data:
        assignee_id = data['assignee_id']
        if assignee_id and not get_user_role(task.project_id, assignee_id):
            return jsonify({'error': 'Assignee must be a project member'}), 400
        task.assignee_id = assignee_id

    if 'due_date' in data:
        try:
            task.due_date = parse_due_date(data['due_date'])
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({'task': task.to_dict()})


@tasks_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    role = get_user_role(task.project_id, user_id)
    if not role:
        return jsonify({'error': 'Access denied'}), 403

    if role == 'member' and task.creator_id != user_id:
        return jsonify({'error': 'Only task creator or admin can delete this task'}), 403

    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted successfully'})


# --- Comments ---

@tasks_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(task_id):
    user_id = int(get_jwt_identity())
    task = Task.query.get_or_404(task_id)
    if not get_user_role(task.project_id, user_id):
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Comment cannot be empty'}), 400

    comment = Comment(content=content, task_id=task_id, user_id=user_id)
    db.session.add(comment)
    db.session.commit()
    return jsonify({'comment': comment.to_dict()}), 201


# --- Dashboard ---

@tasks_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    user_id = int(get_jwt_identity())
    now = datetime.now(timezone.utc)

    # All projects user is in
    memberships = ProjectMember.query.filter_by(user_id=user_id).all()
    project_ids = [m.project_id for m in memberships]

    # Tasks across all projects
    all_tasks = Task.query.filter(Task.project_id.in_(project_ids)).all() if project_ids else []

    # My assigned tasks
    my_tasks = [t for t in all_tasks if t.assignee_id == user_id]

    # Overdue
    overdue = [t for t in all_tasks if t.due_date and t.status != 'done' and
               t.due_date.replace(tzinfo=timezone.utc) < now]

    # Status breakdown
    status_counts = {}
    for status in VALID_STATUSES:
        status_counts[status] = sum(1 for t in all_tasks if t.status == status)

    # Priority breakdown
    priority_counts = {}
    for priority in VALID_PRIORITIES:
        priority_counts[priority] = sum(1 for t in all_tasks if t.priority == priority)

    # Recent tasks
    recent = sorted(all_tasks, key=lambda t: t.created_at, reverse=True)[:10]

    return jsonify({
        'stats': {
            'total_projects': len(project_ids),
            'total_tasks': len(all_tasks),
            'my_tasks': len(my_tasks),
            'overdue_tasks': len(overdue),
            'by_status': status_counts,
            'by_priority': priority_counts
        },
        'my_tasks': [t.to_dict() for t in my_tasks[:10]],
        'overdue_tasks': [t.to_dict() for t in overdue[:10]],
        'recent_tasks': [t.to_dict() for t in recent],
    })
