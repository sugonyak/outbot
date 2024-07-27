from outline_vpn.outline_vpn import OutlineVPN

import logging, json
from telegram import Update, BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters
from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

config_path = os.getenv("APP_CONFIG_PATH", '.appconfig.json')

logger.info(f'Loading config from {config_path}')

f = open(config_path)
config = json.load(f)

admin_users = config['admin_users']
bot_token = config['bot_token']
servers = config['servers']

logger.info(f'Config loaded, got {len(admin_users)} admin(s), {len(servers)} server(s)')

commands = [
    ('start', 'Start bot, list servers and refresh commands'),
    ('list_keys', 'List keys on server, args: server_name'),
    ('add_key', 'Add new key, args: server_name, key_name'),
    ('delete_key', 'Delete key, args: server_name, key_name'),
    ('get_access_url', 'Get access url for key, args: server_name, key_name'),
    ('set_data_limit', 'Sets data limit for key, args: server_name, key_name, data_limit in GB')
]

def init_server(name):
    if name in servers:
        return OutlineVPN(api_url=servers[name]['url'], cert_sha256=servers[name]['key'])
    else:
        raise Exception(f"no server {name} in available servers")

def bytes_to_gb(bytes_value):
    if bytes_value:
        return bytes_value / 1000 / 1000 / 1000 
    else:
        return 0

def gb_to_bytes(gb_value: int):
    if int(gb_value):
        return int(gb_value) * 1000 * 1000 * 1000
    else:
        return 0

def parse_list_keys(command_string):
    # /command server key_name
    split = command_string.split(" ")
    server = split[1]
    return server

def parse_key_action(command_string):
    # /command server key_name
    split = command_string.split(" ")
    server = split[1]
    key_name = split[2].strip("\"”")
    return server, key_name

def parse_set_data_limit(command_string):
    # /command server key_name
    split = command_string.split(" ")
    server = split[1]
    key_name = split[2].strip("\"”")
    data_limit = split[3]
    return server, key_name, data_limit

def get_key_by_name(keys_object, key_name):
    for key in keys_object:
        if key.name == key_name:
            return key
    else:
        raise Exception(f"No key with name {key_name}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f'Recieved start command from {update.effective_user.first_name} {update.effective_user.last_name}, username {update.effective_user.username}')
    await context.application.bot.delete_my_commands(scope=BotCommandScopeChat(update.effective_user.id))
    await context.application.bot.set_my_commands(commands=commands,scope=BotCommandScopeChat(update.effective_user.id))
    await update.message.reply_text(text=f'Hi admin! Check your commands, available servers:\n{'\n'.join(servers)}')

async def list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Got list_keys command from {update.effective_user.first_name} {update.effective_user.last_name}, username {update.effective_user.username}")
    # list_keys nl
    try:
        server = parse_list_keys(update.message.text)
        client = init_server(server)
        keys_string = f"server: {server}\n"
        keys = client.get_keys()
        for key in keys:
            keys_string += f"{bytes_to_gb(key.used_bytes):>5.1f}/{bytes_to_gb(key.data_limit):<5.1f} {key.key_id:<3}:{key.name:<20}\n" 
        await update.message.reply_text(f'<code>{keys_string}</code>', parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'{e}')

async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Got add_key command from {update.effective_user.first_name} {update.effective_user.last_name}, username {update.effective_user.username}")
    # add_key nl "Key"
    try:
        server, key_name = parse_key_action(update.message.text)
        client = init_server(server)
        key = client.create_key(name=key_name)
        await update.message.reply_text(f'Key {key_name} created, access url:\n<code>{key.access_url}</code>', parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'{e}')

async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Got delete_key command from {update.effective_user.first_name} {update.effective_user.last_name}, username {update.effective_user.username}")
    # delete_key nl "Key"
    try:
        server, key_id = parse_key_action(update.message.text)
        client = init_server(server)
        keys = client.get_keys()
        # key = get_key_by_name(keys, key_name)
        client.delete_key(key_id)
        await update.message.reply_text(f'Server {server}, deleted key {key_id}')
    except Exception as e:
        await update.message.reply_text(f'{e}')

async def get_access_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"Got delete_key command from {update.effective_user.first_name} {update.effective_user.last_name}, username {update.effective_user.username}")
    # get_access_url nl "Key"
    try:
        server, key_id = parse_key_action(update.message.text)
        client = init_server(server)
        keys = client.get_keys()
        # key = get_key_by_name(keys, key_name)
        await update.message.reply_text(f'Server {server}, key {key_id} access url:\n<code>{key.access_url}</code>', parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'{e}')

async def set_data_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # set_data_limit nl "Key" 20
    logger.info(f"Got set_data_limit command from {update.effective_user.first_name} {update.effective_user.last_name}, username {update.effective_user.username}")
    try:
        server, key_id, data_limit = parse_set_data_limit(update.message.text)
        client = init_server(server)
        keys = client.get_keys()
        # key = get_key_by_name(keys, key_name)
        logger.info(f'Set data limit {data_limit}GB to key {key_id}')
        client.add_data_limit(key_id, gb_to_bytes(data_limit))
        await update.message.reply_text(f'Server {server}, set data limit {data_limit}GB to key {key_id}')
    except Exception as e:
        await update.message.reply_text(f'{e}')

async def not_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning(f'Got a start attempt from non-admin user {update.effective_user.first_name} {update.effective_user.last_name}, username: {update.effective_user.username}')
    await context.application.bot.delete_my_commands(scope=BotCommandScopeChat(update.effective_user.id))
    await update.message.reply_text('You\'re not an admin user, sorry')

def main() -> None:

    app = ApplicationBuilder().token(bot_token).build()
    logger.info('Adding handlers')

    app.add_handler(CommandHandler(command="start", callback=start, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="start", callback=not_admin, filters=~(filters.Chat(chat_id=admin_users))))

    app.add_handler(CommandHandler(command="list_keys", callback=list_keys, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="add_key", callback=add_key, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="delete_key", callback=delete_key, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="get_access_url", callback=get_access_url, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="set_data_limit", callback=set_data_limit, filters=filters.Chat(chat_id=admin_users)))
    logger.info('Starting polling')

    app.run_polling()

if __name__ == "__main__":

    main()
