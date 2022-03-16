import asyncio

import discord
from bs4 import BeautifulSoup as bs
import requests
from threading import Thread

from discord.ext import tasks

client = discord.Client()

telegram_url = 'https://t.me'
embed_param = 'embed=1&tme_mode=1'
posting_channel_id = 0
watch_channel_dict = {}
'''
{
    'test': 12,
    'test_b': 123,
}
'''


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))  # 봇이 실행되면 콘솔창에 표시


@client.event
async def on_message(message):
    global watch_channel_dict
    if message.author == client.user:  # 봇 자신이 보내는 메세지는 무시
        return

    if message.content.startswith('$set_watch_channel'):
        arg = message.content.strip('$set_watch_channel').split(' ')[1]
        print(arg)
        if not arg:
            print('Correct argument need')
            await message.channel.send('Need Correct argument! Please enter public channel url!')
            return

        info = arg.strip('https://t.me/').split('/')
        channel_name = info[0]
        latest_post_no = int(info[1])
        if await check_post(channel_name):
            latest_post_no = await get_last_post_no(channel_name, latest_post_no)
            watch_channel_dict[channel_name] = latest_post_no

            await message.channel.send('Add watchlist!')

    if message.content.startswith('$sync'):
        for watch_channel, latest_post_no in watch_channel_dict:
            latest_post_no = get_last_post_no(watch_channel, latest_post_no)
            watch_channel_dict[watch_channel] = latest_post_no

    if message.content.startswith('$channel_select'):
        arg = message.content.strip('$set_watch_channel').split(' ')[1]
        global posting_channel_id
        channel = discord.utils.get(client.get_all_channels(), name=arg)
        posting_channel_id = channel.id
        print('set channel', arg, posting_channel_id)
        await message.channel.send('Done channel select!')


async def check_post(channel):
    url = f'{telegram_url}/{channel}'
    page = requests.get(url)
    soup = bs(page.text, "html.parser")

    elements = soup.select('body > div.tgme_page_wrap > div.tgme_body_wrap > div > div.tgme_page_action > a')
    if elements[0].text == 'View in Telegram':
        return True
    else:
        return False


async def get_last_post_no(channel, start_post_no):
    url = f'{telegram_url}/{channel}'

    while True:
        post_url = f'{url}/{start_post_no}?{embed_param}'
        print(post_url)
        page = requests.get(post_url)
        soup = bs(page.text, "html.parser")

        element = soup.select_one('body > div > div.tgme_widget_message_bubble > div')
        print(element)
        if element.text == 'Post not found':
            last_post_no = start_post_no - 1
            print('last_content_no ', last_post_no)
            return last_post_no
        start_post_no += 1


async def find_last_post(channel, start_post_no):
    url = f'{telegram_url}/{channel}/'
    page = requests.get(url)
    soup = bs(page.text, "html.parser")

    while True:
        post_url = f'{url}/{start_post_no}'
        elements = soup.select('body > div > div.tgme_widget_message_bubble')
        if elements[0]:
            start_post_no += 1
        else:
            print('stop', start_post_no)


@tasks.loop(seconds=10)  # repeat after every 10 seconds
async def bg_task():
    global watch_channel_dict
    await client.wait_until_ready()
    if not posting_channel_id:
        print(posting_channel_id)
        return
    discord_channel = client.get_channel(posting_channel_id)
    print(watch_channel_dict)
    for watch_channel, latest_post_no in watch_channel_dict.items():
        current_latest_post_no = await get_last_post_no(watch_channel, latest_post_no)
        if current_latest_post_no > latest_post_no:
            watch_channel_dict[watch_channel] = current_latest_post_no
            url = f'{telegram_url}/{watch_channel}'
            post_url = f'{url}/{current_latest_post_no}'
            await discord_channel.send(post_url)


bg_task.start()
client.run('YOUR_BOT_TOKEN')  # 토큰
