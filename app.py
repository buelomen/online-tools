from flask import Flask, render_template, request, send_file
from PIL import Image
import io
import uuid
import markdown

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(debug=True)
