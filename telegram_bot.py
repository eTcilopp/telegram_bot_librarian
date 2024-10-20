########################################
# Telegram bot
# t.me/book_wise_helper_bot
#
########################################
import telebot
import dotenv
import os
from openai import OpenAI
from pymongo import MongoClient

from prompts import *

dotenv.load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MONGO_DB_CONNECTION_STRING = os.environ.get("MONGO_DB_CONNECTION_STRING")

AI_MODEL_SMART = "gpt-4o"
AI_MODEL_SIMPLE = "gpt-4o"
AI_ASSISTANT_NAME = "Librarian"


def verify_text(text, ai_client):
    chat_completion = ai_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": VERIFICATION_INSTRUCTION
            },
            {
                "role": "user",
                "content": text,
            }
        ],
        model=AI_MODEL_SIMPLE,
    )
    return chat_completion.choices[0].message.content
    

def get_ai_reply(**kwargs):
    
    ai_client = kwargs.get('ai_client')
    ai_assistant = kwargs.get('ai_assistant')
    ai_thread_id = kwargs.get('ai_thread_id')
    text = kwargs.get('text')
    instructions = kwargs.get('instructions')
    
    message = ai_client.beta.threads.messages.create(
        thread_id=ai_thread_id,
        role="user",
        content=text
    )
    
    run = ai_client.beta.threads.runs.create_and_poll(
        thread_id=ai_thread_id,
        assistant_id=ai_assistant.id,
        instructions=instructions
    )
    
    while run.status != 'completed':
        continue

    messages = ai_client.beta.threads.messages.list(
        thread_id=ai_thread_id
    )

    text_response = messages.data[0].content[0].text.value
  

    return text_response

def get_ai_thread_id(chat_id, collection, ai_client):
    query = {"chat_id": chat_id}
    thread_record = collection.find_one(query)
    if thread_record:
        return thread_record.get('thread_id')
    new_thread = ai_client.beta.threads.create()
    document = {"chat_id": chat_id, "thread_id": new_thread.id}
    collection.insert_one(document)
    return new_thread.id
        
def get_ai_assistant(ai_client, ai_assistant_name=AI_ASSISTANT_NAME):
    assistant_lst = ai_client.beta.assistants.list()
    for assistant in assistant_lst:
        if assistant.name == ai_assistant_name:
            return assistant

    return ai_client.beta.assistants.create(
        name=AI_ASSISTANT_NAME,
        instructions=AI_ASSISTANT_INSTRUCTION,
        model=AI_MODEL_SMART,
    )


bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    first_message_text = START_PROMPT
    bot.reply_to(message, first_message_text)

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    ai_thread_id = get_ai_thread_id(message.chat.id, collection, ai_client)
    legit_request = verify_text(message.text, ai_client)
    message_params = {
        'ai_client': ai_client,
        'ai_assistant': ai_assistant,
        'ai_thread_id': ai_thread_id, 
        'text': message.text        
    }
    if 'false' in legit_request.lower():
        message_params.update({'instructions': INCORRECT_REQUEST_INSTRUCTION})
    reply = get_ai_reply(**message_params)
    bot.reply_to(message, reply)


mongo_client = MongoClient(MONGO_DB_CONNECTION_STRING)
mongo_db = mongo_client.threads_database
collection = mongo_db.chat_to_thread_collection

ai_client = OpenAI(api_key=OPENAI_API_KEY)
ai_assistant = get_ai_assistant(ai_client)


if __name__ == '__main__':
    # bot.infinity_polling()
    while True:
        try:
            bot.polling(none_stop=True)
        except:
            pass
