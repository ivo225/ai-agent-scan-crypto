from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from app.models.report import CoinReport
from app.models.coin import CoinReportSchema # Use the Pydantic schema for creation data

async def create_report(db: AsyncSession, report_data: CoinReportSchema) -> CoinReport:
    """
    Creates a new coin analysis report in the database.

    Args:
        db: The AsyncSession instance.
        report_data: A CoinReportSchema object containing the data for the new report.

    Returns:
        The newly created CoinReport SQLAlchemy object.
    """
    # Create a SQLAlchemy model instance from the Pydantic schema data
    # Use model_dump() for Pydantic V2
    db_report = CoinReport(**report_data.dict()) # Use .dict() for Pydantic V1
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return db_report

async def get_report_by_id(db: AsyncSession, report_id: int) -> Optional[CoinReport]:
    """
    Retrieves a specific report by its ID.

    Args:
        db: The AsyncSession instance.
        report_id: The ID of the report to retrieve.

    Returns:
        The CoinReport object if found, otherwise None.
    """
    result = await db.execute(select(CoinReport).filter(CoinReport.id == report_id))
    return result.scalars().first()

async def get_reports_by_coin_id(db: AsyncSession, coin_id: str, limit: int = 10) -> List[CoinReport]:
    """
    Retrieves the latest reports for a specific coin ID.

    Args:
        db: The AsyncSession instance.
        coin_id: The CoinGecko ID of the coin.
        limit: The maximum number of reports to retrieve (default: 10).

    Returns:
        A list of CoinReport objects, ordered by timestamp descending.
    """
    result = await db.execute(
        select(CoinReport)
        .filter(CoinReport.coin_id == coin_id)
        .order_by(CoinReport.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()
