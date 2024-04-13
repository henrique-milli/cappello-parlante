import io
import json
import os
import subprocess

import boto3
import chess
import chess.pgn
import chess.svg
import requests

import constants
from bot_helpers import send_image
from utils import convert_uci_to_human, translate_color, get_color_to_move


def send_solution(puzzle):
    # Save the SVGs as PNGs
    save_solution_svgs(puzzle)

    # convert solution svgs to pngs
    convert_solution_svgs_to_pngs()

    # Create a GIF from the PNGs
    convert_pngs_to_gif()

    # Get the solution text
    solution_text = convert_uci_to_human(puzzle['puzzle']['solution'])

    # Send the final position as an image to the Telegram group
    send_image(constants.PUZZLE_SOLUTION_GIF_PATH, f"Ecco la soluzione del puzzle di oggi:\n{solution_text}")


def save_solution_svgs(puzzle):
    # Get board
    game = get_game(puzzle)
    board = game.end().board()

    # Get solution
    solution = puzzle['puzzle']['solution']

    # Initialize counter
    i = 0

    # Push the initial position
    save_file(chess.svg.board(board=board), constants.PUZZLE_SOLUTION_SVGS_PATH(i))
    i += 1

    # Push the moves for move in solution:
    for move in solution:
        try:
            board.push_uci(move)
            save_file(chess.svg.board(board=board), constants.PUZZLE_SOLUTION_SVGS_PATH(i))
            i += 1
        except chess.IllegalMoveError:
            print(f"Illegal move: {move}")
            continue


def convert_solution_svgs_to_pngs():
    # for all svgs in the solution directory
    for svg in os.listdir(constants.PUZZLE_SOLUTION_SVGS_DIR):
        # convert them to pngs
        convert(
            os.path.join(constants.PUZZLE_SOLUTION_SVGS_DIR, svg),
            os.path.join(constants.PUZZLE_SOLUTION_PNGS_DIR, svg[:-4] + ".png")
            )


def convert_pngs_to_gif():
    # Get all the PNG images
    images = sorted(
        [os.path.join(constants.PUZZLE_SOLUTION_PNGS_DIR, img) for img in os.listdir(constants.PUZZLE_SOLUTION_PNGS_DIR)
         if img.endswith(".png")]
        )

    # save an empty output file to ensure it exists
    save_file("", constants.PUZZLE_SOLUTION_GIF_PATH)

    # Create a GIF from the images using ImageMagick's convert utility
    result = subprocess.run(
        [constants.CONVERT_EXECUTABLE_PATH, "-delay", constants.GIF_DELAY, "-loop", "0", *images,
         constants.PUZZLE_SOLUTION_GIF_PATH]
        )

    # verify the conversion
    if result.returncode != 0:
        print(f"Conversion failed: {result}")


def send_daily_puzzle(puzzle):
    # Save the puzzle as an image
    save_puzzle_png(puzzle)

    # Send the final position as an image to the Telegram group
    send_image(constants.PUZZLE_INITIAL_PNG_PATH, get_puzzle_caption(puzzle))


def save_puzzle_png(puzzle):
    # Get game
    game = get_game(puzzle)

    # Get final position SVG
    save_starting_position(game)

    # Convert SVG to PNG
    convert(constants.PUZZLE_INITIAL_SVG_PATH, constants.PUZZLE_INITIAL_PNG_PATH)


def save_starting_position(game):
    # Get the initial position of the puzzle
    board = game.end().board()

    # Get the SVG content for the board
    svg_content = chess.svg.board(board=board)

    # Save the SVG content to a file
    save_file(svg_content, constants.PUZZLE_INITIAL_SVG_PATH)


def get_daily_puzzle():
    response = requests.get("https://lichess.org/api/puzzle/daily")
    return response.json()


def get_puzzle(id):
    response = requests.get(f"https://lichess.org/api/puzzle/{id}")
    return response.json()


def get_game(puzzle):
    pgn_text = puzzle['game']['pgn']
    pgn_io = io.StringIO(pgn_text)
    return chess.pgn.read_game(pgn_io)


def convert(input_path, output_path):
    # Convert the paths to absolute paths
    input_path = os.path.abspath(input_path)
    output_path = os.path.abspath(output_path)

    # save an empty output file to ensure it exists
    save_file("", output_path)

    # Create a Lambda client
    lambda_client = boto3.client('lambda', region_name='eu-central-1')

    # Read the SVG data from the input file
    with open(input_path, 'r') as f:
        svg_data = f.read()

    # Define the input parameters that will be passed to the Lambda function
    input_params = {
        "svgData": svg_data,
        "width": constants.PNG_WIDTH,
        "height": constants.PNG_HEIGHT
        }

    # Invoke the Lambda function
    response = lambda_client.invoke(
        FunctionName='svg2png-lambda',  # Replace with the name of your Lambda function
        InvocationType='RequestResponse',
        Payload=json.dumps(input_params)
        )

    # If you expect a response from the Lambda function, you can read it like this:
    response_payload = json.loads(response['Payload'].read().decode('utf-8'))

    # Write the response payload (PNG data) to the output file
    save_file(response_payload, output_path)

    # verify the conversion
    if not os.path.exists(output_path):
        print(f"Conversion failed: {response}")


def save_file(content, path):
    directory = os.path.dirname(path)

    # If the directory does not exist, create it
    if not os.path.exists(directory):
        os.makedirs(directory)

    with open(path, 'w+') as f:
        f.write(content)


def get_puzzle_caption(puzzle):
    players = puzzle['game']['players']
    if players is None:
        return f"Riesci a trovare la mossa migliore per il {translate_color(get_color_to_move(puzzle['game']['pgn']))}?"
    p1 = players[0]
    p2 = players[1]
    return f"""
    Questa partita {puzzle['game']['perf']['name']} è stata giocata da {p1['name']} ({translate_color(p1['color'])} - ELO {p1['rating']}) e {p2['name']} ({translate_color(p2['color'])} - ELO {p2['rating']}).
Riesci a trovare le mosse migliori per il {translate_color(get_color_to_move(puzzle['game']['pgn']))}?
👍Se pensi di averlo risolto, 👎 se non sei sicuro.
La soluzione verrà pubblicata più tardi!
"""
