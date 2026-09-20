from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

doc = SimpleDocTemplate("roblox_series_posts.pdf", pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Title'],
    fontName='Helvetica-Bold',
    fontSize=24,
    leading=28,
    textColor=colors.HexColor("#1a202c"),
    alignment=0,
    spaceAfter=15
)

subtitle_style = ParagraphStyle(
    'DocSubtitle',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=12,
    leading=16,
    textColor=colors.HexColor("#4a5568"),
    spaceAfter=20
)

heading_style = ParagraphStyle(
    'PostHeading',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=16,
    leading=20,
    textColor=colors.HexColor("#2b6cb0"),
    spaceBefore=15,
    spaceAfter=10
)

body_style = ParagraphStyle(
    'PostBody',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#2d3748"),
    spaceAfter=10
)

tag_style = ParagraphStyle(
    'PostTags',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=9,
    leading=12,
    textColor=colors.HexColor("#3182ce"),
    spaceBefore=5,
    spaceAfter=15
)

story = []
story.append(Paragraph("Roblox & Software Engineering Series", title_style))
story.append(Paragraph("A 5-post progression from gameplay systems to AI and broader software architecture.", subtitle_style))
story.append(Spacer(1, 10))

posts = [
    ("Post 1 \u2014 Pet Simulator", "Pet Simulator\n\nOne of my first larger Roblox projects was a small pet-simulator-style game.\n\nI built the systems connecting the UI, pets, and gameplay logic, which gave me a much better understanding of how different parts of a game communicate with each other.\n\nAt the time, I was mainly focused on making the game work.\n\nLooking back at it now, I can see plenty of things I'd structure differently \u2014 but that's also what makes old projects useful.\n\nThey show how much your approach changes as you gain experience.\n\nThis project was one of the things that got me interested in building more complex gameplay systems with Luau.", "#Roblox #GameDevelopment #Luau #Programming #SoftwareDevelopment"),
    ("Post 2 \u2014 Time Rewind", "Time Rewind\n\nI wanted to experiment with a mechanic that sounds simple but quickly becomes complicated:\n\n\u23ea Rewinding time.\n\nFor this Roblox project, I worked on a system that allowed gameplay state to be recorded and then reconstructed when the player activated the rewind mechanic.\n\nThe interesting part wasn't the rewind button itself.\n\nIt was figuring out what actually needs to be saved and how to restore that state without everything falling apart.\n\nProjects like this taught me to think less about individual features and more about the underlying state of a system.\n\nIt's also one of the projects I'd approach very differently today.", "#Roblox #GameDev #Luau #GameProgramming #Programming"),
    ("Post 3 \u2014 Wall Movement", "Wall Movement\n\nI spent some time experimenting with custom character movement in Roblox.\n\nOne of the mechanics I worked on was wall-running / wall-pinning.\n\nThe project involved detecting nearby surfaces with raycasts and using that information to control the character's movement and orientation.\n\nWhat looked like a simple movement mechanic ended up involving quite a few questions:\n\n\u2022 How do I reliably detect the wall?\n\u2022 How should the character orient itself?\n\u2022 What happens when the player leaves the wall?\n\u2022 How should velocity be handled?\n\u2022 How do I make the movement feel responsive?\n\nThis was a good introduction to the fact that game development often involves combining relatively simple systems to produce something that feels complex.", "#Roblox #GameDevelopment #Luau #GamePhysics #Programming"),
    ("Post 4 \u2014 Worm Boss", "Worm Boss\n\nOne of my more ambitious Roblox projects was a Terraria-style segmented worm boss.\n\nThe boss used a finite-state machine for its behavior, while the body consisted of many independently represented segments.\n\nThe networking side became an interesting challenge.\n\nI experimented with server-authoritative movement and client-side replication/interpolation so that the segmented body could move smoothly without simply relying on the client to control everything.\n\nWorking on this project taught me a lot about the difference between:\n\n\"It works on my screen.\"\nand\n\"It works as a multiplayer system.\"\n\nIt's an older project now, and there are definitely architectural decisions I'd change today.\n\nBut looking back at it, it's probably one of the projects that taught me the most about game architecture.", "#Roblox #GameDevelopment #Luau #GameAI #Networking #Programming"),
    ("Post 5 \u2014 The Transition", "What Came Next\n\nLooking back at some of my older Roblox projects made me realize something.\n\nI started game development because I wanted to make things move.\n\nThen I became interested in how those systems actually work.\n\nMovement led to physics.\n\nPhysics led to simulation.\n\nGameplay AI led me toward algorithms and decision-making.\n\nNetworking made me think more about distributed systems and architecture.\n\nAnd eventually, that curiosity expanded beyond games.\n\nNow I'm working on projects involving AI, automation, and software architecture \u2014 including my own desktop AI assistant.\n\nI still enjoy game development, but I'm increasingly interested in the underlying engineering behind the things I build.\n\nIt's interesting to look back at old projects and realize that they were teaching me things I didn't even know I was learning at the time.", "#SoftwareEngineering #GameDevelopment #AI #Programming #LearningInPublic")
]

for title, body, tags in posts:
    story.append(Paragraph(title, heading_style))
    for para in body.split('\n\n'):
        story.append(Paragraph(para.replace('\n', '<br/>'), body_style))
    story.append(Paragraph(tags, tag_style))
    story.append(Spacer(1, 10))

doc.build(story)
print("PDF generated successfully.")
