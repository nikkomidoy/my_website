"""StreamField blocks shared by content pages and blog posts.

Markdown blocks render through `markdownify` (nh3-sanitized), so AI drafts and
hand-written Markdown take the same path as before the Wagtail move.
"""

from django.utils.html import format_html
from wagtail import blocks
from wagtail.images.blocks import ImageBlock

from .templatetags.markdown_extras import markdownify

RICH_TEXT_FEATURES = ["h2", "h3", "h4", "bold", "italic", "link", "ol", "ul", "code", "hr"]


class MarkdownBlock(blocks.TextBlock):
    def __init__(self, **kwargs):
        kwargs.setdefault("rows", 12)
        super().__init__(**kwargs)

    def render_basic(self, value, context=None):
        return markdownify(value)

    class Meta:
        icon = "doc-full"
        label = "Markdown"


class CodeBlock(blocks.StructBlock):
    language = blocks.ChoiceBlock(
        choices=[
            ("python", "Python"),
            ("bash", "Shell"),
            ("sql", "SQL"),
            ("javascript", "JavaScript"),
            ("typescript", "TypeScript"),
            ("json", "JSON"),
            ("yaml", "YAML"),
            ("html", "HTML"),
            ("text", "Plain text"),
        ],
        default="python",
    )
    code = blocks.TextBlock()

    def render_basic(self, value, context=None):
        return format_html(
            '<pre><code class="language-{}">{}</code></pre>', value["language"], value["code"]
        )

    class Meta:
        icon = "code"


class FigureBlock(blocks.StructBlock):
    image = ImageBlock()
    caption = blocks.CharBlock(required=False)

    class Meta:
        icon = "image"
        template = "blocks/figure.html"


class BodyBlock(blocks.StreamBlock):
    markdown = MarkdownBlock()
    rich_text = blocks.RichTextBlock(features=RICH_TEXT_FEATURES, label="Rich text")
    figure = FigureBlock()
    code = CodeBlock()
    quote = blocks.BlockQuoteBlock()
