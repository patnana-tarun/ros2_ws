"""Shared typography and layout helpers for the comparison report."""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

INK = colors.HexColor('#1a1a2e')
ACCENT = colors.HexColor('#2d6a9f')
GOOD = colors.HexColor('#2f6b4f')
WARN = colors.HexColor('#a8443f')
OURS = colors.HexColor('#96431a')
GREY = colors.HexColor('#6b6b7b')
LIGHT = colors.HexColor('#eef1f5')
RULE = colors.HexColor('#c8cfd8')


def S(name, **kw):
    base = dict(fontName='Helvetica', fontSize=9.2, leading=13.2,
                textColor=INK, spaceAfter=5)
    base.update(kw)
    return ParagraphStyle(name, **base)


BODY = S('body', alignment=TA_JUSTIFY)
SMALL = S('small', fontSize=8.0, leading=11.0, textColor=GREY)
H1 = S('h1', fontName='Helvetica-Bold', fontSize=15, leading=19,
       spaceBefore=4, spaceAfter=8)
H2 = S('h2', fontName='Helvetica-Bold', fontSize=11.2, leading=15,
       textColor=ACCENT, spaceBefore=12, spaceAfter=5)
H3 = S('h3', fontName='Helvetica-Bold', fontSize=9.6, leading=13,
       spaceBefore=8, spaceAfter=3)
MONO = S('mono', fontName='Courier', fontSize=7.8, leading=10.4)
CAP = S('cap', fontSize=7.6, leading=10, textColor=GREY, alignment=TA_CENTER,
        spaceBefore=3, spaceAfter=10)

PASS = '<font color="#2f6b4f"><b>PASS</b></font>'


class Doc:
    def __init__(self):
        self.story = []

    def h1(self, t):
        self.story.append(Paragraph(t, H1))

    def h2(self, t):
        self.story.append(Paragraph(t, H2))

    def h3(self, t):
        self.story.append(Paragraph(t, H3))

    def p(self, t, style=BODY):
        self.story.append(Paragraph(t, style))

    def sp(self, h=5):
        self.story.append(Spacer(1, h))

    def bullet(self, t):
        self.story.append(Paragraph('&bull;&nbsp; ' + t, BODY))

    def table(self, data, widths, style_extra=None, font=7.9, header=True,
              highlight_rows=()):
        cell = S('cell', fontSize=font, leading=font * 1.34)
        cellh = S('cellh', fontSize=font, leading=font * 1.34,
                  fontName='Helvetica-Bold')
        wrapped = []
        for i, row in enumerate(data):
            out = []
            for c in row:
                out.append(Paragraph(c, cellh if (header and i == 0) else cell)
                           if isinstance(c, str) else c)
            wrapped.append(out)

        st = [
            ('FONT', (0, 0), (-1, -1), 'Helvetica', font),
            ('TEXTCOLOR', (0, 0), (-1, -1), INK),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3.2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.2),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 0), (-1, -2), 0.25, RULE),
        ]
        if header:
            st += [('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', font),
                   ('BACKGROUND', (0, 0), (-1, 0), LIGHT),
                   ('LINEBELOW', (0, 0), (-1, 0), 0.7, ACCENT)]
        for r in highlight_rows:
            st.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#fdf1e8')))
        if style_extra:
            st += style_extra
        t = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0)
        t.setStyle(TableStyle(st))
        self.story.append(t)

    def callout(self, title, body, color=ACCENT):
        inner = [[Paragraph(f'<b>{title}</b>',
                            S('ct', fontSize=9.4, textColor=color,
                              fontName='Helvetica-Bold'))],
                 [Paragraph(body, S('cb', fontSize=8.8, leading=12.6))]]
        t = Table(inner, colWidths=[168 * mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
            ('LEFTPADDING', (0, 0), (-1, -1), 9),
            ('RIGHTPADDING', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBEFORE', (0, 0), (0, -1), 2.4, color),
        ]))
        self.story.append(t)
        self.sp(8)

    def figure(self, path, caption, width=168 * mm):
        from PIL import Image as PILImage
        iw, ih = PILImage.open(path).size
        self.story.append(Image(path, width=width, height=width * ih / iw))
        self.p(caption, CAP)


def decorate_factory(title_left, title_right):
    def decorate(canvas, doc):
        canvas.saveState()
        w, h = A4
        if doc.page > 1:
            canvas.setStrokeColor(RULE)
            canvas.setLineWidth(0.4)
            canvas.line(21 * mm, h - 15 * mm, w - 21 * mm, h - 15 * mm)
            canvas.setFont('Helvetica', 7.2)
            canvas.setFillColor(GREY)
            canvas.drawString(21 * mm, h - 13.2 * mm, title_left)
            canvas.drawRightString(w - 21 * mm, h - 13.2 * mm, title_right)
            canvas.line(21 * mm, 14 * mm, w - 21 * mm, 14 * mm)
            canvas.drawRightString(w - 21 * mm, 10 * mm, f'{doc.page}')
            canvas.drawString(21 * mm, 10 * mm,
                              'All figures produced by executed measurement')
        canvas.restoreState()
    return decorate
