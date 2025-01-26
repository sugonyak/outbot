from outline_vpn.outline_vpn import OutlineVPN

import prettytable as pt
import logging, json, re
from telegram import Update, BotCommandScopeChat, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters
from dotenv import load_dotenv
import os
from prettytable import SINGLE_BORDER

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
    ('get_access_url_override', 'Get access url with override for key, args: server_name, key_name'),
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

def get_total_data_for_server(server):
    data_array = server.get_transferred_data()
    total_data = sum(data_array['bytesTransferredByUserId'].values())
    return total_data

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


def get_key_by_id(keys_object, key_id):
    for key in keys_object:
        if key.key_id == key_id:
            return key
    else:
        raise Exception(f"No key with id {key_id}")

def parse_access_url(url):
    access_url_regex = 'ss://.*@(?P<ip>[\\d\\.]+):(?P<port>[\\d]+)/.*'
    regex = re.compile(access_url_regex)
    match = re.match(regex, url)
    if match:
        return match.group('ip'), match.group('port')
    else:
        raise Exception('Cannot parse access url')

def generate_prefix_and_server_name(server):
    prefix = '%16%03%01%00%C2%A8%01%01'
    return f"&prefix={prefix}#{server}"

def log_event(update: Update, command="", server="", key_id="", key_name=""):
    logger.info(f'Received {command=} {server=} {key_id=} {key_name=} user={" ".join((update.effective_user.first_name, update.effective_user.last_name))}, username={update.effective_user.username}, userId={update.effective_user.id}')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.application.bot.delete_my_commands(scope=BotCommandScopeChat(update.effective_user.id))
    await context.application.bot.set_my_commands(commands=commands,scope=BotCommandScopeChat(update.effective_user.id))
    log_event(update, command="start")
    await update.message.reply_text(text=f'Hi admin! Check your commands, available servers:\n{'\n'.join(servers)}', reply_markup=ReplyKeyboardRemove())


async def list_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        server = parse_list_keys(update.message.text)
        client = init_server(server)
        total_data = get_total_data_for_server(client)
        global_data_limit = client.get_server_information()['accessKeyDataLimit']['bytes']
        keys_string = f"server: {server}\ntotal data: {bytes_to_gb(total_data):>.2f} GB\ndata limit: {bytes_to_gb(global_data_limit):>.2f} GB\n"

        table = pt.PrettyTable(['ID', 'Name', 'Used', 'Limit'])
        table.align = 'l'
        table.align['Used'] = 'r'
        table.set_style(SINGLE_BORDER)

        keys = client.get_keys()
        for key in keys:
            table.add_row([f'{key.key_id}', f'{key.name}'[:12], f'{bytes_to_gb(key.used_bytes):>.1f}', f'{bytes_to_gb(key.data_limit):>.1f}'])

        log_event(update, command="list_keys", server=server)
        await update.message.reply_text(f'{keys_string}<code>{table.get_string(sortby="Name")}</code>', parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'{e}')


async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        server, key_name = parse_key_action(update.message.text)
        client = init_server(server)
        key = client.create_key(name=key_name)
        log_event(update, command="add_key", server=server, key_name=key.name, key_id=key.key_id)

        await update.message.reply_text(f'Key {key.name} created with id {key.key_id}, access url:', parse_mode=ParseMode.HTML)
        await update.message.reply_text(f'\n<span class="tg-spoiler">{key.access_url}</span>', parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'{e}')


async def delete_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        server, key_id = parse_key_action(update.message.text)
        client = init_server(server)
        client.delete_key(key_id)
        log_event(update, command="delete_key", server=server, key_id=key_id)

        await update.message.reply_text(f'Server {server}, deleted key {key_id}')
    except Exception as e:
        await update.message.reply_text(f'{e}')


async def get_access_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        server, key_id = parse_key_action(update.message.text)
        client = init_server(server)
        keys = client.get_keys()
        key = get_key_by_id(keys, key_id)
        access_url = key.access_url
        log_event(update, command="get_access_url", server=server, key_name=key.name, key_id=key.key_id)

        await update.message.reply_text(f'Server {server}, key name {key.name}\naccess url:', parse_mode=ParseMode.HTML)
        await update.message.reply_text(f'<span class="tg-spoiler">{access_url}{generate_prefix_and_server_name(server)}</span>', parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'{e}')


async def get_access_url_override(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        server, key_id = parse_key_action(update.message.text)
        client = init_server(server)
        keys = client.get_keys()
        key = get_key_by_id(keys, key_id)
        if 'access_url_override' not in servers[server]:
            raise Exception(f'No override for server {server}')
        ip, port = parse_access_url(key.access_url)
        access_url = key.access_url.replace(f'{ip}:{port}', servers[server]['access_url_override'])
        log_event(update, command="get_access_url_override", server=server, key_name=key.name, key_id=key.key_id)

        await update.message.reply_text(f'Server {server}, key name {key.name}\naccess url:', parse_mode=ParseMode.HTML)
        await update.message.reply_text(f'<span class="tg-spoiler">{access_url}{generate_prefix_and_server_name(servers[server]['access_url_override_name'])}</span>', parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'{e}')


async def set_data_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        server, key_id, data_limit = parse_set_data_limit(update.message.text)
        client = init_server(server)
        client.add_data_limit(key_id, gb_to_bytes(data_limit))
        log_event(update, command="set_data_limit", server=server, key_id=key_id)
        await update.message.reply_text(f'Server {server}, set data limit {data_limit}GB to key {key_id}')
    except Exception as e:
        await update.message.reply_text(f'{e}')


async def not_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_event(update, command="start_non_admin")
    await context.application.bot.delete_my_commands(scope=BotCommandScopeChat(update.effective_user.id))
    await update.message.reply_text(f'You\'re not an admin user, sorry. Your user ID is {update.effective_user.id}')


def main() -> None:

    app = ApplicationBuilder().token(bot_token).build()
    logger.info('Adding handlers')

    app.add_handler(CommandHandler(command="start", callback=start, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="start", callback=not_admin, filters=~(filters.Chat(chat_id=admin_users))))

    app.add_handler(CommandHandler(command="list_keys", callback=list_keys, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="add_key", callback=add_key, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="delete_key", callback=delete_key, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="get_access_url", callback=get_access_url, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="get_access_url_override", callback=get_access_url_override, filters=filters.Chat(chat_id=admin_users)))
    app.add_handler(CommandHandler(command="set_data_limit", callback=set_data_limit, filters=filters.Chat(chat_id=admin_users)))
    logger.info('Starting polling')

    app.run_polling()

if __name__ == "__main__":

    main()
