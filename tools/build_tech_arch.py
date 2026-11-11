"""Build Qlik-branded MOSS-Image workflows for technical architecture diagrams and marketing assets.

What each generated workflow does, beyond a plain text-to-image prompt:
  1. Layout control - every zone, card, arrow and label is a bounding box with its own
     caption and Qlik palette, so text lands exactly where it is placed.
  2. Refine pass    - the 1 MP render is upscaled 1.5x in pixel space, re-encoded and
     re-sampled at low denoise (the hi-res method in ComfyUI's MOSS-Image guide), giving a
     sharper result (2032x1152 for a 16:9 layout).
  3. Official logo  - the real Qlik logo is composited onto the header after generation,
     because the brand rules forbid a redrawn logo and diffusion models garble logos.

Layouts are drawn at 1 MP (1360x768 for 16:9, 1024x1024 for 1:1, 1568x672 for 21:9): background first,
zones and art next, cards and text last. All content is generic and editable.
"""
import argparse
import copy
import json
import os
import urllib.request

TEMPLATE_URL = ("https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/"
                "templates/image_moss_image_t2i_bboxes.json")
HERE = os.path.dirname(os.path.abspath(__file__))

W, H = 1360, 768
REFINE_SCALE, REFINE_STEPS, REFINE_DENOISE = 1.5, 10, 0.45
LOGO_FILE = "qlik-logo-header.png"              # ComfyUI/input, sized for the refined canvas
LOGO_FILE_DARK = "qlik-logo-header-dark.png"    # charcoal "lik" for light backgrounds
LIGHT_BACKGROUND = {"fun-comic-product-mgmt", "fun-comic-standup", "fun-comic-spreadsheet", "fun-comic-ai-strategy"}

# Qlik brand palette (qlik-marketecture/scripts/brand_core.json), navy theme
NAVY, NAVY_DEEP, GREEN, CYAN = "#19416C", "#0F2A47", "#009845", "#10CFC9"
CHARCOAL, GRAY, WHITE, TEAL = "#54565A", "#A9B3B6", "#FFFFFF", "#006580"

STYLE = ("Premium Qlik-branded marketing hero graphic of a technical architecture, in the style of a keynote "
         "slide: flat, even deep navy blue canvas with a very faint fine grid and no background glows, "
         "recessed darker navy glass panels with thin cyan hairline borders, component cards with crisp white "
         "line-art icons and one Qlik green accent, Qlik products shown as solid bright Qlik green cards with "
         "white text, glowing Qlik green connector arrows with soft light trails, bold clean white "
         "headline, all text set in the Inter typeface, every label sharp and perfectly legible, generous spacing, polished and modern, "
         "high contrast, no photographs, no people, no logos.")


NEGATIVE = ("nsfw, worst quality, watermark, jpeg artifact, logo, wordmark, brand mark, lens flare, light flares, background glow, "
            "bright spots, bokeh, sparkles, vignette, misspelled text")


def is_qlik(label):
    return label.startswith("Qlik")


def box(x, y, w, h, kind, text, desc, palette=()):
    return {"x": x, "y": y, "width": w, "height": h,
            "metadata": {"type": kind, "text": text, "desc": desc, "palette": list(palette)}}


def background():
    return box(0, 0, W, H, "obj", "",
               "A flat, even deep navy blue background with a very faint fine grid, uniform in tone from corner to "
               "corner, clean and empty, no glows, no light spots", (NAVY, NAVY_DEEP))


def header(title, tagline):
    # the top-right corner (x 1180-1336, y 24-90) stays empty for the composited Qlik logo
    return [
        box(40, 26, 1100, 58, "text", title,
            "A large bold white headline set in the Inter typeface reading , single line, left aligned, crisp", (WHITE,)),
        box(40, 88, 1000, 30, "text", tagline,
            "A single line of light cyan subtitle text in the Inter typeface reading , left aligned", (CYAN,)),
        box(40, 124, 96, 5, "obj", "", "A short thin glowing Qlik green accent bar", (GREEN,)),
    ]


def footer(text):
    return box(40, 726, 1100, 28, "text", text,
               "A single line of small cool-grey caption text in the Inter typeface reading , left aligned", (GRAY,))


def zone(x, y, w, h, label):
    return [
        box(x, y, w, h, "obj", "",
            "A large rounded rectangle panel of darker navy glass with a thin glowing cyan hairline border, "
            "an empty grouping zone", (NAVY_DEEP, CYAN)),
        box(x + 16, y + 12, min(w - 32, 520), 34, "text", label,
            "A small bold uppercase cyan zone label in the Inter typeface reading , single line, left aligned", (CYAN,)),
    ]


def comp(x, y, w, h, label, icon):
    lines = label.count("\n") + 1
    th = 34 * lines
    if is_qlik(label):
        card = box(x, y, w, h, "obj", "",
                   f"A solid bright Qlik green rounded card with a soft green glow and a small white line-art {icon} "
                   f"icon at its left edge", (GREEN, WHITE))
        name = box(x + 58, y + (h - th) // 2, w - 68, th, "text", label,
                   "Bold white Inter typeface text reading , left aligned, crisp", (WHITE,))
    else:
        card = box(x, y, w, h, "obj", "",
                   f"A rounded card of dark navy glass with a thin cyan border and a small white line-art {icon} "
                   f"icon with one Qlik green accent at its left edge", (NAVY_DEEP, CYAN, WHITE, GREEN))
        name = box(x + 58, y + (h - th) // 2, w - 68, th, "text", label,
                   "White Inter typeface text reading , left aligned, crisp", (WHITE,))
    return [card, name]


def arrow(x, y, w, h, direction="right"):
    return box(x, y, w, h, "obj", "",
               f"A glowing Qlik green connector arrow pointing {direction} with a solid arrowhead and a soft light trail",
               (GREEN,))


def edge_label(x, y, w, text):
    return box(x, y, w, 28, "text", text,
               "A small cyan label in Inter typeface reading , single line, centered", (CYAN,))


# ---------------------------------------------------------------- layouts
def data_pipeline():
    b = [background(), *header("Modern Data Integration Pipeline",
                               "Real-time change data capture from operational systems to analytics and AI")]
    b += zone(28, 150, 320, 556, "Source Systems")
    b += comp(50, 214, 276, 76, "ERP System", "database cylinder")
    b += comp(50, 354, 276, 76, "CRM Platform", "database cylinder")
    b += comp(50, 494, 276, 76, "Event Streams", "event stream")
    for y in (236, 376, 516):
        b += [arrow(348, y, 60, 32)]
    b += comp(408, 214, 230, 356, "Qlik Talend\nCloud", "data flow")
    b += [edge_label(398, 584, 250, "CDC · ELT · data quality")]
    # data lands in the top row; the platform zone stops at x=1060 so the consumer arrows sit in a visible gap
    b += [arrow(638, 236, 60, 32)]
    b += [edge_label(626, 196, 84, "HTTPS")]
    b += zone(698, 150, 362, 556, "Cloud Data Platform")
    b += comp(716, 214, 326, 76, "Landing Zone", "storage bucket")
    b += [arrow(863, 292, 32, 60, "down")]
    b += comp(716, 354, 326, 76, "Curated Tables", "table grid")
    b += [arrow(863, 432, 32, 60, "down")]
    b += comp(716, 494, 326, 76, "Data Catalog", "catalog book")
    b += zone(1112, 150, 224, 556, "Consumers")
    b += [arrow(1060, 376, 52, 32)]
    b += comp(1124, 354, 200, 76, "Data Warehouse", "warehouse")
    b += [edge_label(1112, 436, 224, "governed sharing")]
    b += [arrow(1060, 516, 52, 32)]
    b += comp(1124, 494, 200, 76, "Qlik Cloud\nAnalytics", "bar chart")
    b += [edge_label(1112, 578, 224, "dashboards · AI answers")]
    b += [footer("Ingest → Land → Curate → Analyze · governed end to end")]
    prompt = ("Technical data integration architecture: an ERP system, a CRM platform and event streams on the left "
              "feed Qlik Talend Cloud, which captures changes and delivers them into a cloud data platform with a "
              "landing zone, curated tables and a data catalog, shared with a data warehouse and served to Qlik "
              "Cloud Analytics on the right. " + STYLE)
    return prompt, b


def cloud_network():
    b = [background(), *header("Cloud Deployment Topology",
                               "Highly available application stack across two availability zones")]
    b += comp(24, 330, 190, 90, "Users", "laptop")
    b += [arrow(214, 358, 44, 32)]
    b += [edge_label(196, 426, 110, "HTTPS")]
    b += comp(258, 330, 176, 90, "CDN / WAF", "shield")
    b += [arrow(434, 358, 28, 32)]
    b += zone(462, 150, 874, 556, "Virtual Network 10.0.0.0/16")
    for i, x in enumerate((478, 906)):
        az = "AB"[i]
        b += zone(x, 202, 414, 492, f"Availability Zone {az}")
        b += zone(x + 14, 250, 386, 196, f"Public 10.0.{i + 1}.0/24")
        b += comp(x + 28, 310, 226, 76, "Load Balancer", "load balancer")
        b += comp(x + 264, 310, 122, 76, "NAT", "router")
        b += zone(x + 14, 460, 386, 222, f"Private 10.0.{i + 11}.0/24")
        b += comp(x + 28, 512, 358, 70, "App Services", "container")
        b += comp(x + 28, 598, 358, 70, "Managed Database", "database cylinder")
    b += [footer("Private data tier · encryption at rest and in transit · automated failover")]
    prompt = ("Technical cloud network architecture: users connect over HTTPS through a CDN and web application "
              "firewall into a virtual network spanning two availability zones, each with a public subnet holding a "
              "load balancer and NAT gateway and a private subnet holding application services and a managed "
              "database. " + STYLE)
    return prompt, b


def microservices():
    b = [background(), *header("Event-Driven Platform with Qlik Analytics",
                               "Microservices on Kubernetes streaming into Qlik in real time")]
    b += zone(24, 150, 190, 556, "Clients")
    b += comp(36, 214, 166, 76, "Web App", "browser window")
    b += comp(36, 354, 166, 76, "Mobile App", "smartphone")
    b += comp(36, 494, 166, 76, "Partner API", "plug")
    b += [arrow(214, 376, 36, 32)]
    b += comp(250, 316, 180, 130, "API Gateway", "shield")
    b += [edge_label(240, 456, 200, "OAuth2 · rate limit")]
    b += [arrow(430, 376, 30, 32)]
    b += zone(460, 150, 470, 424, "Kubernetes Cluster")
    b += comp(478, 214, 212, 76, "Auth Service", "key")
    b += comp(706, 214, 206, 76, "Order Service", "shopping cart")
    b += comp(478, 330, 212, 76, "Inventory Svc", "boxes")
    b += comp(706, 330, 206, 76, "Billing Service", "credit card")
    b += [edge_label(478, 432, 434, "Istio service mesh · mTLS")]
    b += [arrow(679, 576, 32, 34, "down")]
    b += comp(460, 612, 470, 76, "Kafka Event Bus", "event stream")
    b += [arrow(930, 634, 40, 32)]
    b += comp(970, 612, 366, 76, "Qlik Talend Cloud", "data flow")
    b += [arrow(1137, 574, 32, 36, "up")]
    b += zone(970, 150, 366, 424, "Qlik Cloud Analytics")
    b += comp(988, 214, 330, 76, "Qlik Sense Apps", "bar chart")
    b += comp(988, 330, 330, 76, "Qlik Answers", "chat bubble")
    b += comp(988, 446, 330, 76, "Qlik Automate", "lightning bolt")
    b += [footer("Service databases and Kafka topics land in Qlik for live dashboards, automations and AI answers")]
    prompt = ("Technical event-driven architecture: web, mobile and partner clients call an API gateway that routes "
              "to four microservices in a Kubernetes cluster, which publish to a Kafka event bus captured by Qlik "
              "Talend Cloud and delivered to Qlik Cloud Analytics with Qlik Sense apps, Qlik Answers and Qlik "
              "Automate. " + STYLE)
    return prompt, b


def layered_stack():
    b = [background(), *header("Qlik Platform Reference Architecture",
                               "From data movement to AI-powered answers")]
    layers = [
        ("Experience", ("Qlik Sense", "Qlik Answers", "Qlik Automate"), "bar chart"),
        ("APIs", ("REST APIs", "Qlik MCP Server", "Webhooks"), "plug"),
        ("Data Products", ("Qlik Catalog", "Lineage", "Qlik Predict"), "gear"),
        ("Storage", ("Qlik Open Lakehouse", "Cloud Warehouse", "Vector Store"), "database cylinder"),
        ("Movement", ("Data Movement GW", "CDC Streams", "Kubernetes"), "server rack"),
    ]
    for i, (name, items, icon) in enumerate(layers):
        y = 150 + i * 112
        b += [box(28, y, 1010, 98, "obj", "",
                  "A long horizontal rounded band of darker navy glass with a thin cyan hairline border, one layer "
                  "of a technology stack", (NAVY_DEEP, CYAN))]
        b += [box(44, y + 32, 220, 36, "text", name,
                  "A bold uppercase cyan layer name in the Inter typeface reading , single line, left aligned", (CYAN,))]
        for j, item in enumerate(items):
            b += comp(282 + j * 250, y + 12, 236, 74, item, icon)
    b += zone(1062, 150, 274, 546, "Trust & Governance")
    for j, (item, icon) in enumerate((("Qlik Trust Score", "shield check"), ("Identity & IAM", "key"),
                                      ("Secrets & KMS", "lock"), ("Data Quality", "checklist"))):
        b += comp(1078, 206 + j * 120, 242, 78, item, icon)
    b += [footer("Governed, trusted data products feeding analytics, automation and AI")]
    prompt = ("Technical layered reference architecture of the Qlik platform: five horizontal stacked layers from "
              "experience at the top through APIs, data products and storage down to data movement, each with three "
              "component cards, and a vertical trust and governance column on the right. " + STYLE)
    return prompt, b


# ---------------------------------------------------------------- marketing assets
MKT_STYLE = ("Premium marketing campaign graphic in a high-end enterprise software style: flat, even "
             "deep navy blue canvas, bold white headline set in the Inter typeface, emerald green and cyan accents, "
             "a polished abstract 3D illustration of glowing data streams and geometric platform shapes, clean "
             "composition with generous negative space, every word sharp and perfectly legible, no photographs, "
             "no people, no logos.")


def headline(x, y, w, h, text):
    return box(x, y, w, h, "text", text,
               "A very large bold white headline set in the Inter typeface showing the given text, left aligned, tight line spacing",
               (WHITE,))


def subline(x, y, w, h, text):
    return box(x, y, w, h, "text", text,
               "A medium light cyan subheading set in the Inter typeface showing the given text, left aligned", (CYAN,))


def body(x, y, w, h, text):
    return box(x, y, w, h, "text", text,
               "Small white body text set in the Inter typeface showing the given text, left aligned", (WHITE,))


def pill(x, y, w, h, text):
    return [box(x, y, w, h, "obj", "", "A small solid Qlik green rounded pill label", (GREEN,)),
            box(x + 16, y + (h - 30) // 2, w - 32, 30, "text", text,
                "Bold uppercase white text set in the Inter typeface showing the given text, centered, letter-spaced", (WHITE,))]


def button(x, y, w, h, text):
    return [box(x, y, w, h, "obj", "", "A solid bright Qlik green rounded call-to-action button with a soft green glow",
                (GREEN,)),
            box(x + 20, y + (h - 36) // 2, w - 40, 36, "text", text,
                "Bold white text set in the Inter typeface showing the given text, centered", (WHITE,))]


def hero_art(x, y, w, h, desc):
    return box(x, y, w, h, "obj", "", desc + ", completely free of any text, letters, numbers, symbols or logos",
               (GREEN, CYAN, NAVY_DEEP))


def mkt_webinar():
    b = [background()]
    b += [hero_art(700, 110, 640, 600,
                   "An abstract glossy 3D illustration of glowing Qlik green and cyan data streams flowing from the left "
                   "into a faceted crystal-like analytics core that radiates light, floating on a dark navy background")]
    b += pill(60, 140, 240, 46, "LIVE WEBINAR")
    b += [headline(60, 214, 620, 200, "From Raw Data\nto AI-Ready Insights")]
    b += [subline(60, 432, 600, 70, "How data teams build a trusted foundation for AI")]
    b += [body(60, 524, 600, 36, "Thursday · 10:00 AM ET · 45 minutes")]
    b += button(60, 606, 270, 72, "Register Now")
    prompt = ("Webinar promotion graphic: a green 'Live Webinar' label, a large two-line headline, a cyan subheading, "
              "a date line and a green 'Register Now' button on the left, with an abstract 3D data illustration on the "
              "right. " + MKT_STYLE)
    return prompt, b


def mkt_social():
    b = [background()]
    b += [headline(64, 96, 760, 210, "Trusted Data.\nSmarter AI.")]
    b += [hero_art(112, 330, 800, 440,
                   "An abstract glossy 3D isometric illustration of stacked glowing platform layers connected by Qlik "
                   "green and cyan light streams, floating on a dark navy background")]
    b += [subline(64, 806, 896, 64, "Build an AI-ready data foundation")]
    b += button(64, 896, 250, 72, "Learn More")
    prompt = ("Square social media post: a large two-line headline at the top, an abstract 3D platform illustration in "
              "the middle, a cyan subheading and a green 'Learn More' button at the bottom. " + MKT_STYLE)
    return prompt, b


def mkt_banner():
    b = [background()]
    b += [headline(64, 150, 820, 150, "Data You Can Trust.\nAI You Can Use.")]
    b += [subline(64, 330, 800, 56, "One platform for data integration, analytics and AI")]
    b += [box(64, 412, 120, 6, "obj", "", "A short thin Qlik green accent bar", (GREEN,))]
    b += button(64, 460, 250, 70, "Get Started")
    b += [hero_art(920, 110, 600, 520,
                   "An abstract glossy 3D illustration of a sweeping wave of glowing Qlik green and cyan data particles "
                   "rising into geometric crystal shapes, on a dark navy background")]
    prompt = ("Wide website hero banner: a large two-line headline, a cyan subheading, a green accent bar and a green "
              "'Get Started' button on the left, with a sweeping abstract 3D data wave illustration on the right. "
              + MKT_STYLE)
    return prompt, b


def mkt_product():
    b = [background()]
    b += pill(60, 150, 140, 46, "NEW")
    b += [headline(60, 222, 560, 200, "Insights at the\nSpeed of Business")]
    b += [subline(60, 440, 540, 70, "Interactive analytics and AI answers in one experience")]
    b += button(60, 560, 270, 72, "See It in Action")
    b += [hero_art(640, 130, 690, 540,
                   "A cluster of floating translucent glass panels in 3D perspective, each holding a pure graphic shape "
                   "of a bar chart, a line chart or a donut chart in emerald green and cyan, softly glowing, purely "
                   "visual chart shapes without any axes, labels or values")]
    prompt = ("Product launch hero graphic: a green 'New' label, a large two-line headline, a cyan subheading and a "
              "green 'See It in Action' button on the left, with floating glass chart panels on the right. "
              + MKT_STYLE)
    return prompt, b


# ---------------------------------------------------------------- fun: original comic and spoof movie posters
INK, PAPER = "#1A1A1A", "#FFFFFF"


def person(x, y, w, h, desc):
    """An object box the layout prompt labels as a character (see build: character_boxes)."""
    b = box(x, y, w, h, "obj", "", desc)
    b["metadata"]["character"] = True
    return b


def bubble(x, y, w, h, text, tail="down"):
    return box(x, y, w, h, "text", text,
               "Hand-lettered black comic text showing the given text, inside a white rounded speech bubble with a thin black "
               f"outline and a small tail pointing {tail} toward the speaker directly below it, centered", (INK, PAPER))


def comic_pm():
    COMIC = ("clean flat cartoon office comic style with thick black ink outlines, simple shapes, muted pastel "
             "colors and a light paper texture")
    b = [box(0, 0, W, H, "obj", "", "A plain off-white paper background", (PAPER,))]
    b += [box(32, 18, 900, 54, "text", "Product Management, Explained",
              "A bold black hand-lettered comic strip title showing the given text, left aligned", (INK,))]
    panels = [
        ("A comic panel with a thick black border: a bright office meeting room with a whiteboard covered in colorful "
         "sticky notes and a hand-drawn roadmap arrow", 32),
        ("A comic panel with a thick black border: the same office, a bare desk with only a coffee mug and a notepad on it", 540),
        ("A comic panel with a thick black border: a corner office with a large window and a potted plant", 1048),
    ]
    for desc, x in panels:
        b += [box(x, 92, 488, 556, "obj", "", f"{desc}, {COMIC}", (PAPER, INK))]
    # panel 1: the PM presents
    b += [person(150, 300, 250, 340, f"A cheerful product manager with short curly hair, round glasses and a teal "
                                     f"cardigan, proudly pointing at the whiteboard, {COMIC}")]
    b += [bubble(52, 112, 448, 120, "Our roadmap is\n100% data-driven.")]
    # panel 2: the engineer asks
    b += [person(560, 330, 200, 310, f"A deadpan software engineer in a grey hoodie holding a coffee mug, raising one "
                                     f"eyebrow, {COMIC}")]
    b += [person(800, 330, 200, 310, f"The same cheerful product manager with curly hair, round glasses and a teal "
                                     f"cardigan, smiling nervously, {COMIC}")]
    b += [bubble(560, 150, 200, 90, "Which data?", "down toward the engineer on the left")]
    b += [bubble(800, 112, 216, 120, "The data that\nagrees with me.", "down toward the product manager on the right")]
    # panel 3: the executive
    b += [person(1068, 330, 220, 310, f"A beaming executive in a navy suit and bright tie giving a thumbs up, {COMIC}")]
    b += [person(1300, 330, 210, 310, f"The same product manager with curly hair, round glasses and a teal cardigan, "
                                      f"sweating with a panicked smile, {COMIC}")]
    b += [bubble(1068, 112, 260, 110, "Love it.\nShip it Friday.")]
    b += [bubble(1300, 230, 216, 90, "Which Friday?")]
    prompt = ("A three-panel office humor comic strip about product management. Panel one: a product manager proudly "
              "presents a roadmap. Panel two: a deadpan engineer asks which data, and the product manager admits it "
              "is the data that agrees with them. Panel three: a beaming executive says ship it Friday and the "
              "product manager panics. Original characters, " + COMIC + ", every speech bubble crisply lettered "
              "and perfectly legible, no logos.")
    return prompt, b


COMIC = ("clean flat cartoon office comic style with thick black ink outlines, simple shapes, muted pastel colors "
         "and a light paper texture")
PM = "the cheerful product manager with short curly hair, round glasses and a teal cardigan"
ENGINEER = "the deadpan software engineer in a grey hoodie"
EXEC = "the beaming executive in a navy suit and bright tie"
ANALYST = "the eager data analyst with a ponytail and a green sweater"
PANEL_X = (32, 540, 1048)


def comic_strip(title, panels, summary):
    """Three-panel strip. Each panel: (scene, [(x, y, w, h, who)], [(x, y, w, h, text, tail)]),
    with x relative to the panel's left edge."""
    b = [box(0, 0, W, H, "obj", "", "A plain off-white paper background", (PAPER,))]
    b += [box(32, 18, 900, 54, "text", title,
              "A bold black hand-lettered comic strip title showing the given text, left aligned", (INK,))]
    for px, (scene, _, _) in zip(PANEL_X, panels):
        b += [box(px, 92, 488, 556, "obj", "", f"A comic panel with a thick black border: {scene}, {COMIC}", (PAPER, INK))]
    for px, (_, people, lines) in zip(PANEL_X, panels):
        b += [person(px + x, y, w, h, f"{who}, {COMIC}") for x, y, w, h, who in people]
        b += [bubble(px + x, y, w, h, text, tail) for x, y, w, h, text, tail in lines]
    prompt = (f"A three-panel office humor comic strip. {summary} Original characters, {COMIC}, every speech bubble "
              "crisply lettered and perfectly legible, no logos.")
    return prompt, b


def comic_standup():
    return comic_strip("Daily Standup", [
        ("an open-plan office with a kanban board covered in sticky notes",
         [(40, 330, 200, 310, f"{ENGINEER} holding a coffee mug, speaking"),
          (260, 330, 200, 310, f"{PM} listening")],
         [(20, 112, 250, 120, "Yesterday I\nfixed a bug.", "down toward the engineer on the left")]),
        ("the same open-plan office by the kanban board",
         [(140, 330, 220, 310, f"{ENGINEER} shrugging")],
         [(30, 112, 430, 120, "Today I'll fix the bug\nthe fix caused.", "down toward the engineer")]),
        ("the same open-plan office by the kanban board",
         [(30, 330, 200, 310, f"{PM} holding a clipboard, smiling"),
          (260, 330, 200, 310, f"{ENGINEER} with a flat, tired expression")],
         [(20, 112, 220, 90, "Any blockers?", "down toward the product manager on the left"),
          (250, 230, 220, 90, "This meeting.", "down toward the engineer on the right")]),
    ], "Panel one: an engineer says yesterday they fixed a bug. Panel two: today they will fix the bug the fix caused. "
       "Panel three: the product manager asks about blockers and the engineer answers this meeting.")


def comic_spreadsheet():
    return comic_strip("The New Dashboard", [
        ("a bright office with a huge monitor showing a colorful dashboard of charts",
         [(30, 330, 200, 310, f"{ANALYST} proudly gesturing at the monitor"),
          (260, 330, 200, 310, f"{EXEC} looking at the monitor")],
         [(20, 112, 260, 120, "The new dashboard\nis live!", "down toward the analyst on the left")]),
        ("the same office in front of the big dashboard monitor",
         [(140, 330, 220, 310, f"{EXEC} squinting suspiciously at the dashboard")],
         [(40, 112, 410, 120, "Can I get it\nin a spreadsheet?", "down toward the executive")]),
        ("the same office, the executive walking out the door",
         [(30, 330, 200, 310, f"{ANALYST} staring blankly straight at the reader"),
          (280, 330, 190, 310, f"{EXEC} walking away, waving over a shoulder")],
         [(250, 112, 220, 110, "And email it\nevery Monday.", "down toward the executive on the right")]),
    ], "Panel one: an analyst proudly launches a new dashboard. Panel two: the executive asks for it in a "
       "spreadsheet. Panel three: walking away, the executive asks for it by email every Monday while the analyst "
       "stares blankly at the reader.")


def comic_ai_strategy():
    return comic_strip("The AI Strategy", [
        ("a boardroom with a long table and a presentation screen showing a glowing brain icon",
         [(140, 330, 220, 310, f"{EXEC} standing at the head of the table, fist raised")],
         [(40, 112, 410, 120, "We need an\nAI strategy!", "down toward the executive")]),
        ("the same boardroom, seen from the side of the table",
         [(140, 330, 220, 310, f"{ENGINEER} leaning back, arms crossed")],
         [(40, 112, 410, 120, "What problem are\nwe solving?", "down toward the engineer")]),
        ("the same boardroom",
         [(30, 330, 200, 310, f"{EXEC} pointing confidently"),
          (260, 330, 200, 310, f"{PM} with a hand over their face")],
         [(20, 112, 230, 110, "That's\nphase two.", "down toward the executive on the left")]),
    ], "Panel one: an executive declares the company needs an AI strategy. Panel two: an engineer asks what problem "
       "they are solving. Panel three: the executive says that is phase two while the product manager facepalms.")


POSTER = ("Original cinematic movie poster in the style of a modern Hollywood one-sheet: dramatic lighting, rich "
          "teal and orange color grading with Qlik green highlights, film grain, bold condensed title typography, "
          "clean billing block at the bottom, every word crisp and perfectly legible, no logos.")


def poster(title, tagline, art, hero, release, credits="STARRING THE DATA TEAM   MUSIC BY THE ON-CALL PAGER"):
    b = [box(0, 0, W, H, "obj", "", "A dark cinematic background with deep shadows", (NAVY_DEEP,))]
    b += [box(0, 150, W, 760, "obj", "", art, (NAVY_DEEP, GREEN, CYAN))]
    b += [person(*hero)]
    b += [box(56, 96, 600, 46, "text", tagline,
              "Small white uppercase letter-spaced tagline text set in a condensed sans-serif showing the given text, left aligned",
              (WHITE,))]
    b += [box(40, 900, 752, 170, "text", title,
              "A huge bold condensed metallic movie title showing the given text, centered, with a subtle glow", (WHITE, GREEN))]
    b += [box(80, 1100, 672, 30, "text", credits,
              "Tiny condensed grey movie-poster billing block text showing the given text, centered", (GRAY,))]
    b += [box(160, 1150, 512, 48, "text", release,
              "Bold white condensed uppercase release line showing the given text, centered", (WHITE,))]
    return b


def poster_last_dashboard():
    b = poster("THE LAST\nDASHBOARD", "When the data goes dark, one analyst stands",
               "A stormy futuristic city at night under a giant glowing holographic dashboard of charts floating in "
               "the sky, crackling with green light, epic sci-fi scale",
               (266, 420, 300, 470, "A lone heroic data analyst in a long coat seen from behind, silhouetted against "
                                    "the glowing holographic dashboard, holding a laptop like a shield"),
               "COMING THIS QUARTER")
    return ("Original sci-fi action movie poster titled THE LAST DASHBOARD: a lone analyst faces a giant glowing "
            "holographic dashboard over a stormy city. " + POSTER), b


def poster_deadline_friday():
    b = poster("DEADLINE\nFRIDAY", "Scope creeps. Time doesn't.",
               "A long neon-lit office corridor at night with a giant wall clock reading 4:59, papers flying, motion "
               "blur, tense thriller atmosphere",
               (286, 380, 260, 500, "A desperate product manager in a rumpled shirt sprinting toward the camera "
                                    "clutching a laptop and a coffee cup, tie flying"),
               "IN THEATERS NEXT SPRINT")
    return ("Original thriller movie poster titled DEADLINE FRIDAY: a product manager sprints down a neon office "
            "corridor under a giant clock. " + POSTER), b


def poster_rogue_pipeline():
    b = poster("ROGUE\nPIPELINE", "They moved the data. Nobody noticed.",
               "A high-tech vault filled with stacks of glowing green and cyan data cubes, laser beams criss-crossing "
               "the dark, stylish heist movie atmosphere",
               (176, 430, 480, 440, "A crew of four stylish data engineers in dark jackets standing in a confident "
                                    "line, silhouetted against the glowing data vault"),
               "OPENING NEXT RELEASE")
    return ("Original heist movie poster titled ROGUE PIPELINE: a crew of four data engineers in a vault of glowing "
            "data cubes. " + POSTER), b


def poster_schema_drift():
    b = poster("SCHEMA\nDRIFT", "The columns are changing.",
               "A dark abandoned server-room hallway lit by one flickering green light, a giant glitching spreadsheet "
               "grid crawling across the walls and ceiling like vines, eerie horror atmosphere",
               (286, 420, 260, 470, "A terrified data engineer seen from behind holding a flashlight, standing at the "
                                    "end of the hallway"),
               "THIS HALLOWEEN, CHECK YOUR NULLS")
    return ("Original horror movie poster titled SCHEMA DRIFT: a data engineer with a flashlight faces a glitching "
            "spreadsheet grid crawling across a dark server-room hallway. " + POSTER), b


def poster_legacy_system():
    b = poster("THE LEGACY\nSYSTEM", "It was here before you.",
               "A dusty desert ghost town at high noon with a huge rusty old mainframe computer standing in the middle "
               "of the street like an outlaw, tumbleweeds, warm sepia and gold western atmosphere",
               (246, 430, 340, 460, "A lone developer in a cowboy hat and hoodie facing the mainframe, one hand hovering "
                                    "over a keyboard holstered at the hip like a gunslinger"),
               "NOW SHOWING IN PRODUCTION")
    return ("Original western movie poster titled THE LEGACY SYSTEM: a developer gunslinger faces down a rusty "
            "mainframe in a desert ghost town at high noon. " + POSTER), b


def poster_latency():
    b = poster("LOVE IN THE TIME\nOF LATENCY", "Their messages arrived. Eventually.",
               "A warm cozy coffee shop at golden hour with string lights, spinning loading wheels and chat bubbles "
               "drifting slowly through the air between two tables, soft romantic comedy tones",
               (156, 440, 520, 440, "Two charming young professionals at separate tables smiling at their laptops and "
                                    "glancing shyly at each other"),
               "COMING SOON-ISH")
    return ("Original romantic comedy movie poster titled LOVE IN THE TIME OF LATENCY: two professionals in a cozy "
            "coffee shop smile at their laptops as loading wheels drift between them. " + POSTER), b


# name -> (layout, ResolutionSelector aspect, canvas width, canvas height, seed)
# The canvas must equal what ResolutionSelector computes at 1 MP, multiple 16, because its outputs drive the sizes.
LAYOUTS = {
    "tech-arch-data-pipeline": (data_pipeline, "16:9 (Widescreen)", 1360, 768, 571710880652220),
    "tech-arch-cloud-network": (cloud_network, "16:9 (Widescreen)", 1360, 768, 571710880652220),
    "tech-arch-microservices": (microservices, "16:9 (Widescreen)", 1360, 768, 20261113),
    "tech-arch-layered-stack": (layered_stack, "16:9 (Widescreen)", 1360, 768, 20261112),
    "mkt-webinar-promo":       (mkt_webinar,   "16:9 (Widescreen)", 1360, 768, 31),
    "mkt-social-square":       (mkt_social,    "1:1 (Square)",      1024, 1024, 32),
    "mkt-web-banner":          (mkt_banner,    "21:9 (Ultrawide)",  1568, 672, 33),
    "mkt-product-hero":        (mkt_product,   "16:9 (Widescreen)", 1360, 768, 34),
    "fun-comic-product-mgmt":  (comic_pm,      "21:9 (Ultrawide)",  1568, 672, 41),
    "fun-poster-last-dashboard": (poster_last_dashboard, "2:3 (Portrait Photo)", 832, 1248, 51),
    "fun-poster-deadline-friday": (poster_deadline_friday, "2:3 (Portrait Photo)", 832, 1248, 52),
    "fun-poster-rogue-pipeline": (poster_rogue_pipeline, "2:3 (Portrait Photo)", 832, 1248, 53),
    "fun-comic-standup":       (comic_standup, "21:9 (Ultrawide)",  1568, 672, 42),
    "fun-comic-spreadsheet":   (comic_spreadsheet, "21:9 (Ultrawide)", 1568, 672, 43),
    "fun-comic-ai-strategy":   (comic_ai_strategy, "21:9 (Ultrawide)", 1568, 672, 44),
    "fun-poster-schema-drift": (poster_schema_drift, "2:3 (Portrait Photo)", 832, 1248, 54),
    "fun-poster-legacy-system": (poster_legacy_system, "2:3 (Portrait Photo)", 832, 1248, 55),
    "fun-poster-latency":      (poster_latency, "2:3 (Portrait Photo)", 832, 1248, 56),
}


def refined_size(w, h):
    # the refine pass upscales 1.5x; VAE encoding then trims each side to a multiple of 16
    return int(w * REFINE_SCALE) // 16 * 16, int(h * REFINE_SCALE) // 16 * 16


def logo_position(w, h):
    out_w, _ = refined_size(w, h)
    return out_w - 246, 45            # 193 px logo, 53 px right margin, matching the 2032 px tech-arch output


# ---------------------------------------------------------------- graph surgery
def add_refine_pass(sg):
    """Inside the MOSS subgraph: decode -> upscale 1.5x -> encode -> low-denoise sample -> decode -> output."""
    nodes = {n["id"]: n for n in sg["nodes"]}
    state = sg["state"]
    nid, lid = state["lastNodeId"], state["lastLinkId"]

    def new_id():
        nonlocal nid
        nid += 1
        return nid

    def link(o, os_, t, ts, typ):
        nonlocal lid
        lid += 1
        sg["links"].append({"id": lid, "origin_id": o, "origin_slot": os_, "target_id": t, "target_slot": ts, "type": typ})
        if o in nodes:
            nodes[o]["outputs"][os_].setdefault("links", [])
            nodes[o]["outputs"][os_]["links"] = (nodes[o]["outputs"][os_]["links"] or []) + [lid]
        return lid

    decode1 = next(n for n in sg["nodes"] if n["type"] == "VAEDecode")
    sampler1 = next(n for n in sg["nodes"] if n["type"] == "KSampler")
    vae = next(n for n in sg["nodes"] if n["type"] == "VAELoader")
    out_link = next(l for l in sg["links"] if l["origin_id"] == decode1["id"] and l["target_id"] == sg["outputNode"]["id"])
    in_link = {i["name"]: i["link"] for i in sampler1["inputs"]}
    src = {l["id"]: l for l in sg["links"]}
    model_src = src[in_link["model"]]
    pos_src, neg_src = src[in_link["positive"]], src[in_link["negative"]]
    x0, y0 = decode1["pos"][0] + 40, decode1["pos"][1] + 260

    def node(typ, pos, inputs, outputs, widgets):
        n = {"id": new_id(), "type": typ, "pos": pos, "size": [270, 130], "flags": {}, "order": 99, "mode": 0,
             "inputs": [{"name": a, "type": t, "link": None} for a, t in inputs],
             "outputs": [{"name": a, "type": t, "links": []} for a, t in outputs],
             "properties": {"Node name for S&R": typ}, "widgets_values": widgets}
        sg["nodes"].append(n)
        nodes[n["id"]] = n
        return n

    up = node("ImageScaleBy", [x0, y0], [("image", "IMAGE")], [("IMAGE", "IMAGE")], ["lanczos", REFINE_SCALE])
    enc = node("VAEEncode", [x0 + 300, y0], [("pixels", "IMAGE"), ("vae", "VAE")], [("LATENT", "LATENT")], [])
    ks = node("KSampler", [x0 + 600, y0],
              [("model", "MODEL"), ("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("latent_image", "LATENT")],
              [("LATENT", "LATENT")], [7, "fixed", REFINE_STEPS, 2.5, "er_sde", "simple", REFINE_DENOISE])
    dec = node("VAEDecode", [x0 + 900, y0], [("samples", "LATENT"), ("vae", "VAE")], [("IMAGE", "IMAGE")], [])

    # detach the first decode from the subgraph output and route it through the refine chain
    decode1["outputs"][0]["links"] = [l for l in decode1["outputs"][0]["links"] if l != out_link["id"]]
    up["inputs"][0]["link"] = link(decode1["id"], 0, up["id"], 0, "IMAGE")
    enc["inputs"][0]["link"] = link(up["id"], 0, enc["id"], 0, "IMAGE")
    enc["inputs"][1]["link"] = link(vae["id"], 0, enc["id"], 1, "VAE")
    ks["inputs"][0]["link"] = link(model_src["origin_id"], model_src["origin_slot"], ks["id"], 0, "MODEL")
    ks["inputs"][1]["link"] = link(pos_src["origin_id"], pos_src["origin_slot"], ks["id"], 1, "CONDITIONING")
    ks["inputs"][2]["link"] = link(neg_src["origin_id"], neg_src["origin_slot"], ks["id"], 2, "CONDITIONING")
    ks["inputs"][3]["link"] = link(enc["id"], 0, ks["id"], 3, "LATENT")
    dec["inputs"][0]["link"] = link(ks["id"], 0, dec["id"], 0, "LATENT")
    dec["inputs"][1]["link"] = link(vae["id"], 0, dec["id"], 1, "VAE")
    out_link["origin_id"], out_link["origin_slot"] = dec["id"], 0
    dec["outputs"][0]["links"] = [out_link["id"]]
    state["lastNodeId"], state["lastLinkId"] = nid, lid


def add_logo_composite(w, logo_xy, logo_file=LOGO_FILE):
    """Top level: subgraph IMAGE -> ImageCompositeMasked(official logo, alpha mask) -> SaveImage."""
    nodes = {n["id"]: n for n in w["nodes"]}
    save = next(n for n in w["nodes"] if n["type"] == "SaveImage")
    feed = next(l for l in w["links"] if l[3] == save["id"])
    nid, lid = w["last_node_id"], w["last_link_id"]
    sx, sy = save["pos"]

    def node(typ, pos, inputs, outputs, widgets):
        nonlocal nid
        nid += 1
        n = {"id": nid, "type": typ, "pos": pos, "size": [300, 120], "flags": {}, "order": 99, "mode": 0,
             "inputs": [{"name": a, "type": t, "link": None} for a, t in inputs],
             "outputs": [{"name": a, "type": t, "links": []} for a, t in outputs],
             "properties": {"Node name for S&R": typ}, "widgets_values": widgets}
        w["nodes"].append(n)
        nodes[nid] = n
        return n

    def link(o, os_, t, ts, typ):
        nonlocal lid
        lid += 1
        w["links"].append([lid, o, os_, t, ts, typ])
        nodes[o]["outputs"][os_]["links"].append(lid)
        return lid

    logo = node("LoadImage", [sx - 700, sy + 420], [], [("IMAGE", "IMAGE"), ("MASK", "MASK")], [logo_file, "image"])
    inv = node("InvertMask", [sx - 380, sy + 520], [("mask", "MASK")], [("MASK", "MASK")], [])
    comp_ = node("ImageCompositeMasked", [sx - 380, sy + 300],
                 [("destination", "IMAGE"), ("source", "IMAGE"), ("mask", "MASK")], [("IMAGE", "IMAGE")],
                 [logo_xy[0], logo_xy[1], False])
    # LoadImage's MASK is 1 - alpha; invert it so the logo's opaque pixels are the ones composited
    feed[3], feed[4] = comp_["id"], 0
    comp_["inputs"][0]["link"] = feed[0]
    comp_["inputs"][1]["link"] = link(logo["id"], 0, comp_["id"], 1, "IMAGE")
    inv["inputs"][0]["link"] = link(logo["id"], 1, inv["id"], 0, "MASK")
    comp_["inputs"][2]["link"] = link(inv["id"], 0, comp_["id"], 2, "MASK")
    save["inputs"][0]["link"] = link(comp_["id"], 0, save["id"], 0, "IMAGE")
    w["last_node_id"], w["last_link_id"] = nid, lid


def build(template, out_dirs):
    global W, H
    for name, (fn, aspect, W, H, seed) in LAYOUTS.items():
        prompt, boxes = fn()
        lx, ly = logo_position(W, H)
        logo_box = (lx / REFINE_SCALE - 8, ly / REFINE_SCALE - 8, (lx + 193) / REFINE_SCALE, (ly + 81) / REFINE_SCALE)
        for bx in boxes:
            assert bx["x"] >= 0 and bx["y"] >= 0 and bx["x"] + bx["width"] <= W and bx["y"] + bx["height"] <= H, (name, bx)
            if bx["metadata"]["type"] == "text":    # keep text out of the logo's corner
                overlap = not (bx["x"] + bx["width"] <= logo_box[0] or bx["x"] >= logo_box[2]
                               or bx["y"] + bx["height"] <= logo_box[1] or bx["y"] >= logo_box[3])
                assert not overlap, (name, "text under logo", bx["metadata"]["text"])
        w = copy.deepcopy(template)
        for n in w["nodes"]:
            if n["type"] == "CreateBoundingBoxes":
                n["widgets_values"] = [W, H, copy.deepcopy(boxes), copy.deepcopy(boxes)]
            elif n["type"] == "ResolutionSelector":
                n["widgets_values"] = [aspect, 1, 16]
            elif n["type"] == "MOSSImageLayoutPrompt":
                chars = ", ".join(str(i + 1) for i, bx in enumerate(boxes) if bx["metadata"].get("character"))
                n["widgets_values"] = [prompt, W, H, chars]
            elif n["type"] == "SaveImage":
                n["widgets_values"] = [name]
            elif n["type"] == "MarkdownNote" and "Prompt upsampler is" in json.dumps(n["widgets_values"]):
                n["widgets_values"] = [n["widgets_values"][0].replace(
                    "Prompt upsampler is **on** in this template", "Prompt upsampler is **off** in this workflow")]
        sub = next(n for n in w["nodes"] if n["id"] == 18)
        sub["widgets_values"][1] = False                     # prompt enhancer off: it rewrites the layout JSON
        sub["widgets_values"][2] = NEGATIVE
        sub["widgets_values"][3], sub["widgets_values"][4] = W, H
        sub["widgets_values"][5] = seed
        sg = w["definitions"]["subgraphs"][0]
        for n in sg["nodes"]:
            if n["type"] == "EmptyFlux2LatentImage":
                n["widgets_values"][0:2] = [W, H]
        add_refine_pass(sg)
        add_logo_composite(w, (lx, ly), LOGO_FILE_DARK if name in LIGHT_BACKGROUND else LOGO_FILE)
        for d in out_dirs:
            os.makedirs(d, exist_ok=True)
            json.dump(w, open(os.path.join(d, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{name}: {len(boxes)} boxes")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", help="Local copy of image_moss_image_t2i_bboxes.json (downloaded if omitted)")
    ap.add_argument("--out", action="append",
                    help="Output folder (repeatable). Default: ../custom_node/example_workflows")
    args = ap.parse_args()
    if args.template:
        tpl = json.load(open(args.template, encoding="utf-8"))
    else:
        tpl = json.load(urllib.request.urlopen(TEMPLATE_URL, timeout=60))
    build(tpl, args.out or [os.path.join(HERE, "..", "custom_node", "example_workflows")])
