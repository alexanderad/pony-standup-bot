# coding=utf-8
import string
from datetime import datetime


class Dictionary(object):
    """Collection of phrases."""
    # Please report is expected to include team's name. Leave a placeholder.
    PLEASE_REPORT = (
        "Hey, just wanted to ask your current status. How it is going?",

        "Psst. I know, you hate it. But I have to ask. What is your status? "
        "Anything you want to share with the team? Few words.",

        "Hi. Ponies don't have to report. However people made us "
        "to ask other people to. How are you doing today? Give me few words "
        "to share with the team.",

        "Amazing day, dear. I have a questionnaire here. Sponsored by your "
        "team. How it is going on your side today? Just few words.",

        "Dear, I'm here to ask you about your status for the team. Could "
        "you be so kind to share few words on what you are working on now?",

        "Hello, it's me again. How are you doing today? Your team will be "
        "excited to hear. I need just few words from you.",

        "Heya. Just asked all the team members. You are the last one. How's "
        "your day? Anything you want to share with the team?",

        "Hi there! Amazing day. Oh, wait, is that word banned on your team? "
        "Nevermind. I'm here to ask you your daily status update for the "
        "team. Would you mind sharing few words?",

        "Good morning, dear. Just noticed you are online, decided to ask you "
        "your current status for the team. Few words to share?",

        "Dear, I apologise for the inconvenience. Would you mind sharing "
        "your status with the team? Few words.",

        "Good morning. Your beloved pony is here again to ask your daily "
        "status for the team. How are you doing today, anything to share?",

        "Hello, dear. Pony here. What's your story today? Anything to share "
        "with the team?",

        "Honey, good morning! That's a Standup Pony, your best friend. How "
        "are you doing today? Asking for the team.",

        "Bonjorno. Busy day, eh? May I ask you to spend few seconds to tell "
        "me your current status? Just a few words to share with the team.",

        "Hello there. I'm asking you the same thing each day. Because of the "
        "team. Feels a bit like a date to me. Oh well, what's your today's "
        "status?",

        "Another day, another question. Oh, wait, question is the same. Your "
        "status is all I need to know. It's not me, it is for the team.",

        "Can't stop being bossy and asking people on the team their daily "
        "status. What do you have to say?",

        "Hi. That's a team check in. How did it go today?",
    )
    THANKS = (
        "Thanks! :+1:",
        "Thank you so much. Really appreciate it :+1:",
        "Thanks a lot. I'm happy about that.",
        "Thank you, dear! :star2:",
        "Ok",
        "Thank you, I will report to your boss. I mean BOSS.",
        "Many thanks. You :guitar:!",
        "You are so kind. Thanks :+1:",
        "Okay, will report that. Thanks.",
        "You are so hardworking today. Thanks.",
        "Love that. Thanks :+1:",
        "I see. That's intense! Thanks.",
        "Ah, okay. Thanks a lot. <3",
        "Sounds good. Thank you.",
        "Lovely, thanks!",
        "That's a lot. I do not envy you. Thanks, anyway! :+1:",
        "Oh, man. Okay, thanks! :+1:",
        "Sounds great! :muscle:",
        "Okay",
        "No way, that's a lot!",
        "Noted that :white_check_mark:",
        "Sounds good. Thanks!",
        ":heavy_check_mark: Gotcha.",
        "Fantastic! :fire:",
        "Good",
        "Thanks for sharing! :star2:",
        "Love that! <3",
        "Fascinating :sparkles:",
        "Perfect",
        ":bow:",
        "Thanks! :tropical_fish:",
        "Nice! :muscle:",
        ":cool:",
        "Great, thanks.",
        "OK",
    )

    @staticmethod
    def initial_seed(user_id):
        # Slack IDs look like U023BECGF, U04B1CDVB, U04RVVBAY, etc
        digits = [
            string.letters.index(x) if not x.isdigit() else int(x)
            for x in user_id
        ]
        return sum(digits)

    @classmethod
    def pick(cls, phrases, user_id):
        # we want random phrases to be more predictable
        seed = cls.initial_seed(user_id)
        day_of_year = datetime.utcnow().timetuple().tm_yday
        return phrases[(seed + day_of_year) % len(phrases)]
