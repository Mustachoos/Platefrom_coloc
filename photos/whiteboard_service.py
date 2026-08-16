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

WIDTH = 1200
HEIGHT = 900  # 4:3


def _blank_board():
    return Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 255))


def _save_board(event, board):
    buffer = io.BytesIO()
    board.convert("RGB").save(buffer, format="PNG")
    if event.whiteboard_image:
        event.whiteboard_image.delete(save=False)
    event.whiteboard_image.save("board.png", ContentFile(buffer.getvalue()), save=True)


def add_layer(event, drawing):
    """Composite one freshly uploaded drawing on top of the current board."""
    if event.whiteboard_image:
        board = Image.open(event.whiteboard_image.path).convert("RGBA")
    else:
        board = _blank_board()
    layer = Image.open(drawing.image.path).convert("RGBA")
    board = Image.alpha_composite(board, layer)
    _save_board(event, board)


def rebuild_board(event):
    """Recompute the board from every surviving drawing, oldest first."""
    board = _blank_board()
    for drawing in event.whiteboard_drawings.order_by("uploaded_at"):
        layer = Image.open(drawing.image.path).convert("RGBA")
        board = Image.alpha_composite(board, layer)
    _save_board(event, board)
