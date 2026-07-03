"""Report generation: CSV, Excel, and PDF exports."""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from etl.config import AppConfig
from etl.database import DatabaseManager

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates operational reports in multiple formats."""

    def __init__(self, config: AppConfig, db: DatabaseManager) -> None:
        self.config = config
        self.db = db
        self.output_dir = Path(config.report_output_dir)
        self.export_dir = Path(config.export_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_exceptions_csv(self, as_of_date: date) -> Path:
        query = """
            SELECT e.*, f.ticker as fund_ticker
            FROM exceptions e
            LEFT JOIN funds f ON e.fund_id = f.fund_id
            WHERE e.as_of_date = :dt
            ORDER BY e.severity DESC, e.exception_type
        """
        df = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        filepath = self.export_dir / f"exceptions_{as_of_date.isoformat()}.csv"
        df.to_csv(filepath, index=False)
        logger.info("Exported exceptions to %s", filepath)
        return filepath

    def export_nav_csv(self, as_of_date: date) -> Path:
        query = """
            SELECT f.ticker, f.fund_name, n.*
            FROM nav_history n
            JOIN funds f ON n.fund_id = f.fund_id
            WHERE n.nav_date = :dt
        """
        df = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        filepath = self.export_dir / f"nav_{as_of_date.isoformat()}.csv"
        df.to_csv(filepath, index=False)
        return filepath

    def export_trades_csv(self, as_of_date: date) -> Path:
        query = """
            SELECT t.*, f.ticker as fund_ticker, s.ticker as security_ticker
            FROM trades t
            JOIN funds f ON t.fund_id = f.fund_id
            JOIN securities s ON t.security_id = s.security_id
            WHERE t.trade_date = :dt
        """
        df = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
        filepath = self.export_dir / f"trades_{as_of_date.isoformat()}.csv"
        df.to_csv(filepath, index=False)
        return filepath

    def generate_excel_summary(self, as_of_date: date) -> Path:
        filepath = self.output_dir / f"daily_summary_{as_of_date.isoformat()}.xlsx"

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            sheets = {
                "NAV": """
                    SELECT f.ticker, n.nav_per_share, n.total_nav, n.daily_return,
                           n.benchmark_return, n.tracking_error
                    FROM nav_history n JOIN funds f ON n.fund_id = f.fund_id
                    WHERE n.nav_date = :dt
                """,
                "Exceptions": """
                    SELECT f.ticker, e.exception_type, e.severity, e.description, e.status
                    FROM exceptions e LEFT JOIN funds f ON e.fund_id = f.fund_id
                    WHERE e.as_of_date = :dt
                """,
                "Settlements": """
                    SELECT f.ticker, s.ticker as security, t.side, st.settlement_status,
                           st.expected_amount, st.actual_amount
                    FROM settlements st
                    JOIN trades t ON st.trade_id = t.trade_id
                    JOIN funds f ON st.fund_id = f.fund_id
                    JOIN securities s ON t.security_id = s.security_id
                    WHERE st.settlement_date = :dt
                """,
                "Cash": """
                    SELECT f.ticker, cp.cash_balance, cp.available_cash, cp.pending_settlements
                    FROM cash_positions cp
                    JOIN funds f ON cp.fund_id = f.fund_id
                    WHERE cp.as_of_date = :dt
                """,
                "KPIs": """
                    SELECT as_of_date, total_exceptions, critical_count, high_count, open_count
                    FROM vw_operational_kpis WHERE as_of_date = :dt
                """,
            }

            for sheet_name, query in sheets.items():
                try:
                    df = self.db.execute_query(query, {"dt": as_of_date.isoformat()})
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception as e:
                    logger.warning("Could not generate sheet %s: %s", sheet_name, e)

        logger.info("Generated Excel summary: %s", filepath)
        return filepath

    def generate_pdf_report(self, as_of_date: date) -> Path:
        filepath = self.output_dir / f"daily_report_{as_of_date.isoformat()}.pdf"
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=18, spaceAfter=20
        )
        elements = []

        elements.append(Paragraph("ETF Operations Daily Report", title_style))
        elements.append(Paragraph(f"Report Date: {as_of_date.isoformat()}", styles["Normal"]))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]
        ))
        elements.append(Spacer(1, 0.3 * inch))

        # NAV Summary
        nav_df = self.db.execute_query(
            "SELECT f.ticker, n.nav_per_share, n.total_nav, n.daily_return "
            "FROM nav_history n JOIN funds f ON n.fund_id = f.fund_id WHERE n.nav_date = :dt",
            {"dt": as_of_date.isoformat()},
        )
        if not nav_df.empty:
            elements.append(Paragraph("NAV Summary", styles["Heading2"]))
            nav_data = [["Fund", "NAV/Share", "Total NAV", "Daily Return"]]
            for _, row in nav_df.iterrows():
                nav_data.append([
                    row["ticker"],
                    f"${row['nav_per_share']:.4f}",
                    f"${row['total_nav']:,.0f}",
                    f"{row['daily_return']*100:.4f}%",
                ])
            table = Table(nav_data, colWidths=[1.5 * inch, 1.5 * inch, 2 * inch, 1.5 * inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))

        # Exceptions Summary
        exc_df = self.db.execute_query(
            "SELECT exception_type, severity, COUNT(*) as count FROM exceptions "
            "WHERE as_of_date = :dt GROUP BY exception_type, severity ORDER BY count DESC",
            {"dt": as_of_date.isoformat()},
        )
        if not exc_df.empty:
            elements.append(Paragraph("Exception Summary", styles["Heading2"]))
            exc_data = [["Exception Type", "Severity", "Count"]]
            for _, row in exc_df.iterrows():
                exc_data.append([row["exception_type"], row["severity"], str(row["count"])])
            table = Table(exc_data, colWidths=[3 * inch, 1.5 * inch, 1 * inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)

        doc.build(elements)
        logger.info("Generated PDF report: %s", filepath)
        return filepath

    def generate_all_reports(self, as_of_date: date) -> dict[str, Path]:
        return {
            "exceptions_csv": self.export_exceptions_csv(as_of_date),
            "nav_csv": self.export_nav_csv(as_of_date),
            "trades_csv": self.export_trades_csv(as_of_date),
            "excel_summary": self.generate_excel_summary(as_of_date),
            "pdf_report": self.generate_pdf_report(as_of_date),
        }
