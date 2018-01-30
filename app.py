# -*- coding: utf-8 -*-
import sys
sys.path.append('./vendor')

import os
import uuid

from PIL import Image
import io

from flask import Flask, request, abort, send_file

from linebot import (
    LineBotApi, WebhookHandler,
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, VideoMessage, TextSendMessage, AudioMessage, StickerSendMessage, AudioSendMessage
)

from pydub import AudioSegment
import ffmpeg

import argparse
import io

app = Flask(__name__, static_folder='tmp')

line_bot_api = LineBotApi(os.environ.get('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('CHANNEL_SECRET'))

@app.route("/", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=AudioMessage)
def handle_content_message(event):
    if isinstance(event.message, ImageMessage):
        ext = 'jpg'
    elif isinstance(event.message, VideoMessage):
        ext = 'mp4'
    elif isinstance(event.message, AudioMessage):
        ext = 'm4a'
    else:
        return

    message_content = line_bot_api.get_message_content(event.message.id)
    dirname = 'tmp'
    fileName = uuid.uuid4().hex
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    with open("tmp/{}.m4a".format(fileName), 'wb') as audio:
        audio.write(message_content.content)

    AudioSegment.converter = "/usr/local/bin/ffmpeg"
    flac_audio = AudioSegment.from_file("tmp/{}.m4a".format(fileName))
    flac_audio.export("tmp/{}.flac".format(fileName), format="flac")
    text = transcribe_file("tmp/{}.flac".format(fileName))

    title_of_song = "おもちゃのチャチャチャ" # use some useful API to get name
    line_bot_api.reply_message(
        event.reply_token, [
            TextSendMessage(text=text),
            TextSendMessage(text="{}ですね？".format(title_of_song)),
            StickerSendMessage(package_id=1, sticker_id=7),
        ]
    )

def transcribe_file(speech_file):
    """Transcribe the given audio file."""
    from google.cloud import speech
    from google.cloud.speech import enums
    from google.cloud.speech import types
    client = speech.SpeechClient()

    # [START migration_sync_request]
    # [START migration_audio_config_file]
    with io.open(speech_file, 'rb') as audio_file:
        content = audio_file.read()

    audio = types.RecognitionAudio(content=content)
    config = types.RecognitionConfig(
        #encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
        #sample_rate_hertz=16000,
        #language_code='en-US')
        language_code='ja-JP')
    # [END migration_audio_config_file]

    # [START migration_sync_response]
    response = client.recognize(config, audio)
    # [END migration_sync_request]
    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    for result in response.results:
        # The first alternative is the most likely one for this portion.
        print('Transcript: {}'.format(result.alternatives[0].transcript))
        return response.results[0].alternatives[0].transcript

    return '聞き取れませんでした'

if __name__ == "__main__":
    app.debug = True
    app.run(host='localhost')
