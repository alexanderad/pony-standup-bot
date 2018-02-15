# coding=utf-8
import six

if six.PY2:
    from string import letters
if six.PY3:
    from string import ascii_letters as letters

from datetime import datetime


class Dictionary(object):
    """Collection of phrases."""
    PLEASE_REPORT = (
        "Hey, just wanted to ask your current status. How it is going?",

        "Psst. I know you don't like it. But I have to ask. "
        "What is your status? Anything you want to share with the team? "
        "Few words.",

        "Hi. Ponies don't have to report. However, people made us "
        "to ask other people to. How are you doing today? Give me few words "
        "to share with the team.",

        "Amazing day, dear. I have a questionnaire here. Sponsored by your "
        "team. How is it going on your side today? Just a few words.",

        "Dear, I'm here to ask you about your status for the team. Could "
        "you be so kind to share few words on what you are working on now?",

        "Hello, it's me again. How are you doing today? Your team will be "
        "excited to hear. I need just a few words from you.",

        "Heya. Just asked all the team members. You are the last one. How's "
        "your day? Anything you want to share with the team?",

        "Good morning, dear. Just noticed you are online, decided to ask you "
        "your current status for the team. Few words to share?",

        "Dear, I apologize for the inconvenience. Would you mind sharing "
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

        "Another day, another question. Oh, wait, the question is the same. "
        "Your status is all I need to know. It's not me, it is for the team.",

        "Can't stop being bossy and asking people on the team their daily "
        "status. What do you have to say?",

        "Hi. That's a team check in. How did it go today?",
    )
    PLEASE_REPORT_LAST_CALL = (
        "This is the final boarding call for developers reporting to daily "
        "standup. Everything is about to happen! :runner:",

        "Pssst! I know you are busy. This happens to me as well. In few "
        "minutes I'm going to report daily status. Wanna be part of it?",

        "Busy day, eh? Maybe you have a few seconds to report your daily "
        "status, I'm about sending the final version of it! :clock430:",

        "You know that feeling when you ask somebody something "
        "but don't get any response back? That's awful. Wuuuf. Anyway I'm "
        "going to report daily status in a few minutes, would like to see you "
        "a part of it. ",

        "Ladies and gentlemen, captain speaking. We are about to report "
        "daily status, this is a kindly reminder for ya! :helicopter:",

        "Dear, this is just a kindly reminder for you to report your daily "
        "status! :bee:",

        "Everything is awesome, but you totally forgot about me! "
        "I'm reporting daily status in few moments, wanna join the "
        "crowd? :family:",

        "Busy like a bee? Just another question: wanna be a part of daily "
        "summary? One is soon to be sent out! :timer_clock:",
    )
    THANKS = (
        "Thanks! :+1:",
        "Thank you so much. Really appreciate it :+1:",
        "Glad to hear that!",
        "Thanks a lot. I'm happy about that.",
        "Great, this is on my notes now! :notes:",
        "Thank you, dear! :star2:",
        "Ok",
        "Thank you, I will report that to your boss.",
        "Many thanks. You :guitar:!",
        "You are so kind. Thanks :+1:",
        "Okay, will report that. Thanks.",
        "Ah, I see. ",
        "You are so hardworking today. Thanks.",
        "Love that. Thanks :+1:",
        "Oh nice! Great work you do!",
        "I see. That's intense! Thanks.",
        "Ah, okay. Thanks a lot. <3",
        "Sounds good. Thank you.",
        "Lovely, thanks!",
        "Alright, noted that.",
        "That's a lot. I do not envy you. Thanks, anyway! :+1:",
        "Oh, man. Okay, thanks! :+1:",
        "Sounds great! :muscle:",
        "Okay",
        "No way, that's a lot!",
        "Working hard day after day!",
        "Noted that :white_check_mark:",
        "Terrific! (terrific is a new awesome promoted by Woody Allen)",
        "Sounds good. Thanks!",
        "Thank you!",
        ":heavy_check_mark: Gotcha.",
        "Fantastic! :fire:",
        "Good",
        "Awesome, thanks! :cake:",
        "Thanks for sharing! :star2:",
        "Love that! <3",
        "Ty!",
        "That's great! :+1:",
        "Nice, let me write that down :pencil:",
        "Fascinating :sparkles:",
        "Perfect",
        "Noted that :bow:",
        "Thanks! :tropical_fish:",
        "Nice! :muscle:",
        "That is :cool:",
        "Great, thanks.",
        "Is it Friday already? I wish it was Friday. Noted your status, "
        "thanks anyway.",
        "OK",
        "Foarte bine!",
        "You are doing great!",
        "Incredible. Thanks.",
    )

    @staticmethod
    def initial_seed(user_id):
        # Slack IDs look like U023BECGF, U04B1CDVB, U04RVVBAY, etc
        digits = [
            letters.index(x) if not x.isdigit() else int(x)
            for x in user_id
        ]
        return sum(digits)

    @classmethod
    def pick(cls, phrases, user_id):
        # we want random phrases to be more predictable
        seed = cls.initial_seed(user_id)
        day_of_year = datetime.utcnow().timetuple().tm_yday
        return phrases[(seed + day_of_year) % len(phrases)]
