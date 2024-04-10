import datetime
import io
import json
import os
from typing import List, Dict, Any

import boto3
import chess
import chess.pgn
import imageio
import requests
from wand.image import Image as WandImage

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PLAY_ALLOWED_DAYS = os.getenv("PLAY_ALLOWED_DAYS").split(',')
MIN_PLAYERS_FOR_MEETUP = int(os.getenv("MIN_PLAYERS_FOR_MEETUP"))
LATEST_POLLS_SIZE = int(os.getenv("LATEST_POLLS_SIZE"))
AWS_REGION_CP = os.getenv("AWS_REGION_CP")
BOT_BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def lambda_handler(event, context):
    print("Starting the lambda function")
    main()
    return {
        'statusCode': 200, 'body': 'OK'
        }


def main():
    print("Starting the main function")

    try:
        # Initialize the DynamoDB client
        session = boto3.Session(
            region_name=AWS_REGION_CP
            )
        # Now you can use this session to create service clients or resources
        dynamodb = session.resource('dynamodb')

        # Get a reference to the 'cappello-parlante' table
        table = dynamodb.Table('cappello-parlante')
    except Exception as e:
        print(f"Failed while initializing db {e}")
        return

    try:
        # Get the updates
        updates = get_updates()
    except Exception as e:
        print(f"Failed while getting updates {e}")
        return

    try:
        # Add new users to the table
        add_new_users_to_table(updates, table)
    except Exception as e:
        print(f"Failed while adding new users to the table {e}")
        return

    today = datetime.datetime.today().weekday()

    try:
        # Evaluate the latest poll if it's thursday
        if today == 3:
            evaluate_poll(table, updates)
    except Exception as e:
        print(f"Failed while evaluating the latest poll {e}")
        return

    try:
        # Send a new poll if it's monday
        if today == 0:
            send_meet_poll(table)
            kick_inactive_users(table)
    except Exception as e:
        print(f"Failed while sending the meet poll {e}")
        return


# Evaluate the latest poll
def evaluate_poll(table, updates):
    print("Evaluating the latest poll")
    # Get the latest polls from the table
    response = table.get_item(
        Key={
            'cp_id': 'latest_polls'
            }
        )

    latest_polls = response['Item']['polls']

    # Get the ID of the latest poll
    latest_poll_id = latest_polls[-1]['id']

    # Find the latest poll in the updates
    for update in reversed(updates):
        if update['poll'] and update['poll']['id'] == latest_poll_id:
            latest_poll = update.poll
            break
    else:
        return  # No poll found in the updates

    # Get the poll results
    poll_results = latest_poll.results

    # Get the poll options
    poll_options = latest_poll.options

    # send a message with the selected options
    for i, option in enumerate(poll_options):
        if poll_results[i].voter_count >= MIN_PLAYERS_FOR_MEETUP:
            send_message(
                text=f"Questa settimana si gioca il '{option}' con {poll_results[i].voter_count} amici."
                )

    # Get the poll object from the table
    response = table.get_item(
        Key={
            'cp_id': latest_poll_id
            }
        )
    poll = response['Item']['poll']

    # Update the voters list in the poll object
    for result in poll_results:
        for user in result.voters:
            if user.id not in poll['voters']:
                poll['voters'].append(user.id)

    # Store the updated poll object in the table
    table.put_item(
        Item={
            'cp_id': latest_poll_id, 'poll': poll
            }
        )


# Poll asking users to vote which days they want to meet up
def send_meet_poll(table):
    print("Sending the meet poll")
    try:
        response = requests.post(
            f"{BOT_BASE_URL}/sendPoll", data=json.dumps(
                {
                    "chat_id": CHAT_ID,
                    "question": "Questa settimana quando giochiamo?",
                    "options": json.dumps(PLAY_ALLOWED_DAYS),
                    "is_anonymous": False,
                    "allows_multiple_answers": True
                    }
                ), headers={'Content-Type': 'application/json'}
            )
        pool_message = response.json()
    except Exception as e:
        print(f"Failed while sending the meet poll {e}")
        return

    # Get the poll ID
    poll_id = pool_message.poll.id

    # Create a poll object with id and an empty list of voters
    poll = {
        'id': poll_id, 'voters': []
        }
    try:
        # Get the latest polls from the table
        response = table.get_item(
            Key={
                'cp_id': 'latest_polls'
                }
            )
    except Exception as e:
        print(f"Failed while getting latest polls from the table {e}")
        return

    latest_polls = response['Item']['polls']

    # If the number of stored polls is equal to MAX_LATEST_POLL, delete the oldest poll
    if len(latest_polls) >= LATEST_POLLS_SIZE:
        oldest_poll = latest_polls.pop(0)
        table.delete_item(
            Key={
                'cp_id': oldest_poll['id']
                }
            )
    try:
        # Store the poll object in the table
        table.put_item(
            Item={
                'cp_id': poll_id, 'poll': poll
                }
            )
    except Exception as e:
        print(f"Failed while storing the poll object in the table {e}")
        return

    # Add the new poll to the latest polls
    latest_polls.append(poll)
    try:
        # Update the latest polls in the table
        table.put_item(
            Item={
                'cp_id': 'latest_polls', 'polls': latest_polls
                }
            )
    except Exception as e:
        print(f"Failed while updating latest polls in the table {e}")
        return


# Kick users who haven't been seen in the last 1000 updates
def kick_inactive_users(table):
    print("Kicking inactive users")

    try:
        # get the voters from the latest polls
        response = table.get_item(
            Key={
                'cp_id': 'latest_polls'
                }
            )
    except Exception as e:
        print(f"Failed while getting latest polls from the table {e}")
        return

    latest_polls = response['Item']['polls']

    voters = []

    for poll in latest_polls:
        voters += poll['voters']

    # Get the users from the table
    try:
        response = table.get_item(
            Key={
                'cp_id': 'users'
                }
            )
    except Exception as e:
        print(f"Failed while getting users from the table {e}")
        return

    users = response['Item']['users']

    # Kick users who haven't voted in the latest polls
    for user in users:
        if user not in voters:
            kick_chat_member(user['id'])
            users.remove(user)
    try:
        # Delete the users in the table
        table.put_item(
            Item={
                'cp_id': 'users', 'users': users
                }
            )
    except Exception as e:
        print(f"Failed while updating users in the table {e}")
        return


def add_new_users_to_table(updates: List[Dict[str, Any]], table: Any) -> None:
    print("Adding new users to the table")
    try:
        # Get the users from the table
        response = table.get_item(
            Key={
                'cp_id': 'users'
                }
            )
    except Exception as e:
        print(f"Failed while getting users from the table {e}")
        return

    users = response['Item']['users']

    # Add new users to the table
    for update in updates:
        if update['message']['from']['id'] not in users:
            users.append(update['message']['from']['id'])
    try:
        # Update the users in the table
        table.put_item(
            Item={
                'cp_id': 'users', 'users': users
                }
            )
    except Exception as e:
        print(f"Failed while updating users in the table {e}")
        return


def get_updates() -> List[Dict[str, Any]]:
    print("Getting updates")
    try:
        response = requests.get(
            f"{BOT_BASE_URL}/getUpdates", params={'offset': -1}
            )
        updates = response.json()['result']
    except Exception as e:
        print(f"Failed while getting updates {e}")
        return []

    return updates


def send_message(text):
    print("Sending message")
    try:
        response = requests.post(
            f"{BOT_BASE_URL}/sendMessage", data=json.dumps(
                {
                    "chat_id": CHAT_ID, "text": text
                    }
                ), headers={'Content-Type': 'application/json'}
            )
    except Exception as e:
        print(f"Failed while sending message {e}")
        return


def kick_chat_member(user_id):
    print("Kicking chat member")
    try:
        response = requests.post(
            f"{BOT_BASE_URL}/kickChatMember", data=json.dumps(
                {
                    "chat_id": CHAT_ID, "user_id": user_id
                    }
                ), headers={'Content-Type': 'application/json'}
            )
    except Exception as e:
        print(f"Failed while kicking chat member {e}")
        return


def get_daily_puzzle():
    response = requests.get("https://lichess.org/api/puzzle/daily")
    return response.json()


def get_game(puzzle):
    pgn_text = puzzle['game']['pgn']
    pgn_io = io.StringIO(pgn_text)
    return chess.pgn.read_game(pgn_io)


def get_final_position(game):
    board = game.end().board()
    return chess.svg.board(board=board)


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


def save_soution_pngs(svgs):
    for i, svg in enumerate(svgs):
        with WandImage(blob=svg.encode(), format='svg') as img:
            png_image = img.make_blob('png')

        with open(f'temp_{i}.png', 'wb') as temp_file:
            temp_file.write(png_image)


def create_gif_from_pngs(png_prefix, gif_name, duration):
    # Get all the PNG images
    images = sorted([img for img in os.listdir() if img.startswith(png_prefix) and img.endswith(".png")])

    # Read the images into a list
    frames = [imageio.imread(img) for img in images]

    # Create a GIF from the images
    imageio.mimsave(gif_name, frames, 'GIF', duration=duration)


def send_daily_puzzle():
    # Fetch the daily puzzle
    puzzle = get_daily_puzzle()

    # Get the final position of the game
    game = get_game(puzzle)
    final_position_svg = get_final_position(game)

    # Convert SVG to PNG using Wand
    with WandImage(blob=final_position_svg.encode(), format='svg') as img:
        png_image = img.make_blob('png')

    # Save PNG to a temporary file
    with open('temp.png', 'wb') as temp_file:
        temp_file.write(png_image)

    # Send the final position as an image to the Telegram group
    send_image('temp.png', get_puzzle_caption(puzzle))


def send_solution_gif():
    # Fetch the daily puzzle
    puzzle = get_daily_puzzle()

    # Get the solution SVGs
    svgs = get_solution_svgs(puzzle)

    # Save the SVGs as PNGs
    save_soution_pngs(svgs)

    # Create a GIF from the PNGs
    create_gif_from_pngs('temp_', 'solution.gif', duration=3)

    # Send the GIF to the Telegram group
    send_image('solution.gif', "Ecco la soluzione del puzzle di oggi!")


def send_image(image_path, caption):
    with open(image_path, 'rb') as image_file:
        files = {'photo': image_file}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        response = requests.post(f"{BOT_BASE_URL}/sendPhoto", files=files, data=data)
        return response.json()


def get_puzzle_caption(puzzle):
    if puzzle['players'] is None:
        return f"Riesci a trovare la mossa migliore per il {get_color_name(get_color_to_move(puzzle['game']['pgn']))}?"
    p1 = puzzle['players'][0]
    p2 = puzzle['players'][1]
    return f"""
    Questa partita {puzzle['game']['perf']['name']} è stata giocata da {p1['name']} ({get_color_name(p1['color'])} - {p1['rating']}) e {p2['name']} ({get_color_name(p2['color'])} - {p2['rating']}).
    Riesci a trovare la moss migliore per il {get_color_name()}?
"""


def is_white_to_move(pgn):
    return len(pgn.split(' ')) % 2 == 0


def get_color_to_move(pgn):
    return "white" if is_white_to_move(pgn) else "black"


def get_color_name(string):
    if string == "white":
        return "bianco"
    else:
        return "nero"
