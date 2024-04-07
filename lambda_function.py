import asyncio
import datetime
import os

import boto3
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PLAY_ALLOWED_DAYS = os.getenv("PLAY_ALLOWED_DAYS").split(',')
MIN_PLAYERS_FOR_MEETUP = int(os.getenv("MIN_PLAYERS_FOR_MEETUP"))
LATEST_POLLS_SIZE = int(os.getenv("LATEST_POLLS_SIZE"))
AWS_ACCESS_KEY_ID_CP = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY_CP = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION_CP = os.getenv("AWS_REGION")


async def main():
    # Initialize the DynamoDB client
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID_CP,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY_CP,
        region_name=AWS_REGION_CP
        )

    # Now you can use this session to create service clients or resources
    dynamodb = session.resource('dynamodb')

    # Get a reference to the 'cappello-parlante' table
    table = dynamodb.Table('cappello-parlante')

    # Initialize the bot
    bot = Bot(token=BOT_TOKEN)

    # Get the updates
    updates = bot.get_updates()

    # Add new users to the table
    add_new_users_to_table(updates, table)

    today = datetime.datetime.today().weekday()

    # Evaluate the latest poll if it's thursday
    if today == 3:
        evaluate_poll(bot, table, updates)

    # Send a new poll if it's monday
    if today == 0:
        await send_meet_poll(bot, table)
        await kick_inactive_users(bot, table)

    # Close the event loop
    loop.close()


# Evaluate the latest poll
def evaluate_poll(bot, table, updates):
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
        if update.poll and update.poll.id == latest_poll_id:
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
            bot.send_message(
                chat_id=CHAT_ID,
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
async def send_meet_poll(bot, table):
    pool_message = await bot.send_poll(
        chat_id=CHAT_ID,
        question="Questa settimana quando giochiamo?",
        options=PLAY_ALLOWED_DAYS,
        is_anonymous=False,
        allows_multiple_answers=True, )

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
    if len(latest_polls) >= LATEST_POLLS_SIZE:
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
async def kick_inactive_users(bot, table):
    # Get the users from the table
    response = table.get_item(
        Key={
            'cp_id': 'users'
            }
        )

    users = response['Item']['users']

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
            bot.kick_chat_member(chat_id=CHAT_ID, user_id=user)
            users.remove(user)

    # Delete the users in the table
    table.put_item(
        Item={
            'cp_id': 'users', 'users': users
            }
        )


def add_new_users_to_table(updates, table):
    # Get the users from the table
    response = table.get_item(
        Key={
            'cp_id': 'users'
            }
        )

    users = response['Item']['users']

    # Add new users to the table
    for update in updates:
        if update.message.from_user.id not in users:
            users.append(update.message.from_user.id)

    # Update the users in the table
    table.put_item(
        Item={
            'cp_id': 'users', 'users': users
            }
        )


def lambda_handler(event, context):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    return {
        'statusCode': 200,
        'body': 'OK'
        }