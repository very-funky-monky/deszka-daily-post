"""Urbanist (OFL) letöltése build-időben: változó font -> statikus példányok.
Források sorban: Google Fonts CSS, google/fonts repó, coreyhu/Urbanist. Hiba esetén
a renderer DejaVu Sans-ra esik vissza (és figyelmeztet)."""
import io, os, re, sys, urllib.request

D = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def sources():
    gf = "https://raw.githubusercontent.com/google/fonts/main/ofl/urbanist/"
    yield "google/fonts", gf + "Urbanist%5Bwght%5D.ttf", gf + "Urbanist-Italic%5Bwght%5D.ttf"
    cu = "https://raw.githubusercontent.com/coreyhu/Urbanist/main/fonts/variable/"
    yield "coreyhu", cu + "Urbanist%5Bwght%5D.ttf", cu + "Urbanist-Italic%5Bwght%5D.ttf"


def instance(data, wght, out):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    f = TTFont(io.BytesIO(data))
    if "fvar" in f:
        f = instantiateVariableFont(f, {"wght": wght}, inplace=False)
    f.save(out)
    print(f"  OK {os.path.basename(out)} ({os.path.getsize(out)} B)")


def main():
    for name, up, ip in sources():
        try:
            print("Forrás:", name)
            up_d, ip_d = get(up), get(ip)
            instance(up_d, 400, os.path.join(D, "Urbanist-Regular.ttf"))
            instance(up_d, 500, os.path.join(D, "Urbanist-Medium.ttf"))
            instance(up_d, 700, os.path.join(D, "Urbanist-Bold.ttf"))
            instance(ip_d, 400, os.path.join(D, "Urbanist-Italic.ttf"))
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"  HIBA ({name}): {e}", file=sys.stderr)
    print("Urbanist nem tölthető le -> DejaVu tartalék.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
