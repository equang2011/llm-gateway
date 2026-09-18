from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base



class GatewayApiKey(Base):
    __tablename__ = "gateway_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)

    app_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    key_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    requests_per_minute: Mapped[int] = mapped_column(
        nullable=False,
        default=30,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )