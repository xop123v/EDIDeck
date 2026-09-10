# exporter.py
import openpyxl
from openpyxl.styles import Font
import csv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from imdg_generator import generate_imdg_sheet
from reefer_generator import generate_reefer_sheet

def generate_all_excel(containers, filename="BAPLIE_Report.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "All"
    headers = ["Cont. ID","Size","Bay","Row","Tier","PoL","PoD","Weight","DG","Reefer","Temp","Remark"]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=1, column=i, value=h).font = Font(bold=True)
    row = 2
    for c in containers:
        ws.append([
            c.get("container"), c.get("size"), c.get("bay"), c.get("row"), c.get("tier"),
            c.get("pol"), c.get("pod"), c.get("weight"), "Yes" if c.get("dg") else "",
            "Yes" if c.get("reefer") else "", c.get("temperature"), c.get("remark")
        ])
    generate_imdg_sheet(wb, containers)
    generate_reefer_sheet(wb, containers)
    wb.save(filename)
    return filename

def export_csv(containers, filename="BAPLIE_Report.csv"):
    headers = ["container","size","bay","row","tier","pol","pod","weight","dg","reefer","temperature","remark"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for c in containers:
            writer.writerow([
                c.get("container"), c.get("size"), c.get("bay"), c.get("row"), c.get("tier"),
                c.get("pol"), c.get("pod"), c.get("weight"), c.get("dg"), c.get("reefer"),
                c.get("temperature"), c.get("remark")
            ])
    return filename

def export_pdf(containers, filename="BAPLIE_Report.pdf"):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, height - 40, "BAPLIE / EDI Report")
    c.setFont("Helvetica", 9)
    y = height - 60
    for cont in containers:
        line = f"{cont.get('container')} | PoL:{cont.get('pol')} PoD:{cont.get('pod')} W:{cont.get('weight')} DG:{cont.get('dg')} Reefer:{cont.get('reefer')} Temp:{cont.get('temperature')}"
        c.drawString(40, y, line[:120])
        y -= 12
        if y < 60:
            c.showPage()
            y = height - 40
    c.save()
    return filename
