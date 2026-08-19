from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
from pypdf import PdfWriter, PdfReader
import pikepdf
import os
import io
import uuid

app = Flask(__name__)
app.secret_key = "super-secret-key-12345"

UPLOAD_FOLDER = "/tmp"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp", "bmp"}
ALLOWED_PDF = {"pdf"}

def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/convert-image", methods=["POST"])
def convert_image():
    try:
        if "file" not in request.files:
            return "فایلی انتخاب نشده", 400

        file = request.files["file"]
        target_format = request.form.get("format", "png").lower()

        if file.filename == "":
            return "فایل خالی است", 400

        img = Image.open(file.stream)

        # تبدیل حالت رنگ اگر لازم باشد
        if target_format in ["jpg", "jpeg"] and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        output = io.BytesIO()
        save_format = "JPEG" if target_format in ["jpg", "jpeg"] else target_format.upper()
        img.save(output, format=save_format)
        output.seek(0)

        filename = f"converted_{uuid.uuid4().hex[:8]}.{target_format}"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype=f"image/{target_format}"
        )
    except Exception as e:
        return f"خطا در تبدیل عکس: {str(e)}", 500

@app.route("/compress-image", methods=["POST"])
def compress_image():
    try:
        if "file" not in request.files:
            return "فایلی انتخاب نشده", 400

        file = request.files["file"]
        quality = int(request.form.get("quality", 70))

        if file.filename == "":
            return "فایل خالی است", 400

        img = Image.open(file.stream)
        output = io.BytesIO()

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)

        filename = f"compressed_{uuid.uuid4().hex[:8]}.jpg"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="image/jpeg"
        )
    except Exception as e:
        return f"خطا در فشرده‌سازی عکس: {str(e)}", 500

@app.route("/merge-pdf", methods=["POST"])
def merge_pdf():
    try:
        files = request.files.getlist("files")
        if not files or files[0].filename == "":
            return "حداقل یک فایل PDF انتخاب کنید", 400

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
        return send_file(output, as_attachment=True, download_name=filename, mimetype="application/pdf")
    except Exception as e:
        return f"خطا در ادغام PDF: {str(e)}", 500

@app.route("/compress-pdf", methods=["POST"])
def compress_pdf():
    try:
        if "file" not in request.files:
            return "فایلی انتخاب نشده", 400

        file = request.files["file"]
        if file.filename == "" or not allowed_file(file.filename, ALLOWED_PDF):
            return "فقط فایل PDF مجاز است", 400

        input_path = os.path.join(UPLOAD_FOLDER, f"in_{uuid.uuid4().hex}.pdf")
        output_path = os.path.join(UPLOAD_FOLDER, f"out_{uuid.uuid4().hex}.pdf")

        file.save(input_path)

        with pikepdf.open(input_path) as pdf:
            pdf.save(output_path, compress_streams=True)

        return send_file(output_path, as_attachment=True, download_name="compressed.pdf", mimetype="application/pdf")
    except Exception as e:
        return f"خطا در فشرده‌سازی PDF: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)
