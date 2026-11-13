from .extensions import db


class Depot(db.Model):
    __tablename__ = "depots"

    depot_id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)


class Handler(db.Model):
    __tablename__ = "handlers"

    handler_id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    depot_id = db.Column(db.String(10), db.ForeignKey("depots.depot_id"), nullable=False)
    available = db.Column(db.Boolean, nullable=False, default=True)
    maximum_capacity = db.Column(db.Integer, nullable=False)
    current_workload = db.Column(db.Integer, nullable=False, default=0)
    assigned_categories = db.Column(db.JSON, nullable=False)


class Report(db.Model):
    __tablename__ = "reports"

    report_id = db.Column(db.String(100), primary_key=True)
    original_request = db.Column(db.JSON, nullable=False)
    reporter_details = db.Column(db.JSON, nullable=False)
    identifier = db.Column(db.String(100), nullable=False)
    issue_code = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    emergency = db.Column(db.Boolean, nullable=False, default=False)
    severe_accident = db.Column(db.Boolean, nullable=False, default=False)
    dangerous_electrical_fault = db.Column(db.Boolean, nullable=False, default=False)
    dfa_valid = db.Column(db.Boolean, nullable=False)
    regex_valid = db.Column(db.Boolean, nullable=False)
    validators_agree = db.Column(db.Boolean, nullable=False)
    validation_status = db.Column(db.String(20), nullable=False)
    validation_reason = db.Column(db.Text, nullable=False)
    classification_category = db.Column(db.String(30), nullable=True)
    classification_reason = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    current_status = db.Column(db.String(30), nullable=False, default="Pending")
    submission_timestamp = db.Column(db.DateTime, nullable=False)


class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey("reports.report_id"), unique=True, nullable=False)
    depot_id = db.Column(db.String(10), db.ForeignKey("depots.depot_id"), nullable=True)
    handler_id = db.Column(db.String(20), db.ForeignKey("handlers.handler_id"), nullable=True)
    status = db.Column(db.String(30), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=False)


class RoutingDecision(db.Model):
    __tablename__ = "routing_decisions"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey("reports.report_id"), unique=True, nullable=False)
    identifier = db.Column(db.String(100), nullable=False)
    route_key = db.Column(db.String(1), nullable=True)
    distance_lookup = db.Column(db.JSON, nullable=False)
    selected_depot_id = db.Column(db.String(10), nullable=True)
    selected_handler_id = db.Column(db.String(20), nullable=True)
    priority = db.Column(db.String(20), nullable=False)
    assignment_timestamp = db.Column(db.DateTime, nullable=False)
    submission_timestamp = db.Column(db.DateTime, nullable=False)
    assignment_status = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.Text, nullable=False)


class StatusHistory(db.Model):
    __tablename__ = "status_history"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey("reports.report_id"), nullable=False)
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_at = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=True)


class QueueEntry(db.Model):
    __tablename__ = "queue_entries"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey("reports.report_id"), unique=True, nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    priority_rank = db.Column(db.Integer, nullable=False)
    submission_timestamp = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), nullable=False)
    reason = db.Column(db.Text, nullable=False)


class TimestampedModel:
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False,
    )
