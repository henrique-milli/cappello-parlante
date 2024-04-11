import json
from datetime import datetime

import boto3
import requests

import constants
from bot_helpers import get_updates, send_message, kick_chat_member, handle_updates
from puzzle_helpers import (
    get_daily_puzzle, send_daily_puzzle, send_solution,
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

    handle_updates(updates, table)

    run_day_specific_tasks(table, updates)

    run_routine(updates, table)


def run_day_specific_tasks(table, updates):
    print("Running day specific tasks")
    # return if already done today
    if not is_first_run_today(table):
        print("Already done today")
        return

    # Monday
    if constants.TODAY == 0:
        send_meet_poll(table)
        kick_inactive_users(table)
    # Thursday
    if constants.TODAY == 3:
        evaluate_poll(table, updates)


def run_routine(updates, table):
    print("Running the routine")
    puzzle_routine(table)


def evaluate_poll(table, updates):
    print("Evaluating the poll")

    response = table.get_item(
        Key={
            'cp_id': 'latest_poll'
            }
        )

    latest_poll = response['Item']['polls']

    count_dict = {}

    for i in latest_poll['options_ids']:
        if i in count_dict:
            count_dict[i] += 1
        else:
            count_dict[i] = 1

    for opt, count in count_dict.items():
        if count >= constants.MIN_PLAYERS_FOR_MEETUP:
            send_message(
                f"Questa settimana giochiamo {constants.PLAY_ALLOWED_DAYS[opt]}.\n(Le mie scuse devo tradurre questo codice, Henrique)"
                )
            break


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
            'cp_id': 'latest_poll'
            }
        )

    latest_poll = response['Item']['polls']

    # If the number of stored polls is equal to MAX_LATEST_POLL, delete the oldest poll
    if len(latest_poll) >= constants.LATEST_POLLS_SIZE:
        oldest_poll = latest_poll.pop(0)
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
    latest_poll.append(poll)

    # Update the latest polls in the table
    table.put_item(
        Item={
            'cp_id': 'latest_poll', 'polls': latest_poll
            }
        )


# Kick users who haven't been seen in the last 1000 updates
def kick_inactive_users(table):
    print("Kicking inactive users")

    # get the voters from the latest polls
    response = table.get_item(
        Key={
            'cp_id': 'latest_poll'
            }
        )

    latest_poll = response['Item']['polls']

    voters = []

    for poll in latest_poll:
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


def puzzle_routine(table):
    print("Running the puzzle routine")
    puzzle = get_daily_puzzle()

    # check the last puzzle sent
    response = table.get_item(
        Key={
            'cp_id': 'latest_puzzle'
            }
        )

    # if the last puzzle was sent today, send the solution
    if response['Item']['date'] == datetime.today().date().isoformat():
        send_solution(puzzle)

    else:
        send_daily_puzzle(puzzle)
        # update the last puzzle sent
        table.put_item(
            Item={
                'cp_id': 'latest_puzzle', 'date': datetime.today().date().isoformat(), 'id': puzzle['puzzle']['id']
                }
            )


def is_first_run_today(table):
    print("Checking if it's the first run today")
    # get last day specific run
    response = table.get_item(
        Key={
            'cp_id': 'latest_run'
            }
        )

    # if the last day specific run was today, return True
    if response['Item']['date'] == datetime.today().date().isoformat():
        return False

    else:
        # update the last run date
        table.put_item(
            Item={
                'cp_id': 'latest_run', 'date': datetime.today().date().isoformat()
                }
            )
        return True


# Use this to test snippets locally
def local_testing():

    # Initialize the DynamoDB table
    session = boto3.Session(
        region_name=constants.AWS_REGION_CP,
        aws_access_key_id=constants.AWS_ACCESS_KEY_ID_CP,
        aws_secret_access_key=constants.AWS_SECRET_ACCESS_KEY_CP
        )

    table = session.resource('dynamodb').Table('cappello-parlante')

    # [{'update_id': 171822184, 'edited_message': {'message_id': 89, 'from': {'id': 853709991, 'is_bot': False, 'first_name': 'Flavio', 'last_name': 'Moccia', 'username': 'flaviomoccia'}, 'chat': {'id': -1002076164562, 'title': 'Circolo della fenice', 'type': 'supergroup'}, 'date': 1712768123, 'edit_date': 1712779068, 'voice': {'duration': 30, 'mime_type': 'audio/ogg', 'file_id': 'AwACAgQAAx0Ce7_B0gADWWYW7zwUZ0ZJUHVpAkS-O5nxfr4wAAIaEgACd8O4UL_4IlQUK2FONAQ', 'file_unique_id': 'AgADGhIAAnfDuFA', 'file_size': 122398}}}]
    updates = get_updates()

    handle_updates(updates, table)

    run_day_specific_tasks(table, updates)

    run_routine(updates, table)
