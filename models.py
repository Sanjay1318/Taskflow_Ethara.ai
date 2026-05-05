from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project_memberships = db.relationship('ProjectMember', back_populates='user', cascade='all, delete-orphan')
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assignee_id', back_populates='assignee')
    created_tasks = db.relationship('Task', foreign_keys='Task.creator_id', back_populates='creator')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='active')  # active, archived
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    members = db.relationship('ProjectMember', back_populates='project', cascade='all, delete-orphan')
    tasks = db.relationship('Task', back_populates='project', cascade='all, delete-orphan')

    def to_dict(self, include_members=False, include_stats=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_members:
            data['members'] = [m.to_dict() for m in self.members]
        if include_stats:
            now = datetime.now(timezone.utc)
            total = len(self.tasks)
            done = sum(1 for t in self.tasks if t.status == 'done')
            in_progress = sum(1 for t in self.tasks if t.status == 'in_progress')
            overdue = sum(1 for t in self.tasks if t.due_date and t.status != 'done' and
                         t.due_date.replace(tzinfo=timezone.utc) < now)
            data['stats'] = {
                'total': total,
                'done': done,
                'in_progress': in_progress,
                'todo': sum(1 for t in self.tasks if t.status == 'todo'),
                'overdue': overdue,
                'progress': round((done / total * 100) if total > 0 else 0)
            }
        return data


class ProjectMember(db.Model):
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # admin, member
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', back_populates='project_memberships')

    __table_args__ = (db.UniqueConstraint('project_id', 'user_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'user': self.user.to_dict() if self.user else None
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, review, done
    priority = db.Column(db.String(10), default='medium')  # low, medium, high, critical
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project = db.relationship('Project', back_populates='tasks')
    assignee = db.relationship('User', foreign_keys=[assignee_id], back_populates='assigned_tasks')
    creator = db.relationship('User', foreign_keys=[creator_id], back_populates='created_tasks')
    comments = db.relationship('Comment', back_populates='task', cascade='all, delete-orphan')

    def to_dict(self, include_comments=False):
        now = datetime.now(timezone.utc)
        due = self.due_date.replace(tzinfo=timezone.utc) if self.due_date and self.due_date.tzinfo is None else self.due_date
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'project_id': self.project_id,
            'project_name': self.project.name if self.project else None,
            'assignee_id': self.assignee_id,
            'assignee': self.assignee.to_dict() if self.assignee else None,
            'creator_id': self.creator_id,
            'creator': self.creator.to_dict() if self.creator else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'is_overdue': bool(due and self.status != 'done' and due < now),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_comments:
            data['comments'] = [c.to_dict() for c in self.comments]
        return data


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    task = db.relationship('Task', back_populates='comments')
    user = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'user': self.user.to_dict() if self.user else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
