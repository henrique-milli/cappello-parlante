import json

import requests

import constants


def get_updates():
    print("Getting updates")

    response = requests.get(
        f"{constants.BOT_BASE_URL}/getUpdates", params={'offset': -1}
        )
    updates = response.json()['result']

    return updates


def send_message(text):
    print("Sending message")

    requests.post(
        f"{constants.BOT_BASE_URL}/sendMessage", data=json.dumps(
            {
                "chat_id": constants.CHAT_ID, "text": text
                }
            ), headers={'Content-Type': 'application/json'}
        )


def send_image(image_path, caption):
    print("Sending image")

    with open(image_path, 'rb') as image_file:
        files = {'photo': image_file}
        data = {'chat_id': constants.CHAT_ID, 'caption': caption}
        response = requests.post(f"{constants.BOT_BASE_URL}/sendPhoto", files=files, data=data)
        return response.json()


def kick_chat_member(user_id):
    print("Kicking chat member")

    response = requests.post(
        f"{constants.BOT_BASE_URL}/kickChatMember", data=json.dumps(
            {
                "chat_id": constants.CHAT_ID, "user_id": user_id
                }
            ), headers={'Content-Type': 'application/json'}
        )


def handle_updates(updates, table):

    for update in updates:
        if 'poll_answer' in update:
            handle_poll_answer(table, update['poll_answer'])

    add_new_users_to_table(updates, table)


def handle_poll_answer(table, poll_answer):
    poll_id = poll_answer['poll_id']
    user_id = poll_answer['user']['id']
    options_ids = poll_answer['option_ids']

    # Here you would add your own logic to store these details
    store_poll_answer(table, poll_id, user_id, options_ids)


def store_poll_answer(table, poll_id, user_id, oids):
    response = table.get_item(
        Key={
            'cp_id': 'latest_poll'
            }
        )

    if response['Item']['id'] != poll_id:
        return

    options_ids = response['Item']['options_ids']
    voters = response['Item']['voters']

    if user_id not in voters:
        voters.append(user_id)

    for oid in oids:
        options_ids.append(oid)


def add_new_users_to_table(updates, table):
    print("Adding new users to the table")

    # Get the users from the table
    response = table.get_item(
        Key={
            'cp_id': 'users'
            }
        )

    users_ids = response['Item']['users_ids']

    # Add new users to the table
    for update in updates:

        message = {}
        if 'message' in update:
            message = update['message']
        elif 'edited_message' in update:
            message = update['edited_message']
        else:
            continue

        if message['from']['id'] not in users_ids:
            users_ids.append(update['message']['from']['id'])

    # Update the users in the table
    table.put_item(
        Item={
            'cp_id': 'users', 'users_ids': users_ids
            }
        )
