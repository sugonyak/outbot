# Outbot
Small Python script for easy multi-server Outline management through Telegram

## Prerequisites
- [Telegram bot token](https://core.telegram.org/bots/tutorial#obtain-your-bot-token)
- [Outline server](https://support.getoutline.org/s/article/Outline-server-setup?language=en_US) and credentials from `/opt/outline/access.txt`

## Configuration
Example config:
```
{
    "admin_users":
    [
        TG_ADMIN_USER_ID,
        TG_ADMIN_USER_ID2
    ],
    "bot_token": "TG_BOT_TOKEN",
    "servers":
    {
        "example_server":
        {
            "url": "apiUrl FROM_ACCESS_TXT",
            "key": "certSha256 FROM_ACCESS_TXT",
            "access_url_override": "IP:PORT of two hop server, optional",
            "access_url_override_name": "name for override key, optional",
        }
    }
}
```
### Two hop server
See this [link](https://github.com/net4people/bbs/issues/126#issuecomment-1257116005)
## How to run
Set values to [config](#Configuration) and put config to `/opt/outbot-config.json`, then run:
```
docker run -d --name outbot -e APP_CONFIG_PATH=/opt/config.json -v /opt/outbot-config.json:/opt/config.json sugonyak/outbot:latest
```
Verify service by checking logs:
```
docker logs -f outbot
```
And finally - type `/start` in chat with your bot - it should update command list, and typing `/` again should give you all commands
## Development
### Run python
```
python3 -m venv ./venv
source venv/bin/activate
pip3 install -r requirements.txt
export APP_CONFIG_PATH=/path/to/your/config.json
python3 main.py
```
### Build docker
```
docker build -t outbot:latest .
```
