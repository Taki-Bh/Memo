import platform
import os
import sys
import subprocess

try:
    import psutil
    import reportlab
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil", "reportlab"])

import psutil
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

system_info = [
    ["System", platform.system()],
    ["Node Name", platform.node()],
    ["Release", platform.release()],
    ["Version", platform.version()],
    ["Machine", platform.machine()],
    ["Processor", platform.processor()],
    ["Python Version", platform.python_version()],
    ["CPU Cores (Physical)", str(psutil.cpu_count(logical=False))],
    ["CPU Cores (Logical)", str(psutil.cpu_count(logical=True))],
    ["Total RAM", f"{round(psutil.virtual_memory().total / (1024.0 ** 3), 2)} GB"],
    ["Available RAM", f"{round(psutil.virtual_memory().available / (1024.0 ** 3), 2)} GB"],
    ["Disk Usage (Total)", f"{round(psutil.disk_usage('/').total / (1024.0 ** 3), 2)} GB"],
    ["Disk Usage (Free)", f"{round(psutil.disk_usage('/').free / (1024.0 ** 3), 2)} GB"],
]

pdf_filename = "system_info.pdf"
doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
styles = getSampleStyleSheet()
story = []

title_style = ParagraphStyle(
    'TitleStyle',
    parent=styles['Title'],
    fontSize=20,
    textColor=colors.HexColor('#1a365d'),
    spaceAfter=20
)

story.append(Paragraph("System Information Report", title_style))
story.append(Spacer(1, 10))

table_data = [["Property", "Value"]] + system_info
t = Table(table_data, colWidths=[200, 300])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b6cb0')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('BOTTOMPADDING', (0,0), (-1,0), 8),
    ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f7fafc')),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f7fafc')]),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
]))

story.append(t)
doc.build(story)
print("PDF generated successfully.")