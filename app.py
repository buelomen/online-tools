from flask import Flask, render_template, request, send_file, abort
from PIL import Image
import io
import uuid
import os
import markdown
import re


# =========================================================
# App
# =========================================================

app = Flask(__name__)


# =========================================================
# Paths
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARTICLES_DIR = os.path.join(
    BASE_DIR,
    "articles"
)


# =========================================================
# Home
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# Article System
# =========================================================

def load_article(language, slug):
    """
    Load article from:

    articles/{language}/{slug}.md
    """

    article_path = os.path.join(
        ARTICLES_DIR,
        language,
        f"{slug}.md"
    )

    # Article does not exist
    if not os.path.isfile(article_path):
        return None

    try:
        with open(
            article_path,
            "r",
            encoding="utf-8"
        ) as file:
            raw_content = file.read()

    except Exception:
        return None

    metadata = {}
    markdown_content = raw_content

    # -----------------------------------------------------
    # Front Matter
    # -----------------------------------------------------

    if raw_content.startswith("---"):

        parts = raw_content.split(
            "---",
            2
        )

        if len(parts) == 3:

            front_matter = parts[1].strip()
            markdown_content = parts[2].strip()

            for line in front_matter.splitlines():

                line = line.strip()

                if not line or ":" not in line:
                    continue

                key, value = line.split(
                    ":",
                    1
                )

                key = key.strip()
                value = value.strip()

                # Remove quotation marks
                if (
                    len(value) >= 2
                    and value[0] == value[-1]
                    and value[0] in ("'", '"')
                ):
                    value = value[1:-1]

                metadata[key] = value

    # -----------------------------------------------------
    # Markdown → HTML
    # -----------------------------------------------------

    html_content = markdown.markdown(
        markdown_content,
        extensions=[
            "extra",
            "toc",
            "sane_lists"
        ]
    )

    # -----------------------------------------------------
    # Reading Time
    # -----------------------------------------------------

    plain_text = re.sub(
        r"<[^>]+>",
        " ",
        html_content
    )

    words = re.findall(
        r"\b[\w'-]+\b",
        plain_text,
        flags=re.UNICODE
    )

    word_count = len(words)

    # Approximately 200 words per minute
    reading_time = max(
        1,
        round(word_count / 200)
    )

    # -----------------------------------------------------
    # Article Metadata
    # -----------------------------------------------------

    metadata["slug"] = slug
    metadata["language"] = language
    metadata["reading_time"] = reading_time
    metadata["word_count"] = word_count

    # Default values
    metadata.setdefault(
        "title",
        slug.replace("-", " ").title()
    )

    metadata.setdefault(
        "description",
        ""
    )

    metadata.setdefault(
        "category",
        "Image Tools"
    )

    metadata.setdefault(
        "date",
        ""
    )

    metadata.setdefault(
        "author",
        "ImageTools"
    )

    metadata.setdefault(
        "image",
        ""
    )

    return {
        "metadata": metadata,
        "content": html_content
    }


# =========================================================
# Get Articles
# =========================================================

def get_articles(language="en"):

    language_dir = os.path.join(
        ARTICLES_DIR,
        language
    )

    articles_list = []

    # Language folder does not exist
    if not os.path.isdir(language_dir):
        return articles_list

    try:
        filenames = os.listdir(
            language_dir
        )
    except Exception:
        return articles_list

    for filename in filenames:

        # Markdown files only
        if not filename.lower().endswith(".md"):
            continue

        slug = filename[:-3]

        article = load_article(
            language,
            slug
        )

        if article:

            metadata = article["metadata"]

            metadata["url"] = (
                f"/articles/{slug}"
            )

            articles_list.append(
                metadata
            )

    # Newest articles first
    articles_list.sort(
        key=lambda article: article.get(
            "date",
            ""
        ),
        reverse=True
    )

    return articles_list


# =========================================================
# Articles List
# =========================================================

@app.route("/articles")
def articles():

    # Default language
    language = "en"

    articles_list = get_articles(
        language
    )

    return render_template(
        "articles.html",
        articles=articles_list,
        language=language
    )


# =========================================================
# Single Article
# =========================================================

@app.route("/articles/<slug>")
def article(slug):

    # Default language
    language = "en"

    article_data = load_article(
        language,
        slug
    )

    if article_data is None:
        abort(404)

    return render_template(
        "article.html",
        article=article_data["metadata"],
        content=article_data["content"]
    )


# =========================================================
# Image Format Converter
# =========================================================

@app.route(
    "/convert-image",
    methods=["POST"]
)
def convert_image():

    try:

        # Check file
        if "file" not in request.files:
            return "No file selected", 400

        file = request.files["file"]

        # Target format
        target_format = request.form.get(
            "format",
            "png"
        ).lower()

        # Allowed formats
        allowed_formats = {
            "jpg",
            "jpeg",
            "png",
            "webp"
        }

        if target_format not in allowed_formats:
            return "Invalid image format", 400

        # Empty filename
        if file.filename == "":
            return "Empty file", 400

        # Open image
        img = Image.open(
            file.stream
        )

        # -------------------------------------------------
        # Handle transparency when converting to JPG
        # -------------------------------------------------

        if (
            target_format in ("jpg", "jpeg")
            and img.mode in ("RGBA", "LA", "P")
        ):

            background = Image.new(
                "RGB",
                img.size,
                "white"
            )

            if img.mode in ("RGBA", "LA"):

                background.paste(
                    img,
                    mask=img.getchannel("A")
                )

            else:

                background.paste(img)

            img = background

        # -------------------------------------------------
        # Save image
        # -------------------------------------------------

        output = io.BytesIO()

        save_format = (
            "JPEG"
            if target_format in ("jpg", "jpeg")
            else target_format.upper()
        )

        img.save(
            output,
            format=save_format
        )

        output.seek(0)

        # Output extension
        extension = (
            "jpg"
            if target_format == "jpeg"
            else target_format
        )

        filename = (
            f"converted_"
            f"{uuid.uuid4().hex[:8]}."
            f"{extension}"
        )

        # MIME type
        mimetype = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp"
        }[target_format]

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )

    except Exception as e:

        return (
            f"Image conversion error: {str(e)}",
            500
        )


# =========================================================
# Image Compressor
# =========================================================

@app.route(
    "/compress-image",
    methods=["POST"]
)
def compress_image():

    try:

        # Check file
        if "file" not in request.files:
            return "No file selected", 400

        file = request.files["file"]

        # Get quality
        try:
            quality = int(
                request.form.get(
                    "quality",
                    70
                )
            )
        except ValueError:
            quality = 70

        # Limit quality
        quality = max(
            10,
            min(quality, 100)
        )

        # Empty filename
        if file.filename == "":
            return "Empty file", 400

        # Open image
        img = Image.open(
            file.stream
        )

        # -------------------------------------------------
        # Convert to RGB
        # -------------------------------------------------

        if img.mode in ("RGBA", "LA", "P"):

            background = Image.new(
                "RGB",
                img.size,
                "white"
            )

            if img.mode in ("RGBA", "LA"):

                background.paste(
                    img,
                    mask=img.getchannel("A")
                )

            else:

                background.paste(img)

            img = background

        elif img.mode != "RGB":

            img = img.convert("RGB")

        # -------------------------------------------------
        # Compress
        # -------------------------------------------------

        output = io.BytesIO()

        img.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True
        )

        output.seek(0)

        filename = (
            f"compressed_"
            f"{uuid.uuid4().hex[:8]}"
            ".jpg"
        )

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="image/jpeg"
        )

    except Exception as e:

        return (
            f"Image compression error: {str(e)}",
            500
        )


# =========================================================
# 404 Page
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return """
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>404 - Page Not Found</title>

        <style>

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                min-height: 100vh;

                display: flex;
                align-items: center;
                justify-content: center;

                padding: 20px;

                font-family:
                    Arial,
                    sans-serif;

                background: #f6f8fc;

                color: #111827;

                text-align: center;
            }

            .box {
                width: 100%;
                max-width: 500px;

                padding: 50px 30px;

                background: #ffffff;

                border-radius: 20px;

                box-shadow:
                    0 20px 50px
                    rgba(0, 0, 0, 0.08);
            }

            h1 {
                margin: 0 0 10px;

                font-size: 64px;
            }

            p {
                margin-bottom: 25px;

                color: #64748b;
            }

            a {
                color: #635bff;

                text-decoration: none;

                font-weight: bold;
            }

        </style>

    </head>

    <body>

        <div class="box">

            <h1>404</h1>

            <p>
                The page you are looking for
                could not be found.
            </p>

            <a href="/">
                ← Back to ImageTools
            </a>

        </div>

    </body>

    </html>
    """, 404


# =========================================================
# Run Application
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True
    )
