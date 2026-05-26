from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io

buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=A4)
styles = getSampleStyleSheet()
story = []
story.append(Paragraph('This is a <a href="https://linkedin.com" color="blue">LinkedIn</a> link.', styles['Normal']))
story.append(Paragraph('This is a <link href="https://github.com" color="blue">GitHub</link> link.', styles['Normal']))
doc.build(story)

with open('test_links.pdf', 'wb') as f:
    f.write(buffer.getvalue())
print("Generated test_links.pdf")
