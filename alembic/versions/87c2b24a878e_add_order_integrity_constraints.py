
"""add order integrity constraints

Revision ID: 87c2b24a878e
Revises: b373bb731e52
Create Date: 2026-09-17 20:16:24.574431
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "87c2b24a878e"
down_revision: Union[str, Sequence[str], None] = "b373bb731e52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_orders_total_amount_non_negative",
        "orders",
        "total_amount >= 0",
    )

    op.create_check_constraint(
        "ck_order_items_quantity_positive",
        "order_items",
        "quantity > 0",
    )

    op.create_check_constraint(
        "ck_order_items_unit_price_non_negative",
        "order_items",
        "unit_price >= 0",
    )

    op.create_check_constraint(
        "ck_order_items_subtotal_non_negative",
        "order_items",
        "subtotal >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_order_items_subtotal_non_negative",
        "order_items",
        type_="check",
    )

    op.drop_constraint(
        "ck_order_items_unit_price_non_negative",
        "order_items",
        type_="check",
    )

    op.drop_constraint(
        "ck_order_items_quantity_positive",
        "order_items",
        type_="check",
    )

    op.drop_constraint(
        "ck_orders_total_amount_non_negative",
        "orders",
        type_="check",
    )