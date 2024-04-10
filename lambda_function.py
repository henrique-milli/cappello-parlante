import json

import boto3
import requests

import constants
from bot_helpers import get_updates, send_message, send_image, kick_chat_member
from puzzle_helpers import (
    get_daily_puzzle, get_puzzle_caption, save_soution_pngs, create_gif_from_pngs, save_puzzle_png,
    )


def lambda_handler(event, context):
    print("Starting the lambda function")
    main()
    return {
        'statusCode': 200, 'body': 'OK'
        }


def main():
    print("Starting the main function")

    # Initialize the DynamoDB table
    session = boto3.Session(
        region_name=constants.AWS_REGION_CP
        )

    table = session.resource('dynamodb').Table('cappello-parlante')

    updates = get_updates()

    run_day_specific_tasks(table, updates)

    run_every_day_tasks(updates, table)


def run_day_specific_tasks(table, updates):

    # Monday
    if constants.TODAY == 0:
        send_meet_poll(table)
        kick_inactive_users(table)
    # Thursday
    if constants.TODAY == 3:
        evaluate_poll(table, updates)


def run_every_day_tasks(updates, table):
    add_new_users_to_table(updates, table)



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
        if poll_results[i].voter_count >= constants.MIN_PLAYERS_FOR_MEETUP:
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


def send_meet_poll(table):
    print("Sending the meet poll")
    try:
        response = requests.post(
            f"{constants.BOT_BASE_URL}/sendPoll", data=json.dumps(
                {
                    "chat_id": constants.CHAT_ID,
                    "question": "Questa settimana quando giochiamo?",
                    "options": json.dumps(constants.PLAY_ALLOWED_DAYS),
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

    # Get the latest polls from the table
    response = table.get_item(
        Key={
            'cp_id': 'latest_polls'
            }
        )

    latest_polls = response['Item']['polls']

    # If the number of stored polls is equal to MAX_LATEST_POLL, delete the oldest poll
    if len(latest_polls) >= constants.LATEST_POLLS_SIZE:
        oldest_poll = latest_polls.pop(0)
        table.delete_item(
            Key={
                'cp_id': oldest_poll['id']
                }
            )

    # Store the poll object in the table
    table.put_item(
        Item={
            'cp_id': poll_id, 'poll': poll
            }
        )

    # Add the new poll to the latest polls
    latest_polls.append(poll)

    # Update the latest polls in the table
    table.put_item(
        Item={
            'cp_id': 'latest_polls', 'polls': latest_polls
            }
        )


# Kick users who haven't been seen in the last 1000 updates
def kick_inactive_users(table):
    print("Kicking inactive users")

    # get the voters from the latest polls
    response = table.get_item(
        Key={
            'cp_id': 'latest_polls'
            }
        )

    latest_polls = response['Item']['polls']

    voters = []

    for poll in latest_polls:
        voters += poll['voters']

    # Get the users from the table

    response = table.get_item(
        Key={
            'cp_id': 'users'
            }
        )

    users = response['Item']['users']

    # Kick users who haven't voted in the latest polls
    for user in users:
        if user not in voters:
            kick_chat_member(user['id'])
            users.remove(user)

    # Delete the users in the table
    table.put_item(
        Item={
            'cp_id': 'users', 'users': users
            }
        )


def add_new_users_to_table(updates, table):
    print("Adding new users to the table")

    # Get the users from the table
    response = table.get_item(
        Key={
            'cp_id': 'users'
            }
        )

    users = response['Item']['users']

    # Add new users to the table
    for update in updates:
        if update['message']['from']['id'] not in users:
            users.append(update['message']['from']['id'])

    # Update the users in the table
    table.put_item(
        Item={
            'cp_id': 'users', 'users': users
            }
        )


def send_daily_puzzle():
    # Fetch the daily puzzle
    puzzle = get_daily_puzzle()

    save_puzzle_png(puzzle)

    # Send the final position as an image to the Telegram group
    send_image('temp.png', get_puzzle_caption(puzzle))


def send_solution_gif():
    # Fetch the daily puzzle
    puzzle = get_daily_puzzle()

    # Save the SVGs as PNGs
    save_soution_pngs(puzzle)

    # Create a GIF from the PNGs
    create_gif_from_pngs('temp_', 'solution.gif', duration=3)

    # Send the GIF to the Telegram group
    send_image('solution.gif', "Ecco la soluzione del puzzle di oggi!")
