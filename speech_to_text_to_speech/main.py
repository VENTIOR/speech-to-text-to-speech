import asyncio
import logging
import os
import sys
import pynput
import httpcore
import httpx
import speech_recognition as sr
import translatepy.translators
from voicevox import Client
from speech_to_text_to_speech.playsound import play_sound

SOUNDFILE_NAME = os.getenv("SOUNDFILE_NAME")
RECORD_KEY = os.getenv("RECORD_KEY")
STOP_KEY = os.getenv("STOP_KEY")

r = sr.Recognizer()
gtranslate = translatepy.translators.GoogleTranslate()


def get_user_input():
    # Gets the user input to choose the mic for input
    chosen_microphone = input('Choose your microphone using its Index or "Default": ')
    return chosen_microphone


def get_mic(send_mics: bool):
    # Gets executed recursively if no correct input is given
    for i, microphone_name in enumerate(sr.Microphone.list_microphone_names()):
        print(i, microphone_name)

    chosen_microphone = get_user_input()
    if chosen_microphone.upper() == "DEFAULT":
        return None
    try:
        sr.Microphone.list_microphone_names()[int(chosen_microphone)]
    except ValueError:
        print("Not a valid choice!")
        chosen_microphone = get_mic(False)
    return int(chosen_microphone)


async def get_speaker(send_speaker: bool):
    async with Client() as client:
        speakers_list = await client.fetch_speakers()
    if send_speaker:
        for i, speaker in enumerate(speakers_list):
            print(i, speaker.name)

    speaker = input("Please specify which speaker you want to use: ")
    try:
        speakers_list[int(speaker)]
    except ValueError:
        print("Not a valid speaker!")
        await get_speaker(send_speaker=False)
    return int(speaker)


def keyboard_input():
    # Starts a keyboard listener - may cause inputlag
    def on_press(key):
        global running
        try:
            if key.char == RECORD_KEY:
                running = not running
                logging.info(f"Set running to {running}")
            elif key.char == STOP_KEY:
                sys.exit()
        except AttributeError:
            pass

    listener = pynput.keyboard.Listener(
        on_press=on_press
    )
    listener.start()


async def get_japanese_translation():
    # Gets translation to give to Voicevox
    with sr.Microphone(device_index=chosen_mic) as source:
        logging.info("Adjusting...")
        r.adjust_for_ambient_noise(source)
        logging.info("Now listening")
        audio_data = r.listen(source)
        logging.info("Recognizing...")
        try:
            text = r.recognize_google(audio_data, language="de")
            translation = gtranslate.translate(text, "Japanese", source_language='de')
            logging.info('Recognized input: {} | Translation: {}'.format(text, translation))
            return translation.result
        except:
            logging.error("Unknown Translation")
            await get_japanese_translation()


async def synthesize(speaker: int):
    # Synthesizes the final voice
    async with Client() as client:
        try:
            print(speaker)
            audio_query = await client.create_audio_query(await get_japanese_translation(), speaker=speaker)
            logging.info("Synthesizing...")
            with open(SOUNDFILE_NAME, "wb") as f:
                f.write(await audio_query.synthesis(speaker=speaker))
        except (httpcore.ConnectError, ConnectionRefusedError, OSError, httpx.ConnectError):
            logging.error("Connection refused")
        else:
            logging.info("Finished synthesizing")


async def main():
    await synthesize(speaker=speaker)
    await play_sound()


chosen_mic = get_mic(True)
keyboard_input()
speaker = asyncio.run(get_speaker(True))
running = False
while True:
    if running:
        asyncio.run(main())
