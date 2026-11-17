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
LIGHT_BACKGROUND = {"fun-comic-product-mgmt", "fun-comic-standup", "fun-comic-spreadsheet", "fun-comic-ai-strategy",
                    "fun-comic-data-quality", "fun-comic-migration", "fun-comic-quick-sync"}

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


def poster_null_and_void():
    b = poster("NULL\n& VOID", "Some values are better left missing.",
               "A rain-soaked city alley at night in black-and-white film noir style, neon reflections in puddles, "
               "faint glowing green question marks drifting through the fog",
               (276, 420, 280, 480, "A hard-boiled detective in a trench coat and fedora standing under a streetlamp, "
                                    "face half in shadow, holding a printed spreadsheet"),
               "NOW STREAMING IN YOUR WAREHOUSE")
    return ("Original film noir movie poster titled NULL AND VOID: a trench-coated detective in a rainy neon alley "
            "full of glowing question marks. " + POSTER), b


def comic_data_quality():
    return comic_strip("Data Quality", [
        ("a bright office with a big monitor showing a chart shooting straight up",
         [(30, 330, 200, 310, f"{ANALYST} jumping with excitement, pointing at the chart"),
          (260, 330, 200, 310, f"{ENGINEER} sipping coffee")],
         [(20, 112, 260, 120, "Revenue is\nup 400%!", "down toward the analyst on the left")]),
        ("the same office in front of the monitor, with only one person in the panel",
         [(140, 330, 220, 310, f"{ENGINEER} alone, wincing apologetically")],
         [(40, 112, 410, 120, "We loaded the table\nfour times.", "down toward the engineer")]),
        ("a corner office with a large window, with exactly three people in the panel",
         [(20, 330, 190, 310, f"{EXEC} on the left, giving an enthusiastic thumbs up"),
          (225, 350, 120, 290, f"{ANALYST}, horrified"),
          (350, 350, 120, 290, f"{ENGINEER}, horrified")],
         [(20, 112, 250, 110, "Great. Let's keep\ndoing that.", "down toward the executive on the left")]),
    ], "Panel one: an analyst celebrates revenue up 400 percent. Panel two: the engineer, alone, admits the table was "
       "loaded four times; the executive does not appear until panel three. Panel three: the executive in the navy suit "
       "says to keep doing that while the analyst and engineer look horrified.")


def mkt_event_vertical():
    b = [background()]
    b += pill(56, 140, 260, 48, "JOIN US LIVE")
    b += [headline(56, 214, 656, 250, "Where Data\nMeets Action")]
    b += [hero_art(0, 500, 768, 560,
                   "An abstract glossy 3D illustration of a glowing stage of stacked platform layers with emerald green "
                   "and cyan data streams rising upward like light beams, on a dark navy background")]
    b += [subline(56, 1092, 656, 70, "Live demos · Expert sessions · Hands-on labs")]
    b += button(56, 1196, 320, 80, "Book a Demo")
    prompt = ("Tall vertical event roll-up banner: a green 'Join Us Live' label and a large two-line headline at the top, "
              "an abstract 3D stage illustration in the middle, a cyan subheading and a green 'Book a Demo' button at the "
              "bottom. " + MKT_STYLE)
    return prompt, b


def mkt_three_steps():
    b = [background(), *header("From Data to Decisions in Three Steps", "A simple path from raw data to action")]
    steps = [("Connect", "Bring every source together in real time",
              "a cluster of glowing database cylinders and cloud shapes linked by light streams"),
             ("Transform", "Clean, govern and shape trusted data",
              "a glowing prism refracting messy particles into neat aligned cubes"),
             ("Analyze", "Turn insights into action with AI",
              "a glowing rising bar chart with a sparkling spark of light above it")]
    for i, (title, body_text, art) in enumerate(steps):
        x = 40 + i * 440
        b += [box(x, 150, 400, 540, "obj", "",
                  "A tall rounded card of darker navy glass with a thin glowing cyan hairline border", (NAVY_DEEP, CYAN))]
        b += [box(x + 24, 174, 64, 64, "obj", "", "A solid bright emerald green circle badge", (GREEN,))]
        b += [box(x + 36, 186, 40, 40, "text", str(i + 1),
                  "A bold white number showing the given text, centered", (WHITE,))]
        b += [hero_art(x + 100, 190, 220, 200, f"A small glossy 3D icon illustration of {art}")]
        b += [box(x + 24, 420, 352, 60, "text", title,
                  "A bold white step title set in the Inter typeface showing the given text, left aligned", (WHITE,))]
        b += [box(x + 24, 490, 352, 110, "text", body_text,
                  "Light cyan body text set in the Inter typeface showing the given text, left aligned", (CYAN,))]
    for x in (440, 880):
        b += [arrow(x, 400, 40, 40)]
    b += [footer("Connect · Transform · Analyze")]
    prompt = ("Three-step infographic: three tall cards side by side numbered one to three, Connect, Transform and "
              "Analyze, each with a small 3D icon, a title and a short description, joined by glowing green arrows. "
              + MKT_STYLE)
    return prompt, b


def mkt_email_header():
    b = [background()]
    b += [headline(64, 180, 900, 170, "Your Monthly\nData Digest")]
    b += [subline(64, 380, 900, 60, "News, tips and product updates for data teams")]
    b += [box(64, 470, 120, 6, "obj", "", "A short thin emerald green accent bar", (GREEN,))]
    b += [hero_art(980, 110, 560, 520,
                   "An abstract glossy 3D illustration of floating envelopes and glowing chart cards orbiting a soft "
                   "emerald green light core")]
    prompt = ("Wide email newsletter header: a large two-line headline, a cyan subheading and a green accent bar on the "
              "left, with an abstract 3D illustration of floating envelopes and chart cards on the right. " + MKT_STYLE)
    return prompt, b


FUN_PRINT = ("Original glossy print design, rich color, crisp detail, every word sharp and perfectly legible, "
             "no logos.")


def fun_trading_card():
    b = [box(0, 0, W, H, "obj", "", "A dark navy background", (NAVY_DEEP,))]
    b += [box(24, 104, 784, 1120, "obj", "",
              "An ornate collectible trading card frame with shimmering holographic emerald green and cyan foil "
              "edges, simple rounded corners with no emblems or shields, and a dark inner panel", (GREEN, CYAN, NAVY_DEEP))]
    b += [box(60, 136, 560, 60, "text", "THE DATA ENGINEER",
              "Bold white fantasy-style card title showing the given text, left aligned", (WHITE,))]
    b += [person(120, 210, 592, 580, "A heroic data engineer character in a hoodie with glowing green goggles, "
                                     "holding a wrench and a plain unmarked laptop with a blank lid, dramatic fantasy "
                                     "trading-card illustration, no symbols or logos on clothing or objects")]
    b += [box(60, 810, 712, 40, "text", "LEGENDARY · PIPELINE CLASS",
              "Small bold emerald green uppercase card type line showing the given text, centered", (GREEN,))]
    b += [box(100, 870, 632, 190, "text", "UPTIME  99\nDEBUGGING  97\nCOFFEE  100",
              "Three lines of bold white card stats showing the given text, left aligned, evenly spaced", (WHITE,))]
    b += [box(80, 1080, 672, 100, "text", "Fixes in production what\nothers won't admit is broken.",
              "Italic light grey flavor text showing the given text, centered", (GRAY,))]
    prompt = ("Original collectible fantasy trading card for THE DATA ENGINEER: ornate holographic frame, heroic "
              "character art, a type line, three stats and italic flavor text. " + FUN_PRINT)
    return prompt, b


def fun_magazine_cover():
    b = [box(0, 0, W, H, "obj", "", "A bright clean studio backdrop in soft emerald green", (GREEN, WHITE))]
    b += [box(40, 40, 620, 150, "text", "DATA WEEKLY",
              "A huge bold white magazine masthead showing the given text, left aligned, tightly kerned", (WHITE,))]
    b += [person(140, 230, 560, 840, "A confident data scientist in a sharp blazer posing for a glossy magazine cover, "
                                     "arms crossed, studio lighting")]
    b += [box(40, 300, 280, 150, "text", "10 QUERIES\nTHAT WILL\nCHANGE YOUR LIFE",
              "Bold black uppercase magazine cover line showing the given text, left aligned", (INK,))]
    b += [box(530, 640, 270, 150, "text", "IS YOUR\nDASHBOARD\nLYING TO YOU?",
              "Bold white uppercase magazine cover line on a dark band showing the given text, left aligned", (WHITE,))]
    b += [box(40, 1080, 752, 90, "text", "EXCLUSIVE: WE ASKED AI\nTO WRITE THIS HEADLINE",
              "Bold yellow uppercase magazine cover line showing the given text, left aligned", ("#FFD200",))]
    b += [box(40, 1192, 420, 30, "text", "ISSUE 42 · NOVEMBER",
              "Small white uppercase issue line showing the given text, left aligned", (WHITE,))]
    prompt = ("Original spoof glossy magazine cover titled DATA WEEKLY: a confident data scientist on a green studio "
              "backdrop surrounded by bold cover lines. " + FUN_PRINT)
    return prompt, b


# ---------------------------------------------------------------- more technical architectures
def lakehouse():
    b = [background(), *header("Open Lakehouse Architecture",
                               "Streaming changes into Apache Iceberg tables that any engine can query")]
    b += zone(28, 150, 250, 556, "Sources")
    b += comp(44, 214, 218, 76, "Operational DBs", "database cylinder")
    b += comp(44, 354, 218, 76, "SaaS Apps", "cloud")
    b += comp(44, 494, 218, 76, "Files & Streams", "event stream")
    for y in (236, 376, 516):
        b += [arrow(278, y, 40, 32)]
    b += comp(318, 214, 200, 356, "Qlik Talend\nCloud", "data flow")
    b += [edge_label(308, 584, 220, "CDC · streaming")]
    b += [arrow(518, 376, 40, 32)]
    b += zone(558, 150, 520, 556, "Qlik Open Lakehouse")
    b += comp(576, 214, 484, 76, "Bronze · Raw Iceberg", "layers")
    b += [arrow(802, 292, 32, 60, "down")]
    b += comp(576, 354, 484, 76, "Silver · Cleaned Tables", "table grid")
    b += [arrow(802, 432, 32, 60, "down")]
    b += comp(576, 494, 484, 76, "Gold · Data Products", "star")
    b += [edge_label(568, 600, 500, "adaptive optimizer · open catalog")]
    b += [arrow(1078, 376, 34, 32)]
    b += zone(1112, 150, 224, 556, "Query Engines")
    for i, (name, icon) in enumerate((("Spark", "lightning bolt"), ("Trino", "magnifying glass"),
                                      ("Snowflake", "snowflake"), ("Qlik Cloud\nAnalytics", "bar chart"))):
        b += comp(1124, 214 + i * 116, 200, 76, name, icon)
    b += [footer("Open table formats · one copy of the data · any engine")]
    prompt = ("Technical open lakehouse architecture: operational databases, SaaS apps and files on the left stream "
              "through Qlik Talend Cloud into Qlik Open Lakehouse with bronze, silver and gold Apache Iceberg layers, "
              "queried by Spark, Trino, Snowflake and Qlik Cloud Analytics on the right. " + STYLE)
    return prompt, b


def rag_ai():
    b = [background(), *header("Retrieval-Augmented AI Architecture",
                               "Grounding AI answers in governed enterprise data")]
    b += zone(28, 150, 250, 556, "Knowledge Sources")
    b += comp(44, 214, 218, 76, "Documents", "document")
    b += comp(44, 354, 218, 76, "Wikis & Tickets", "chat bubble")
    b += comp(44, 494, 218, 76, "Data Products", "database cylinder")
    b += [arrow(278, 376, 40, 32)]
    b += zone(318, 150, 300, 556, "Ingestion")
    b += comp(334, 214, 268, 76, "Chunking", "scissors")
    b += [arrow(452, 292, 32, 60, "down")]
    b += comp(334, 354, 268, 76, "Embeddings", "network nodes")
    b += [arrow(452, 432, 32, 60, "down")]
    b += comp(334, 494, 268, 76, "Metadata & ACLs", "lock")
    b += [arrow(618, 376, 40, 32)]
    b += comp(658, 316, 220, 130, "Vector Store", "database cylinder")
    b += [edge_label(648, 456, 240, "semantic search")]
    b += [arrow(878, 376, 40, 32)]
    b += zone(918, 150, 418, 556, "AI Experience")
    b += comp(936, 214, 382, 76, "LLM Orchestrator", "brain")
    b += comp(936, 354, 382, 76, "Qlik Answers", "chat bubble")
    b += comp(936, 494, 382, 76, "Guardrails & Audit", "shield check")
    b += [footer("Every answer cites its source · user permissions respected end to end")]
    prompt = ("Technical retrieval-augmented generation architecture: documents, wikis and data products on the left "
              "are chunked, embedded and tagged with access controls, stored in a vector store, and used by an LLM "
              "orchestrator, Qlik Answers and a guardrails layer on the right. " + STYLE)
    return prompt, b


def hybrid_cloud():
    b = [background(), *header("Hybrid Cloud Data Movement",
                               "Securely replicating on-premises systems to the cloud")]
    b += zone(28, 150, 400, 556, "On-Premises Data Center")
    b += comp(44, 214, 368, 76, "Mainframe", "server rack")
    b += comp(44, 330, 368, 76, "ERP Database", "database cylinder")
    b += comp(44, 446, 368, 76, "Oracle Database", "database cylinder")
    b += [arrow(212, 524, 32, 48, "down")]
    b += comp(44, 574, 368, 100, "Qlik Data Movement\nGateway", "gateway")
    b += [arrow(428, 606, 60, 32)]
    b += [edge_label(418, 646, 80, "TLS")]
    b += zone(488, 150, 848, 556, "Cloud")
    b += comp(508, 214, 380, 76, "Cloud Data Warehouse", "warehouse")
    b += comp(508, 330, 380, 76, "Object Storage", "storage bucket")
    b += [arrow(682, 412, 32, 156, "up")]
    b += comp(508, 574, 380, 100, "Qlik Talend Cloud", "data flow")
    b += [arrow(888, 236, 32, 32), arrow(888, 352, 32, 32)]
    b += comp(920, 214, 396, 76, "Qlik Cloud Analytics", "bar chart")
    b += comp(920, 330, 396, 76, "Qlik Answers", "chat bubble")
    b += comp(920, 446, 396, 76, "Qlik Automate", "lightning bolt")
    b += [footer("Outbound-only connection · no inbound firewall ports · encrypted in transit")]
    prompt = ("Technical hybrid cloud architecture: a mainframe, an ERP database and an Oracle database in an "
              "on-premises data center replicate through a Qlik Data Movement Gateway over an encrypted link to Qlik "
              "Talend Cloud, which loads a cloud data warehouse and object storage that feed Qlik Cloud Analytics, "
              "Qlik Answers and Qlik Automate. " + STYLE)
    return prompt, b


def iot_streaming():
    b = [background(), *header("Real-Time IoT Analytics", "From sensor events to live dashboards and alerts")]
    b += zone(28, 150, 240, 556, "Edge Devices")
    b += comp(44, 214, 208, 76, "Sensors", "thermometer")
    b += comp(44, 354, 208, 76, "Machines", "gear")
    b += comp(44, 494, 208, 76, "Vehicles", "truck")
    b += [arrow(268, 376, 40, 32)]
    b += comp(308, 316, 190, 130, "IoT Hub", "antenna")
    b += [edge_label(298, 456, 210, "MQTT · millions/sec")]
    b += [arrow(498, 376, 40, 32)]
    b += comp(538, 214, 200, 356, "Stream\nProcessing", "lightning bolt")
    b += [arrow(738, 264, 50, 32), arrow(738, 560, 50, 32)]
    b += zone(788, 150, 548, 260, "Hot Path · Seconds")
    b += comp(806, 214, 250, 76, "Anomaly Alerts", "bell")
    b += comp(1068, 214, 250, 76, "Qlik Automate", "lightning bolt")
    b += [edge_label(806, 306, 512, "real-time triggers and notifications")]
    b += zone(788, 446, 548, 260, "Cold Path · History")
    b += comp(806, 510, 250, 76, "Lakehouse Storage", "database cylinder")
    b += comp(1068, 510, 250, 76, "Qlik Sense\nDashboards", "bar chart")
    b += [edge_label(806, 602, 512, "trends · forecasting · machine learning")]
    b += [footer("Hot path for alerts in seconds · cold path for history and prediction")]
    prompt = ("Technical real-time IoT architecture: sensors, machines and vehicles on the left send events to an IoT "
              "hub and a stream processing engine, which splits into a hot path of anomaly alerts and Qlik Automate "
              "and a cold path of lakehouse storage and Qlik Sense dashboards on the right. " + STYLE)
    return prompt, b


# ---------------------------------------------------------------- more marketing assets
def mkt_quote_card():
    b = [background()]
    b += [box(64, 90, 150, 120, "obj", "", "A large stylized emerald green opening quotation mark shape", (GREEN,))]
    b += [box(64, 230, 896, 330, "text", "We went from waiting days\nfor reports to answering\nquestions in minutes.",
              "A large bold white quotation set in the Inter typeface showing the given text with no quotation marks, left aligned", (WHITE,))]
    b += [box(64, 596, 120, 6, "obj", "", "A short thin emerald green accent bar", (GREEN,))]
    b += [box(64, 624, 640, 44, "text", "Head of Data, Global Retailer",
              "Light cyan attribution text set in the Inter typeface showing the given text, left aligned", (CYAN,))]
    b += button(64, 900, 300, 72, "Read the Story")
    b += [hero_art(560, 680, 464, 344,
                   "An abstract glossy 3D illustration of glowing emerald green and cyan data ribbons curving upward")]
    prompt = ("Square customer testimonial card: a large green quotation mark, a three-line quotation, a green accent "
              "bar, an attribution line and a green 'Read the Story' button, with abstract 3D data ribbons in the "
              "corner. " + MKT_STYLE)
    return prompt, b


def mkt_stats():
    b = [background(), *header("The Impact of Trusted Data", "What data teams report after modernizing")]
    stats = [("3x", "faster time\nto insight", "a glowing upward rocket trail"),
             ("60%", "less time spent\npreparing data", "a glowing hourglass with light flowing through it"),
             ("24/7", "real-time data\ndelivery", "a glowing circular clock ring of light")]
    for i, (num, label, art) in enumerate(stats):
        x = 40 + i * 440
        b += [box(x, 150, 400, 540, "obj", "",
                  "A tall rounded card of darker navy glass with a thin glowing cyan hairline border", (NAVY_DEEP, CYAN))]
        b += [box(x + 24, 190, 352, 170, "text", num,
                  "A huge bold emerald green number set in the Inter typeface showing the given text, left aligned", (GREEN,))]
        b += [box(x + 24, 380, 352, 110, "text", label,
                  "Bold white text set in the Inter typeface showing the given text, left aligned", (WHITE,))]
        b += [hero_art(x + 24, 510, 352, 160, f"A small glossy 3D illustration of {art}")]
    b += [footer("Illustrative figures · replace with your own results")]
    prompt = ("Statistics callout graphic: three tall glass cards side by side, each with a huge green number, a "
              "short white label and a small 3D illustration. " + MKT_STYLE)
    return prompt, b


def mkt_before_after():
    b = [background(), *header("Before and After a Modern Data Platform",
                               "From spreadsheet chaos to governed, real-time insight")]
    b += [box(40, 150, 620, 540, "obj", "", "A rounded card of dull dark charcoal grey glass, muted and lifeless",
              (CHARCOAL, NAVY_DEEP))]
    b += [box(64, 170, 300, 44, "text", "BEFORE",
              "Bold uppercase grey letter-spaced label set in the Inter typeface showing the given text, left aligned", (GRAY,))]
    b += [box(64, 230, 572, 280, "obj", "",
              "A messy tangle of overlapping paper spreadsheets, sticky notes and broken grey cables in dull grey tones, "
              "completely free of any text, letters, numbers, symbols or logos", (GRAY, CHARCOAL))]
    b += [box(64, 540, 572, 120, "text", "Manual exports · Stale reports\nConflicting numbers",
              "Grey body text set in the Inter typeface showing the given text, left aligned", (GRAY,))]
    b += [arrow(660, 400, 40, 40)]
    b += [box(700, 150, 620, 540, "obj", "",
              "A rounded card of deep navy glass with a glowing emerald green hairline border", (NAVY_DEEP, GREEN))]
    b += [box(724, 170, 300, 44, "text", "AFTER",
              "Bold uppercase emerald green letter-spaced label set in the Inter typeface showing the given text, left aligned",
              (GREEN,))]
    b += [hero_art(724, 230, 572, 280,
                   "A neat glowing 3D platform of aligned data blocks connected by clean emerald green and cyan light streams")]
    b += [box(724, 540, 572, 120, "text", "Automated pipelines · Live dashboards\nOne trusted version of the truth",
              "White body text set in the Inter typeface showing the given text, left aligned", (WHITE,))]
    prompt = ("Before and after comparison graphic: a dull grey card on the left showing tangled spreadsheets and "
              "cables, a green arrow, and a glowing navy card on the right showing a neat connected data platform, each "
              "with a label and two lines of text. " + MKT_STYLE)
    return prompt, b


def mkt_carousel_cover():
    b = [background()]
    b += pill(64, 110, 220, 46, "DATA TIPS")
    b += [headline(64, 184, 880, 300, "5 Signs Your\nData Stack Needs\nan Upgrade")]
    b += [hero_art(424, 500, 600, 340,
                   "An abstract glossy 3D illustration of a stack of glowing platform blocks with one cracked block "
                   "leaking sparks of emerald green light")]
    b += [subline(64, 868, 520, 60, "Swipe to see them all")]
    b += [arrow(600, 876, 90, 44)]
    prompt = ("Square social carousel cover: a green 'Data Tips' label, a large three-line headline, a 3D illustration "
              "of a stack of platform blocks with one cracked block, and a cyan 'Swipe to see them all' line with a green "
              "arrow. " + MKT_STYLE)
    return prompt, b


def mkt_ebook_cover():
    b = [background()]
    b += pill(56, 140, 200, 46, "EBOOK")
    b += [headline(56, 214, 720, 320, "The AI-Ready\nData Playbook")]
    b += [subline(56, 556, 720, 100, "A practical guide to building\ntrusted data for AI")]
    b += [hero_art(0, 690, 832, 420,
                   "An abstract glossy 3D illustration of an open book whose pages rise into glowing layers of emerald "
                   "green and cyan data")]
    b += [box(56, 1150, 720, 40, "text", "2026 EDITION",
              "Small light grey uppercase letter-spaced text set in the Inter typeface showing the given text, left aligned",
              (GRAY,))]
    prompt = ("Portrait ebook cover: a green 'Ebook' label, a large two-line title, a cyan subtitle, a 3D illustration of "
              "an open book rising into glowing data layers, and a small edition line. " + MKT_STYLE)
    return prompt, b


# ---------------------------------------------------------------- more fun
def comic_migration():
    return comic_strip("The Cloud Migration", [
        ("a boardroom with a presentation screen showing a simple cloud shape",
         [(140, 330, 220, 310, f"{EXEC} standing with arms spread wide")],
         [(40, 112, 410, 120, "We're moving everything\nto the cloud!", "down toward the executive")]),
        ("the same boardroom, with only one person in the panel",
         [(140, 330, 220, 310, f"{ENGINEER} alone, raising one eyebrow")],
         [(40, 112, 410, 120, "Including the\nmainframe from 1987?", "down toward the engineer")]),
        ("a dusty server room with a huge beige mainframe computer on the right side, with exactly two people in the panel",
         [(30, 330, 200, 310, f"{ENGINEER} on the left with a flat, tired expression"),
          (260, 330, 200, 310, f"{EXEC} on the right hugging the beige mainframe protectively")],
         [(250, 112, 220, 110, "Not Gerald.\nGerald stays.", "a single tail pointing down toward the executive on the right")]),
    ], "Panel one: the executive announces everything is moving to the cloud. Panel two: the engineer, alone, asks "
       "about the mainframe from 1987. Panel three: the tired engineer stands on the left while the executive on the right hugs the old beige "
       "mainframe and says Gerald stays.")


def comic_meeting():
    return comic_strip("Quick Sync", [
        ("a small meeting room with a wall clock showing ten o'clock",
         [(30, 330, 200, 310, f"{PM} smiling and holding a laptop"),
          (260, 330, 200, 310, f"{ENGINEER} sitting down")],
         [(20, 112, 260, 110, "Quick sync.\nFive minutes.", "down toward the product manager on the left")]),
        ("the same meeting room, the wall clock now showing eleven o'clock, with only one person in the panel",
         [(140, 330, 220, 310, f"{ENGINEER} alone, slumped in a chair, exhausted, speaking")],
         [(40, 112, 410, 110, "It's been\nan hour.", "down toward the engineer")]),
        ("the same meeting room",
         [(30, 330, 200, 310, f"{PM} beaming"),
          (260, 330, 200, 310, f"{ENGINEER} with head down on the table")],
         [(20, 112, 260, 110, "Great! Let's book\na follow-up.", "down toward the product manager on the left")]),
    ], "Panel one: the product manager promises a five-minute sync. Panel two: an hour later the slumped engineer, alone in the "
       "panel, says it has been an hour. Panel three: the beaming product manager suggests a follow-up while the engineer puts "
       "their head on the table.")


def poster_scope_creep():
    b = poster("SCOPE\nCREEP", "It started as one small feature.",
               "A giant towering monster made of thousands of yellow sticky notes and paper feature requests stomping "
               "through a city skyline at dusk, debris flying, epic monster movie atmosphere",
               (236, 520, 360, 370, "A small terrified team of three office workers in the street looking up at the "
                                    "monster"),
               "NOW IN EXTENDED EDITION")
    return ("Original monster movie poster titled SCOPE CREEP: a giant monster made of sticky notes stomps through a "
            "city while a small team looks up in terror. " + POSTER), b


def poster_merge_conflict():
    b = poster("MERGE\nCONFLICT", "Only one branch survives.",
               "A dramatic rooftop at night in pouring rain, two glowing branching lines of light, one green and one "
               "orange, colliding in the sky in a burst of sparks, explosive action movie atmosphere",
               (156, 430, 520, 450, "Two rival developers facing each other in a tense standoff on the rooftop, each "
                                    "holding a glowing laptop like a weapon, the laptop screens plain glowing light "
                                    "with no logos, letters or symbols"),
               "IN THEATERS AFTER CODE FREEZE")
    return ("Original action movie poster titled MERGE CONFLICT: two rival developers face off on a rainy rooftop as "
            "two branches of light collide above them. " + POSTER), b


def fun_motivational():
    b = [box(0, 0, W, H, "obj", "", "A solid black background", ("#000000",))]
    b += [box(90, 134, 652, 652, "obj", "", "A thin white rectangular border framing a photograph", (WHITE,))]
    b += [person(96, 140, 640, 640, "A photograph of a lone office worker at a desk buried under towering stacks of "
                                    "printed reports, warm dramatic window light, completely free of text")]
    b += [box(56, 830, 720, 120, "text", "REPORTING",
              "A huge white letter-spaced serif uppercase title showing the given text, centered", (WHITE,))]
    b += [box(76, 980, 680, 130, "text", "Because nobody reads it,\nbut everyone wants it on Monday.",
              "White serif caption text showing the given text, centered", (WHITE,))]
    prompt = ("Original spoof motivational office poster: a solid black background, a framed photograph of an office "
              "worker buried in printed reports, a large serif title and a deadpan two-line caption. " + FUN_PRINT)
    return prompt, b


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
    "fun-poster-null-and-void": (poster_null_and_void, "2:3 (Portrait Photo)", 832, 1248, 57),
    "fun-comic-data-quality":  (comic_data_quality, "21:9 (Ultrawide)", 1568, 672, 46),
    "fun-trading-card":        (fun_trading_card, "2:3 (Portrait Photo)", 832, 1248, 62),
    "fun-magazine-cover":      (fun_magazine_cover, "2:3 (Portrait Photo)", 832, 1248, 62),
    "mkt-event-vertical":      (mkt_event_vertical, "9:16 (Portrait Widescreen)", 768, 1360, 35),
    "mkt-three-steps":         (mkt_three_steps, "16:9 (Widescreen)", 1360, 768, 36),
    "mkt-email-header":        (mkt_email_header, "21:9 (Ultrawide)", 1568, 672, 37),
    "tech-arch-lakehouse":     (lakehouse,     "16:9 (Widescreen)", 1360, 768, 21),
    "tech-arch-rag-ai":        (rag_ai,        "16:9 (Widescreen)", 1360, 768, 25),
    "tech-arch-hybrid-cloud":  (hybrid_cloud,  "16:9 (Widescreen)", 1360, 768, 23),
    "tech-arch-iot-streaming": (iot_streaming, "16:9 (Widescreen)", 1360, 768, 24),
    "mkt-quote-card":          (mkt_quote_card, "1:1 (Square)",     1024, 1024, 38),
    "mkt-stats":               (mkt_stats,     "16:9 (Widescreen)", 1360, 768, 39),
    "mkt-before-after":        (mkt_before_after, "16:9 (Widescreen)", 1360, 768, 40),
    "mkt-carousel-cover":      (mkt_carousel_cover, "1:1 (Square)", 1024, 1024, 41),
    "mkt-ebook-cover":         (mkt_ebook_cover, "2:3 (Portrait Photo)", 832, 1248, 42),
    "fun-comic-migration":     (comic_migration, "21:9 (Ultrawide)", 1568, 672, 47),
    "fun-comic-quick-sync":    (comic_meeting, "21:9 (Ultrawide)",  1568, 672, 48),
    "fun-poster-scope-creep":  (poster_scope_creep, "2:3 (Portrait Photo)", 832, 1248, 58),
    "fun-poster-merge-conflict": (poster_merge_conflict, "2:3 (Portrait Photo)", 832, 1248, 59),
    "fun-motivational-poster": (fun_motivational, "2:3 (Portrait Photo)", 832, 1248, 63),
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


# ---------------------------------------------------------------- photo edits (MOSS-Image edit LoRA)
EDIT_TEMPLATE_URL = ("https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/"
                     "templates/image_moss_image_edit.json")
EDIT_SAMPLE = "two_women_berets_floral_jackets.png"   # the template's own sample photo; swap it in Load Image
EDIT_MEGAPIXELS = 0.5                                  # raise to 1.0 on GPUs with more than 4 GB
CARTOON = ("Change only the art style of the whole image to a clean flat cartoon illustration with bold black ink "
           "outlines, simple cel shading and bright flat colors. Keep every person, their faces, expressions, "
           "hairstyles, glasses, clothing, poses, the framing and the background layout unchanged.")
EDITS = {
    "img-photo-to-cartoon": CARTOON,
    "img-photo-to-cartoon-bowtie": CARTOON[:-1] + (", and add a bright lime-green bow tie with small white polka "
                                                   "dots at the shirt collar."),
}


def build_edits(template, out_dirs):
    for name, instruction in EDITS.items():
        w = copy.deepcopy(template)
        for n in w["nodes"]:
            if n["type"] == "LoadImage":
                n["widgets_values"][0] = EDIT_SAMPLE
            elif n["type"] == "ImageScaleToTotalPixels":
                # 1 MP plus the reference copy needs a 4 GB block in the sampler; 0.5 MP fits a 4 GB GPU
                n["widgets_values"][1] = EDIT_MEGAPIXELS
            elif n["type"] == "SaveImage":
                n["widgets_values"] = [name]
            elif n["type"] == "TextEncodeMOSSImageEdit" and n["widgets_values"][0].startswith("Change only"):
                n["widgets_values"][0] = instruction
        for d in out_dirs:
            json.dump(w, open(os.path.join(d, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{name}: edit")


# ---------------------------------------------------------------- photo to cartoon, image-to-image (fits a 4 GB GPU)
# At 0.83 the result is a true cartoon, but the model only keeps a likeness for the features the prompt names
# (hair or baldness, skin, facial hair, glasses, clothing); below about 0.8 it stays a retouched photo.
I2I_SUBJECT = ("two young women with brown bob haircuts and bangs in front of a grey block wall: on the left one with "
               "closed eyes, round gold glasses, a dark green beret and a pink floral jacket over a white blouse; on the "
               "right one in a navy beret and a navy cardigan embroidered with red flowers over a white blouse")       # describes the sample photo; replace it with a description of yours
I2I_CARTOON = (f"A clean flat cartoon illustration of {I2I_SUBJECT}, keeping their faces, expressions and pose, "
               "bold black ink outlines, simple cel shading, bright flat colors, friendly and polished")
I2I_NEGATIVE = "photo, photorealistic, worst quality, blurry, deformed face, extra people, text, watermark, logo"
I2I_DENOISE = 0.83      # lower keeps more of the photo, higher is more cartoon
I2I_NOTE = ("## Photo to cartoon\n\n1. Load your photo in **Load Image**.\n2. In the top **CLIP Text Encode**, replace "
            "the description after *cartoon illustration of* with your subject: hair (or bald), skin tone, facial hair, "
            "glasses, clothing. Add extras the same way, e.g. *with a lime-green polka-dot bow tie*.\n3. Run.\n\n"
            "Denoise 0.83 gives a true cartoon. The model keeps only the features you describe, so describe them. "
            "Below about 0.8 the result stays close to the photo.")


def build_i2i(out_dirs, name="img-photo-to-cartoon-lite"):
    nodes, links = [], []

    def node(nid, typ, pos, widgets, inputs=(), outputs=()):
        nodes.append({"id": nid, "type": typ, "pos": pos, "size": [320, 120], "flags": {}, "order": nid, "mode": 0,
                      "inputs": [{"name": a, "type": t, "link": None} for a, t in inputs],
                      "outputs": [{"name": a, "type": t, "links": []} for a, t in outputs],
                      "properties": {"Node name for S&R": typ}, "widgets_values": widgets})

    def link(src, slot, dst, dslot, typ):
        lid = len(links) + 1
        links.append([lid, src, slot, dst, dslot, typ])
        by = {n["id"]: n for n in nodes}
        by[src]["outputs"][slot]["links"].append(lid)
        by[dst]["inputs"][dslot]["link"] = lid

    node(1, "UNETLoader", [0, 0], ["moss_image_sft_int8_convrot.safetensors", "default"], outputs=[("MODEL", "MODEL")])
    node(2, "CLIPLoader", [0, 160], ["qwen3.5_9b_w4a8_gptq.safetensors", "moss_image", "default"], outputs=[("CLIP", "CLIP")])
    node(3, "VAELoader", [0, 320], ["flux2-vae_small.safetensors"], outputs=[("VAE", "VAE")])
    node(4, "CLIPTextEncode", [380, 0], [I2I_CARTOON], [("clip", "CLIP")], [("CONDITIONING", "CONDITIONING")])
    node(5, "CLIPTextEncode", [380, 200], [I2I_NEGATIVE], [("clip", "CLIP")], [("CONDITIONING", "CONDITIONING")])
    node(6, "LoadImage", [0, 480], [EDIT_SAMPLE, "image"], outputs=[("IMAGE", "IMAGE"), ("MASK", "MASK")])
    node(7, "ImageScaleToTotalPixels", [380, 480], ["lanczos", 1.0, 16], [("image", "IMAGE")], [("IMAGE", "IMAGE")])
    node(8, "VAEEncode", [760, 480], [], [("pixels", "IMAGE"), ("vae", "VAE")], [("LATENT", "LATENT")])
    node(9, "KSampler", [800, 0], [7, "fixed", 25, 3.0, "euler", "simple", I2I_DENOISE],
         [("model", "MODEL"), ("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("latent_image", "LATENT")],
         [("LATENT", "LATENT")])
    node(10, "VAEDecode", [1180, 0], [], [("samples", "LATENT"), ("vae", "VAE")], [("IMAGE", "IMAGE")])
    node(11, "SaveImage", [1180, 160], [name], [("images", "IMAGE")])
    node(12, "MarkdownNote", [0, -260], [I2I_NOTE])
    nodes[-1]["size"] = [700, 220]
    link(1, 0, 9, 0, "MODEL")
    link(2, 0, 4, 0, "CLIP")
    link(2, 0, 5, 0, "CLIP")
    link(4, 0, 9, 1, "CONDITIONING")
    link(5, 0, 9, 2, "CONDITIONING")
    link(6, 0, 7, 0, "IMAGE")
    link(7, 0, 8, 0, "IMAGE")
    link(3, 0, 8, 1, "VAE")
    link(8, 0, 9, 3, "LATENT")
    link(9, 0, 10, 0, "LATENT")
    link(3, 0, 10, 1, "VAE")
    link(10, 0, 11, 0, "IMAGE")
    w = {"last_node_id": len(nodes), "last_link_id": len(links), "nodes": nodes, "links": links,
         "groups": [], "config": {}, "extra": {}, "version": 0.4}
    for d in out_dirs:
        json.dump(w, open(os.path.join(d, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{name}: image-to-image")


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
    outs = args.out or [os.path.join(HERE, "..", "custom_node", "example_workflows")]
    build(tpl, outs)
    build_edits(json.load(urllib.request.urlopen(EDIT_TEMPLATE_URL, timeout=60)), outs)
    build_i2i(outs)
