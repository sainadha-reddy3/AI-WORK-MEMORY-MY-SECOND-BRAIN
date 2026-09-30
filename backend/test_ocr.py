import io

from PIL import Image, ImageDraw, ImageFont

from app.db.session import SessionLocal
from app.services.attachment_service import list_attachments, read_attachment
from app.services.extraction import ocr_image

# 1. A fake K9s-style screenshot: light text on a dark background.
img = Image.new("RGB", (900, 160), (18, 18, 28))
draw = ImageDraw.Draw(img)
font = ImageFont.load_default(size=28)
draw.text((20, 20), "NAME             READY   STATUS", fill=(220, 220, 220), font=font)
draw.text((20, 70), "api-7d9f8b-x2k   0/1     CrashLoopBackOff", fill=(220, 220, 220), font=font)
buf = io.BytesIO()
img.save(buf, format="PNG")

r = ocr_image(buf.getvalue())
print(f"SYNTHETIC — confidence {r.confidence}, words {r.words}, uncertain {r.uncertain_words}")
print(r.text)

# 2. Your most recent real screenshot, if you've uploaded one.
db = SessionLocal()
shots = list_attachments(db, kind="screenshot", limit=1)
if shots:
    r = ocr_image(read_attachment(shots[0]))
    print(f"\nREAL ({shots[0].original_filename}) — confidence {r.confidence}, "
          f"words {r.words}, uncertain {r.uncertain_words}")
    print((r.text or "(no text found)")[:600])
else:
    print("\nNo screenshots uploaded yet — paste one in the app, then re-run.")
db.close()