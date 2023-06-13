from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont


def text_to_image(
        items: List[List[str]],
        font_filepath: str,
        font_size: int,
        color: Tuple[int, int, int],
        background: Tuple[int, int, int],
) -> Image:
    countries = max(map(len, items))
    font = ImageFont.truetype(font_filepath, size=font_size)

    max_y = 0
    max_x = 0
    offset = 10
    offsets = list()
    lines_to_draw = list()
    for idx in range(countries):
        lines = [line[idx] or '' if len(line) > idx else '' for line in items]

        offsets.append(offset)
        lines_to_draw.append(lines)

        x, y = font.getsize_multiline("\n".join(lines))
        offset += x
        offset += 20
        max_x = max(max_x, offset)
        max_y = max(max_y, y)

    img = Image.new("RGB", (max_x, max_y + 30), color=background)

    draw = ImageDraw.Draw(img)
    for offset, lines in zip(offsets, lines_to_draw):
        draw_point = (offset, 0)
        draw.multiline_text(draw_point, "\n".join(lines), font=font, fill=color, align="left")

    return img