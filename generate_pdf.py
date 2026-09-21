from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_pdf(filename="l9raya_amena_mn_nes.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1a365d'),
        alignment=1,
        spaceAfter=15
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=8
    )
    
    story = []
    
    story.append(Paragraph("Importance of L9raya (Education) Being Safe from People's Influence", title_style))
    story.append(Spacer(1, 10))
    
    intro_text = (
        "Education (<i>l9raya</i>) is one of the most powerful tools for personal and societal growth. "
        "However, the environment in which one studies, the motivations behind acquiring knowledge, "
        "and the influences of those around us play a crucial role in determining the true value and sincerity of that education. "
        "Keeping one's educational journey safe from negative external opinions, interference, or societal pressures—often "
        "expressed as being <i>'amena mn nes'</i> (secure or protected from people)—is essential for true intellectual and personal freedom."
    )
    story.append(Paragraph(intro_text, body_style))
    
    story.append(Paragraph("1. Protection from External Doubt and Demoralization", heading_style))
    p1 = (
        "When individuals pursue learning, they often encounter discouragement, skepticism, or unsolicited opinions from peers, "
        "family members, or society. Protecting your studies from these negative voices ensures that your self-belief, intrinsic motivation, "
        "and passion for learning remain untouched. Doubt is contagious, and keeping your goals private or secure helps maintain steady progress."
    )
    story.append(Paragraph(p1, body_style))
    
    story.append(Paragraph("2. Cultivating Pure Intention (Sincerity in Purpose)", heading_style))
    p2 = (
        "Education sought purely for personal enrichment, self-awareness, and self-improvement yields the most profound results. "
        "When learning is overly influenced by what people think, expect, or praise, it can shift from a genuine quest for knowledge "
        "to a performance meant for social approval. Keeping your educational path secure from people's judgment fosters authenticity."
    )
    story.append(Paragraph(p2, body_style))
    
    story.append(Paragraph("3. Avoiding Envy and Unnecessary Pressure", heading_style))
    p3 = (
        "Sharing every step of your academic or professional journey can sometimes invite unwanted comparison, envy, or pressure. "
        "Working quietly, focusing diligently, and letting your results speak for themselves creates a peaceful mental space conducive "
        "to deep focus, critical thinking, and long-term success."
    )
    story.append(Paragraph(p3, body_style))
    
    story.append(Paragraph("Conclusion", heading_style))
    conclusion = (
        "In summary, keeping <i>l9raya</i> safe from the interference and negative perceptions of others is not about isolation, "
        "but about safeguarding your mental well-being, focus, and core motivations. By nurturing your knowledge in a secure and peaceful "
        "environment, you build a stronger foundation for lifelong success and personal fulfillment."
    )
    story.append(Paragraph(conclusion, body_style))
    
    doc.build(story)

if __name__ == '__main__':
    create_pdf()
