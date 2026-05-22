import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ── Enums (like Java Enum) ─────────────────────────────────────────────────

class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# ── Workflow Table ─────────────────────────────────────────────────────────

class Workflow(Base):
    __tablename__ = "workflows"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=WorkflowStatus.PENDING)

    # Input and Output
    input_data: Mapped[str] = mapped_column(Text, nullable=True)   # user input
    output_data: Mapped[str] = mapped_column(Text, nullable=True)  # final result
    confidence_score: Mapped[float] = mapped_column(nullable=True) # ← ADD THIS!

    # Audit fields (like @CreatedDate, @LastModifiedDate)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationship (like @OneToMany in JPA)
    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


# ── WorkflowStep Table ─────────────────────────────────────────────────────

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign Key (like @ManyToOne in JPA)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))

    # Core fields
    step_name: Mapped[str] = mapped_column(String(255))  # e.g. "PlannerAgent"
    step_order: Mapped[int] = mapped_column()             # 1, 2, 3 ...
    status: Mapped[str] = mapped_column(String(50), default=StepStatus.PENDING)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Input/Output of this step
    input_data: Mapped[str] = mapped_column(Text, nullable=True)
    output_data: Mapped[str] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(default=0)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship back to Workflow
    workflow: Mapped["Workflow"] = relationship(back_populates="steps")


# ── ExecutionLog Table ─────────────────────────────────────────────────────

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Foreign Key
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"))

    # Log details
    level: Mapped[str] = mapped_column(String(20))   # INFO, WARNING, ERROR
    message: Mapped[str] = mapped_column(Text)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationship
    workflow: Mapped["Workflow"] = relationship(back_populates="logs")



# -- User table ─────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        default=True
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), 
        onupdate=func.now()
    )



# Work flow approval
class WorkflowApproval(Base):
    __tablename__ = "workflow_approvals"

    id: Mapped[str] = mapped_column(
        String, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    workflow_id: Mapped[str] = mapped_column(
        ForeignKey("workflows.id")
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING"
    )
    reason: Mapped[str] = mapped_column(
        Text, nullable=True
    )
    confidence_score: Mapped[float] = mapped_column(
        nullable=True
    )
    reviewed_by: Mapped[str] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(),
        onupdate=func.now()
    )