"""
Schemas tambahan untuk Wallet — PTS exchange dan top-up.
WalletResponse dan TransactionResponse sudah ada di schemas/task.py.
"""

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ExchangePtsRequest(BaseModel):
    pts_amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)

    @model_validator(mode="after")
    def validate_multiple_of_100(self) -> "ExchangePtsRequest":
        if self.pts_amount % 100 != 0:
            raise ValueError("pts_amount harus kelipatan 100.")
        if self.pts_amount < 100:
            raise ValueError("Minimum exchange adalah 100 PTS.")
        return self


class ExchangePtsResponse(BaseModel):
    pts_deducted: Decimal
    idr_credited: Decimal
    rate_pts: Decimal        # berapa PTS yang dipakai sebagai basis rate
    rate_idr: Decimal        # berapa IDR basis rate tsb
    new_balance_pts: Decimal
    new_balance_idr: Decimal


class TopupWalletRequest(BaseModel):
    """
    Parent top-up their own IDR wallet.
    MVP: no payment gateway — direct credit.
    """
    amount: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    description: str | None = Field(default=None, max_length=200)
