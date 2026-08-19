from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
from pypdf import PdfWriter, PdfReader
import pikepdf
import os
import io
import uuid

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # حداکثر ۱۶ مگابایت

ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp"}
ALLOWED_PDF = {"pdf"}

def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

@app.route("/")
def index():
    return render_template("index.html")

# ---------------- تبدیل فرمت عکس ----------------
@app.route("/convert-image", methods=["POST"])
def convert_image():
    if "file" not in request.files:
        flash("فایلی انتخاب نشده")
        return redirect(url_for("index"))
    
    file = request.files["file"]
    target_format = request.form.get("format", "png").lower()

    if file.filename == "" or not allowed_file(file.filename, ALLOWED_IMAGE):
        flash("فرمت فایل پشتیبانی نمی‌شود")
        return redirect(url_for("index"))

    try:
        img = Image.open(file.stream)
        if target_format == "jpg" or target_format == "jpeg":
            img = img.convert("RGB")
        
        output = io.BytesIO()
        img.save(output, format=target_format.upper())
        output.seek(0)

        filename = f"converted_{uuid.uuid4().hex[:8]}.{target_format}"
        return send_file(output, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f"خطا در تبدیل: {str(e)}")
        return redirect(url_for("index"))

# ---------------- فشرده‌سازی عکس ----------------
@app.route("/compress-image", methods=["POST"])
def compress_image():
    if "file" not in request.files:
        flash("فایلی انتخاب نشده")
        return redirect(url_for("index"))

    file = request.files["file"]
    quality = int(request.form.get("quality", 70))

    if file.filename == "" or not allowed_file(file.filename, ALLOWED_IMAGE):
        flash("فرمت فایل پشتیبانی نمی‌شود")
        return redirect(url_for("index"))

    try:
        img = Image.open(file.stream)
        output = io.BytesIO()
        
        if img.format == "PNG":
            img.save(output, format="PNG", optimize=True)
        else:
            img = img.convert("RGB")
            img.save(output, format="JPEG", quality=quality, optimize=True)
        
        output.seek(0)
        filename = f"compressed_{uuid.uuid4().hex[:8]}.jpg"
        return send_file(output, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f"خطا در فشرده‌سازی: {str(e)}")
        return redirect(url_for("index"))

# ---------------- ادغام PDF ----------------
@app.route("/merge-pdf", methods=["POST"])
def merge_pdf():
    files = request.files.getlist("files")
    if not files or files[0].filename == "":
        flash("حداقل دو فایل PDF انتخاب کنید")
        return redirect(url_for("index"))

    try:
        writer = PdfWriter()
        for file in files:
            if allowed_file(file.filename, ALLOWED_PDF):
                reader = PdfReader(file.stream)
                for page in reader.pages:
                    writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        filename = f"merged_{uuid.uuid4().hex[:8]}.pdf"
        return send_file(output, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f"خطا در ادغام: {str(e)}")
        return redirect(url_for("index"))

# ---------------- فشرده‌سازی PDF ----------------
@app.route("/compress-pdf", methods=["POST"])
def compress_pdf():
    if "file" not in request.files:
        flash("فایلی انتخاب نشده")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename, ALLOWED_PDF):
        flash("فقط فایل PDF مجاز است")
        return redirect(url_for("index"))

    try:
        # ذخیره موقت
        temp_input = os.path.join(app.config["UPLOAD_FOLDER"], f"temp_{uuid.uuid4().hex}.pdf")
        file.save(temp_input)

        temp_output = os.path.join(app.config["UPLOAD_FOLDER"], f"compressed_{uuid.uuid4().hex}.pdf")

        with pikepdf.open(temp_input) as pdf:
            pdf.save(temp_output, compress_streams=True)

        return send_file(temp_output, as_attachment=True, download_name="compressed.pdf")
    except Exception as e:
        flash(f"خطا در فشرده‌سازی PDF: {str(e)}")
        return redirect(url_for("index"))
    finally:
        # پاک کردن فایل‌های موقت
        for f in [temp_input, temp_output]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    app.run(debug=True)
