from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def convert_cyrillic_to_pdf(input_file, output_pdf, font_path):
    """
    Convert a Cyrillic text file to a PDF

    Args:
        input_file (str): Path to the input text file
        output_pdf (str): Path to the output PDF file
        font_path (str): Path to the Cyrillic TrueType font
    """
    # Register the Cyrillic font
    pdfmetrics.registerFont(TTFont("CyrillicFont", font_path))

    # Create a new PDF with Reportlab
    c = canvas.Canvas(str(output_pdf), pagesize=letter)

    # Set font and size
    c.setFont("CyrillicFont", 10)

    # Read the input file
    with open(input_file, encoding="utf-8") as file:
        text = file.read()

    # Split text into lines
    lines = text.split("\n")

    # Starting y-coordinate
    y = 750

    # Write text to PDF
    for line in lines:
        c.drawString(50, y, line)
        y -= 15  # Move to next line

        # Create new page if needed
        if y <= 50:
            c.showPage()
            c.setFont("CyrillicFont", 10)
            y = 750

    # Save the PDF
    c.save()
    Path(input_file).unlink()
    print(f"PDF created successfully: {output_pdf}")
    return output_pdf
