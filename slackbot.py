# -*- coding: utf-8 -*-
import os
import time
import re
from MarkovGenerator import Markov
from slackclient import SlackClient
import random


# instantiate Slack client

BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_USER_TOKEN = os.environ.get('SLACK_USER_TOKEN')
slack_client = SlackClient(BOT_TOKEN)
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = "MarkovSimulate"

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
MENTION_REGEX2 = "<@(|[WU].+?)>"
MENTION_REGEX3 = "<@u(.+?)>"

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def regexUpper(match):
    return match.group(0).upper()

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """
    SENTENCES = 4
    # Default response is help text for the user
    default_response = "Something broke! Contact the devs!"
    match = re.search(MENTION_REGEX2, command)
    response = None
    if match is None:
        response = "Cannot find user."
    else:
        user = match.group(1) 
        channelList = get_channels()
        userMessages = []
        
        if command.split(" ")[-1].isdigit():
            SENTENCES = int(command.split(" ")[-1])

        for channelObject in channelList["channels"]:
            if user in channelObject["members"]:
                history = get_history(channelObject["id"])
                for message in history["messages"]:
                    if "user" in message:
                        if message["user"] == user:
                            userMessages.append(message["text"])

        markovChain = ""
        starterWords = []
        for message in userMessages:
            starterWords.append(message.split(" ")[0].lower())
            if message[-1] != ".":
                message += ". "
            markovChain += message
        markov = Markov(markovChain)
        markov.create_word_chain()
        response = ""

        for i in range(0, SENTENCES):
            response += markov.create_response(curr_word=random.choice(starterWords))
            response += "\n"

        response = re.sub(MENTION_REGEX3, regexUpper, response)

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )

def get_channels():
    return slack_client.api_call("channels.list", token=SLACK_USER_TOKEN)


def get_history(channel):
    return slack_client.api_call("channels.history", channel=channel, token=SLACK_USER_TOKEN)

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")
