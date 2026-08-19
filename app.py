from flask import Flask, render_template, request, send_file, abort
from PIL import Image
import io
import uuid
import os
import markdown

app = Flask(__name__)


# =========================================================
# صفحه اصلی
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# سیستم مقالات
# =========================================================

def load_article(language, slug):
    """
    خواندن مقاله از فایل Markdown
    مسیر:
    articles/{language}/{slug}.md
    """

    article_path = os.path.join(
        "articles",
        language,
        f"{slug}.md"
    )

    # اگر مقاله وجود نداشت
    if not os.path.exists(article_path):
        return None

    # خواندن فایل
    with open(article_path, "r", encoding="utf-8") as file:
        content = file.read()

    metadata = {}

    # -----------------------------------------------------
    # خواندن Front Matter
    # -----------------------------------------------------

    if content.startswith("---"):

        parts = content.split("---", 2)

        if len(parts) >= 3:

            front_matter = parts[1].strip()
            markdown_content = parts[2].strip()

            for line in front_matter.splitlines():

                if ":" in line:

                    key, value = line.split(":", 1)

                    key = key.strip()
                    value = value.strip()

                    # حذف کوتیشن‌ها
                    value = value.strip('"').strip("'")

                    metadata[key] = value

        else:
            markdown_content = content

    else:
        markdown_content = content

    # -----------------------------------------------------
    # تبدیل Markdown به HTML
    # -----------------------------------------------------

    html_content = markdown.markdown(
        markdown_content,
        extensions=[
            "extra",
            "toc"
        ]
    )

    # اطلاعات اضافی
    metadata["slug"] = slug
    metadata["language"] = language

    return {
        "metadata": metadata,
        "content": html_content
    }


# =========================================================
# لیست مقالات
# =========================================================

@app.route("/articles")
def articles():

    language = "en"

    articles_path = os.path.join(
        "articles",
        language
    )

    articles_list = []

    # اگر پوشه مقالات وجود داشته باشد
    if os.path.exists(articles_path):

        for filename in os.listdir(articles_path):

            # فقط فایل‌های Markdown
            if not filename.endswith(".md"):
                continue

            # حذف .md از نام فایل
            slug = filename[:-3]

            article = load_article(
                language,
                slug
            )

            if article:
                articles_list.append(
                    article["metadata"]
                )

    # مرتب‌سازی بر اساس تاریخ
    articles_list.sort(
        key=lambda x: x.get("date", ""),
        reverse=True
    )

    return render_template(
        "articles.html",
        articles=articles_list
    )


# =========================================================
# نمایش یک مقاله
# =========================================================

@app.route("/articles/<slug>")
def article(slug):

    language = "en"

    article = load_article(
        language,
        slug
    )

    # اگر مقاله پیدا نشد
    if article is None:
        abort(404)

    return render_template(
        "article.html",
        article=article["metadata"],
        content=article["content"]
    )


# =========================================================
# تبدیل فرمت عکس
# =========================================================

@app.route("/convert-image", methods=["POST"])
def convert_image():

    try:

        if "file" not in request.files:
            return "فایلی انتخاب نشده", 400

        file = request.files["file"]

        target_format = request.form.get(
            "format",
            "png"
        ).lower()

        if file.filename == "":
            return "فایل خالی است", 400

        img = Image.open(file.stream)

        # تبدیل تصاویر دارای شفافیت برای JPG
        if target_format in ["jpg", "jpeg"] and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        output = io.BytesIO()

        save_format = (
            "JPEG"
            if target_format in ["jpg", "jpeg"]
            else target_format.upper()
        )

        img.save(
            output,
            format=save_format
        )

        output.seek(0)

        filename = (
            f"converted_"
            f"{uuid.uuid4().hex[:8]}."
            f"{target_format}"
        )

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype=f"image/{target_format}"
        )

    except Exception as e:

        return (
            f"خطا در تبدیل عکس: {str(e)}",
            500
        )


# =========================================================
# فشرده‌سازی عکس
# =========================================================

@app.route("/compress-image", methods=["POST"])
def compress_image():

    try:

        if "file" not in request.files:
            return "فایلی انتخاب نشده", 400

        file = request.files["file"]

        quality = int(
            request.form.get(
                "quality",
                70
            )
        )

        # جلوگیری از کیفیت خارج از محدوده
        quality = max(
            10,
            min(quality, 100)
        )

        if file.filename == "":
            return "فایل خالی است", 400

        img = Image.open(file.stream)

        output = io.BytesIO()

        # تبدیل برای JPEG
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True
        )

        output.seek(0)

        filename = (
            f"compressed_"
            f"{uuid.uuid4().hex[:8]}.jpg"
        )

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="image/jpeg"
        )

    except Exception as e:

        return (
            f"خطا در فشرده‌سازی عکس: {str(e)}",
            500
        )


# =========================================================
# اجرای برنامه
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)
