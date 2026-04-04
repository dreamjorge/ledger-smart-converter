import io
import matplotlib.pyplot as plt
from fpdf import FPDF
from typing import Dict, Any

class PdfReportGenerator:
    def generate(self, report_data: Dict[str, Any]) -> bytes:
        """
        Generates a PDF report from aggregated data.
        Returns the PDF as bytes.
        """
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        
        # Header
        pdf.cell(0, 10, f"Financial Report: {report_data['period']}", ln=True, align='C')
        pdf.ln(10)
        
        # Summary Section
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Summary", ln=True)
        pdf.set_font("helvetica", "", 12)
        pdf.cell(60, 10, f"Total Income: ${report_data['total_income']:.2f}")
        pdf.cell(60, 10, f"Total Expenses: ${report_data['total_expenses']:.2f}")
        pdf.cell(60, 10, f"Net Flow: ${report_data['net_flow']:.2f}", ln=True)
        pdf.ln(10)
        
        # Chart Section
        if report_data.get('category_breakdown'):
            chart_img = self._generate_category_chart(report_data['category_breakdown'])
            pdf.image(chart_img, x=10, y=pdf.get_y(), w=180)
            pdf.ln(110) # Space for chart
            
        # Transactions Table (Simplified for first version)
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Top Transactions", ln=True)
        pdf.set_font("helvetica", "", 10)
        
        # Table Header
        pdf.cell(30, 8, "Date", border=1)
        pdf.cell(100, 8, "Description", border=1)
        pdf.cell(30, 8, "Amount", border=1, ln=True)
        
        # Table Rows (showing top 10 to keep PDF concise)
        sorted_txns = sorted(report_data.get('transactions', []), key=lambda x: abs(x.amount or 0), reverse=True)[:10]
        for txn in sorted_txns:
            # Shorten description if too long
            desc = (txn.description[:45] + '..') if len(txn.description) > 45 else txn.description
            pdf.cell(30, 8, str(txn.date), border=1)
            pdf.cell(100, 8, desc, border=1)
            pdf.cell(30, 8, f"${txn.amount:.2f}", border=1, ln=True)

        return pdf.output()

    def _generate_category_chart(self, breakdown: Dict[str, float]) -> io.BytesIO:
        """Generates a pie chart for category distribution."""
        plt.figure(figsize=(8, 5))
        labels = list(breakdown.keys())
        values = list(breakdown.values())
        
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.title("Expenses by Category")
        
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', bbox_inches='tight')
        plt.close()
        img_buf.seek(0)
        return img_buf
