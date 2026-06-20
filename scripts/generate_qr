from pathlib import Path
import sys

import qrcode


def generate_qr(url, output_path="tannaz_qr.png"):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    qr_image = qr.make_image(
        fill_color="#C9A84C",
        back_color="#0D0D1A",
    ).convert("RGB")

    qr_image = qr_image.resize((500, 500))
    qr_image.save(output_path)

    print(f"QR code created: {Path(output_path).resolve()}")
    print(f"URL: {url}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        render_url = sys.argv[1]
    else:
        render_url = input("Render URL: ").strip()

    output = sys.argv[2] if len(sys.argv) > 2 else "tannaz_qr.png"
    generate_qr(render_url, output)
