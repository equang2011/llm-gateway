from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


from app.database import Base



class GatewayApiKey(Base):
    __tablename__ = "gateway_api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)

    app_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
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