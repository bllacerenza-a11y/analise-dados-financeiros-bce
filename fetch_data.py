"""Download the fixed 2025 ECB reference-rate CSV snapshot."""

from pathlib import Path
from urllib.request import Request, urlopen

URL = ("https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
       "?startPeriod=2025-01-01&endPeriod=2025-12-31&format=csvdata")
TARGET = Path(__file__).resolve().parent / "ecb_usd_eur_2025.csv"


def main() -> None:
    with urlopen(Request(URL, headers={"User-Agent": "data-portfolio/1.0"}), timeout=30) as response:
        content = response.read()
    if not content.startswith(b"KEY,FREQ,"):
        raise ValueError("Resposta inesperada da API do BCE")
    TARGET.write_bytes(content)
    print(f"Salvo: {TARGET} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
