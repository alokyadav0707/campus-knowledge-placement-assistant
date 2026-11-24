"""Create a clearly fictional PDF with normal text and a ruled table."""

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def create_demo_pdf(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 70), "SYNTHETIC DEMO - NOT OFFICIAL DATA", fontsize=12)
        page.insert_text((50, 105), "Demo college placement registration ends on 15 August.")

        page = document.new_page()
        page.insert_text((50, 65), "SYNTHETIC PLACEMENT TABLE - NOT OFFICIAL DATA", fontsize=12)
        headers = ["Department", "Offers Accepted", "Median CTC"]
        rows = [["Computer Science", "42", "14.5 LPA"], ["Mechanical", "27", "8.0 LPA"]]
        x_positions = [50, 220, 380, 540]
        y_positions = [90, 125, 160, 195]
        for x in x_positions:
            page.draw_line((x, y_positions[0]), (x, y_positions[-1]), color=(0, 0, 0))
        for y in y_positions:
            page.draw_line((x_positions[0], y), (x_positions[-1], y), color=(0, 0, 0))
        for row_number, values in enumerate([headers] + rows):
            for column_number, value in enumerate(values):
                page.insert_text((x_positions[column_number] + 7,
                                  y_positions[row_number] + 23), value, fontsize=10)
        document.save(destination)
    print(f"Created synthetic demo PDF: {destination}")


if __name__ == "__main__":
    create_demo_pdf(ROOT / "data/raw/demo_synthetic.pdf")
