from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product
    from app.models.warehouse import Warehouse
    from app.models.inventory import Inventory
    from app.models.customer import Customer
    from app.models.order import Order


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="organization"
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="organization"
    )

    warehouses: Mapped[list["Warehouse"]] = relationship(
        back_populates="organization"
    )

    inventories: Mapped[list["Inventory"]] = relationship(
        back_populates="organization"
    )
    
    customers: Mapped[list["Customer"]] = relationship(
        back_populates="organization"
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="organization"
    )