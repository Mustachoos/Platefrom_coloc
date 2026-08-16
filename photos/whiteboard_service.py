"""Compositing the collective whiteboard.

Each guest draws on a transparent canvas and uploads only their own
strokes as a PNG (WhiteboardDrawing). The visible board is the flatten of
every surviving drawing, oldest first, on top of a blank white canvas.

Adding a new drawing only needs the previous composite plus the one new
layer (cheap). Deleting a drawing requires a full recompute from scratch,
since a flattened PNG can't have a layer subtracted back out of the middle
of the stack.
"""

import io

from django.core.files.base import ContentFile
from PIL import Image

WIDTH = 3600
HEIGHT = 2700  # 4:3, 3x the original 1200x900 for a sharper board


def _blank_board():
    return Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))


def _ensure_size(image):
    # Drawings/boards saved before a resolution change are a different
    # size than the current WIDTH/HEIGHT, and Image.alpha_composite
    # requires both images to match exactly. Resize rather than reject
    # them so existing whiteboard content survives a resolution bump
    # instead of crashing on the next upload or delete.
    if image.size != (WIDTH, HEIGHT):
        image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)
    return image


def _save_board(event, board):
    buffer = io.BytesIO()
    board.convert("RGB").save(buffer, format="PNG")
    if event.whiteboard_image:
        event.whiteboard_image.delete(save=False)
    event.whiteboard_image.save("board.png", ContentFile(buffer.getvalue()), save=True)


def add_layer(event, drawing):
    """Composite one freshly uploaded drawing on top of the current board."""
    if event.whiteboard_image:
        board = _ensure_size(Image.open(event.whiteboard_image.path).convert("RGBA"))
    else:
        board = _blank_board()
    layer = _ensure_size(Image.open(drawing.image.path).convert("RGBA"))
    board = Image.alpha_composite(board, layer)
    _save_board(event, board)


def rebuild_board(event):
    """Recompute the board from every surviving drawing, oldest first."""
    board = _blank_board()
    for drawing in event.whiteboard_drawings.order_by("uploaded_at"):
        layer = _ensure_size(Image.open(drawing.image.path).convert("RGBA"))
        board = Image.alpha_composite(board, layer)
    _save_board(event, board)
