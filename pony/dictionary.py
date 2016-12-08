# coding=utf-8
import string
from datetime import datetime


class Dictionary(object):
    """Collection of phrases."""
    # Please report is expected to include team's name. Leave a placeholder.
    PLEASE_REPORT = (
        "Hey, just wanted to ask your current status for {}, how it is going?",

        "Psst. I know, you hate it. But I have to ask for {}. Any blockers?",

        "Hi. Ponies don't have to report. However people on {} made us "
        "to ask other people to. How are you doing today? Give me few words "
        "to share with the team.",

        "Amazing day, dear. I have a questionnaire here. Sponsored by {}. How "
        "it is going on your side today?",

        "Dear, I'm here to ask you about your status for {}. Could "
        "you be so kind to share few words on what you are working on now?",

        "Hello, it's me again. How are you doing today? {} will be excited "
        "to hear. I need just few words from you.",

        "Heya. Just asked all {} members. You are the last one. How's "
        "your day? Anything you want to share with the team?",

        "Hi there! Amazing day. Oh, wait, is that word banned on your team? "
        "Nevermind. I'm here to ask you your daily status update for {}. "
        "Would you mind sharing few words?",

        "Good morning, dear. Just noticed you are online, decided to ask you "
        "your current status for the {}. Few words to share?",

        "Dear, I apologise for the inconvenience. Would you mind sharing "
        "your status with {}? Few words.",

        "Good morning. Your beloved pony is here again to ask your daily "
        "status for {}. How are you doing today?",

        "Hello, dear. Pony here. What's your story today? Anything to share "
        "with {}?",

        "Honey, good morning! That's a Standup Pony, your best friend. How "
        "are you doing today? Asking for {}.",

        "Bonjorno. Busy day, eh? May I ask you to spend few seconds to tell "
        "me your current status? Just a few words to share with the {}.",

        "Hello there. I'm asking you the same thing each day. Because of {}. "
        "Feels a bit like a date to me. Oh well, what's your today's status?",

        "Another day, another question. Oh, wait, question is the same. Your "
        "status is all I need to know. It's not me, it is {}.",
        
        "Good day. Having English breakfast while pony asks people their "
        "status for {} dear? How do you do?",

        "Can't stop being bossy and asking people on {} their daily status. "
        "What do you have to say?",
    )
    THANKS = (
        "Thanks! :+1:",
        "Thank you so much. Really appreciate it :+1:",
        "Thanks a lot. I'm happy about that.",
        "Thank you, dear. :star2:",
        "Ok",
        "Thank you, I will report to your boss. I mean BOSS.",
        "Many thanks. You :guitar:",
        "You are so kind. Thanks :+1:",
        "Okay, will report that. Thanks.",
        "You are so hardworking today. Thanks.",
        "Love that. Thanks :+1:",
        "I see. That's intense! Thanks.",
        "Ah, okay. Thanks a lot.",
        "Sounds good. Thank you.",
        "Lovely, thanks!",
        "That's a lot. I do not envy you. Thanks, anyway! :+1:",
        "Oh, man. Okay, thanks! :+1:",
        "Sounds great! :muscle:",
        "Okay",
        "No way, that's a lot!",
        "Noted that :white_check_mark:",
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
