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

    response = requests.post(
        f"{constants.BOT_BASE_URL}/sendMessage", data=json.dumps(
            {
                "chat_id": constants.CHAT_ID, "text": text
                }
            ), headers={'Content-Type': 'application/json'}
        )


def send_image(image_path, caption):
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
