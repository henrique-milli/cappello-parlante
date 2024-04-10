import io
import os

import chess
import chess.pgn
import chess.svg
import imageio
import requests
from wand.image import Image as WandImage

from bot_helpers import send_image


def save_puzzle_png(puzzle):
    # Get the final position of the game
    game = get_game(puzzle)

    final_position_svg = get_final_position_svg(game)

    # Convert SVG to PNG using Wand
    with WandImage(blob=final_position_svg.encode(), format='svg') as img:
        png_image = img.make_blob('png')

    # Save PNG to a temporary file
    with open('temp.png', 'wb') as temp_file:
        temp_file.write(png_image)


def get_final_position_svg(game):
    board = game.end().board()
    return chess.svg.board(board=board)


def get_puzzle_caption(puzzle):
    players = puzzle['game']['players']
    if players is None:
        return f"Riesci a trovare la mossa migliore per il {get_color_name(get_color_to_move(puzzle['game']['pgn']))}?"
    p1 = players[0]
    p2 = players[1]
    return f"""
    Questa partita {puzzle['game']['perf']['name']} è stata giocata da {p1['name']} ({get_color_name(p1['color'])} - {p1['rating']}) e {p2['name']} ({get_color_name(p2['color'])} - {p2['rating']}).
    Riesci a trovare le mosse migliore per il {get_color_name(get_color_to_move(puzzle['game']['pgn']))}?
    Non fare spoiler! La soluzione verrà pubblicata più tardi.
"""


def save_soution_pngs(puzzle):
    svgs = get_solution_svgs(puzzle)

    for i, svg in enumerate(svgs):
        with WandImage(blob=svg.encode(), format='svg') as img:
            png_image = img.make_blob('png')

        with open(f'temp_{i}.png', 'wb') as temp_file:
            temp_file.write(png_image)


def get_solution_svgs(puzzle):
    game = get_game(puzzle)

    solution = puzzle['puzzle']['solution']

    svgs = []
    board = game.end().board()
    for move in solution:
        try:
            board.push_uci(move)
            svgs.append(chess.svg.board(board=board))
        except chess.IllegalMoveError:
            print(f"Illegal move: {move}")
            continue

    return svgs


def create_gif_from_pngs(png_prefix, gif_name, duration):
    # Get all the PNG images
    images = sorted([img for img in os.listdir() if img.startswith(png_prefix) and img.endswith(".png")])

    # Read the images into a list
    frames = [imageio.imread(img) for img in images]

    # Create a GIF from the images
    imageio.mimsave(gif_name, frames, 'GIF', duration=duration)


def get_daily_puzzle():
    response = requests.get("https://lichess.org/api/puzzle/daily")
    return response.json()


def get_game(puzzle):
    pgn_text = puzzle['game']['pgn']
    pgn_io = io.StringIO(pgn_text)
    return chess.pgn.read_game(pgn_io)


def get_color_name(string):
    if string == "white":
        return "bianco"
    else:
        return "nero"


def get_color_to_move(pgn):
    return "white" if is_white_to_move(pgn) else "black"


def is_white_to_move(pgn):
    return len(pgn.split(' ')) % 2 == 0


def send_daily_puzzle(puzzle):
    # Save the puzzle as an image
    save_puzzle_png(puzzle)

    # Send the final position as an image to the Telegram group
    send_image('temp.png', get_puzzle_caption(puzzle))


def send_solution_gif(puzzle):
    # Save the SVGs as PNGs
    save_soution_pngs(puzzle)

    # Create a GIF from the PNGs
    create_gif_from_pngs('temp_', 'solution.gif', duration=3)

    # Send the GIF to the Telegram group
    send_image('solution.gif', "Ecco la soluzione del puzzle di oggi!")
