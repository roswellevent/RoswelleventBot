#!/usr/bin/env python
import datetime
import json
import logging
import re
import requests
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler)
from bs4 import BeautifulSoup
import time
from datetime import timedelta
from wakeonlan import send_magic_packet
from icalendar import Calendar, Event
from RoswelleventBotConfig import BotConfig


logger = logging.getLogger(__name__)
keyboard = [
            #[InlineKeyboardButton("恆生指數", callback_data='1'),
            # InlineKeyboardButton("股票報價", callback_data='2')]
            # ,
            [InlineKeyboardButton("市場資訊", callback_data='3'),
             InlineKeyboardButton("定期存款利率", callback_data='4')
             ],
            [InlineKeyboardButton("6D 巴士到站時間", callback_data='5')
            ]
           ]

markup = InlineKeyboardMarkup(keyboard)

def getBusStopInfo(p_route,p_bound,p_stop_seq):
    url = 'http://search.kmb.hk/KMBWebSite/Function/FunctionRequest.ashx?action=getstops'
    payload = {'route': p_route, 'bound': p_bound}
    r = requests.get(url, payload)
    r.encoding = 'UTF-8'
    j = json.loads(r.text)
    basicInfo = j['data']['basicInfo']
    routeStop = j['data']['routeStops'][int(p_stop_seq)]
    stopinfo = {'OriCName': basicInfo['OriCName'], 'DestCName': basicInfo['DestCName'], 'StopInfo': routeStop}
    return stopinfo

def getBusStopETA(p_route,p_stop_seq,p_bound, lang = 'tc'):
    url = 'http://etav3.kmb.hk/?action=geteta'
    payload = {'route': p_route, 'stop_seq': p_stop_seq, 'bound': p_bound, 'lang': lang}
    r = requests.get(url,payload)
    r.encoding ="UTF-8"
    j = json.loads(r.text)
    etainfo = j['response']
    return etainfo


def getBusStopSummary(p_route,p_bound,p_stop_seq):
    BusStopInfo = getBusStopInfo(p_route, p_bound,p_stop_seq)
    title = ("*{} (往{}) - {}*".format(p_route, BusStopInfo['DestCName'], BusStopInfo['StopInfo']['CName'])) + '\n'
    title += "----------------------------------------------\n"
    o = getBusStopETA(p_route,BusStopInfo['StopInfo']['Seq'], p_bound)
    current_time = time.strftime("%H:%M")

    for info in o:
            if (info['t'] != '尾班車已過本站' and "行車受阻" not in str(info['t'])):
                eta_time = timedelta(minutes=int(info['t'][0:2]),seconds=int(info['t'][3:5]))
                cur_time = timedelta(minutes=int(current_time[0:2]),seconds=int(current_time[3:5]))
                delta_time = eta_time - cur_time
                total_seconds = delta_time.total_seconds()
                if (total_seconds> 0):
                    delta_minutes = str(delta_time.total_seconds())[:-2]
                    title += '到站時間: {} ({}分鐘)'.format(info['t'], delta_minutes) + '\n'
                else:
                    if (len(o) < 2):
                        title += '尾班車剛剛已過本站!\n'
            else:
                title += info['t'] +'\n'

    return title

def getPublicFinanceInterestRate():
    url = "https://www.publicfinance.com.hk/2/finance/asp/interest_rate_tc.asp"
    r = requests.get(url)
    r.encoding = "UTF-8"
    soup = BeautifulSoup(r.text,'html.parser')
    interest_table = soup.findAll('table',{'class': 'content'})
    effective_date = soup.findAll('span',{'class': 'content'})

    amount = (interest_table[0].select("td > p")[1].get_text())
    three_month_interest_rate = interest_table[0].select("td > p")[3].get_text()
    six_month_interest_rate = interest_table[0].select("td > p")[5].get_text()
    one_year_interest_rate = interest_table[0].select("td > p")[7].get_text()
    effective_date = effective_date[0].get_text()
    title ="*大眾財務高息定期存款利率*"

    content_table = title + '\n\n'
    content_table += amount + '\n'
    content_table += '--------------------------------------' + '\n'
    content_table += '三個月      ' + three_month_interest_rate + '\n'
    content_table += '六個月      ' + six_month_interest_rate + '\n'
    content_table += '十二個月  ' + one_year_interest_rate + '\n'
    content_table += '\n' + effective_date + '\n'

    return content_table

def getHSI():
    url = "http://money18.on.cc/js/real/hk/index/HSI_r.js"
    j = get_json(url)
    j["change"] = str(percentage(j["value"], j["pc"]))
    return j


def getStockInfo(stock_no):
    stock_no = str(stock_no).zfill(5)
    url1 = "http://money18.on.cc/js/real/hk/quote/{}_r.js".format(stock_no)
    url2 = "http://money18.on.cc/js/daily/hk/quote/{}_d.js".format(stock_no)
    j1 = get_json(url1)
    if j1:
        j = get_json(url2)
        j["np"] = j1["np"]
        return j
    else:
        return False


def get_json(url):
    r = requests.get(url)
    r.encoding = "Big5"
    p = re.compile(r'{.*}', re.DOTALL)
    result = r.text.replace("'", '"')
    m = p.search(result)
    text = m.group()
    try:
        jsonObj = json.loads(text)
        return jsonObj
    except ValueError as err:
        print("invalid json: %s" % err)
        return False

def percentage(current_price, prev_price):
    return round(100 * (float(current_price) - float(prev_price)) / float(prev_price), 2)


def start(bot, update):
    update.message.reply_text('Welcome to Stock Bot', reply_markup=markup)
#    job.run_daily(daily_stock_summary, market_open_time, market_days, context=update.message.chat_id)
#    job.run_daily(daily_stock_summary, market_close_time, market_days, context=update.message.chat_id)


def getHSItoMessage():
    j = getHSI()
    direction = "升" if float(j["difference"]) >= 0 else "跌"
    o = '*恆生指數:* ' + j["value"] + ' \n' + direction + ': ' + j["difference"] + ' (' + j["change"] + '%)'
    return o


def getStockInfotoMessage():
    stocks_no = config.getStockNo()
    o = ""
    for stock_no in stocks_no:
        j = getStockInfo(stock_no)
        current_price = j["np"]
        prev_price = j["preCPrice"]
        company_name = j["nameChi"]
        percent = percentage(current_price, prev_price)
        diff = round(float(current_price)- float(prev_price), 3)
        direction = "升" if percent >= 0 else "跌"
        o += '*{}* ({}) : ${} \n{} ${} ({}%)\n\n'.format(company_name, stock_no, current_price, direction, str(diff), str(percent))
    return o


def getMarketSummary():
    o = "*市場資訊*\n"
    o += "-------------------------------------------------\n"
    o += getHSItoMessage() + '\n\n*股票報價*\n'
    o += "-------------------------------------------------\n"
    o += getStockInfotoMessage()
    return o


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def click_button(bot, update):
    query = update.callback_query
    if query.data == '1':
        o = getHSItoMessage()
        bot.sendMessage(chat_id=query.message.chat_id, text=o, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        #bot.answerCallbackQuery(callback_query_id=query.id, text=o, show_alert=True)
    elif query.data == '2':
        o = getStockInfotoMessage()
        bot.sendMessage(chat_id=query.message.chat_id, text=o, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        #bot.answerCallbackQuery(callback_query_id=query.id, text=o, show_alert=True)
    elif query.data == '3':
        o = getMarketSummary()
        bot.sendMessage(chat_id=query.message.chat_id, text=o, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    elif query.data == '4':
        o = getPublicFinanceInterestRate()
        bot.sendMessage(chat_id=query.message.chat_id, text=o, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    elif query.data == '5':

        route = "6D"
        stop_no = "21"
        bound = "2"
        o = getBusStopSummary(route,bound,stop_no)
        stop_no = "0"
        bound = "1"
        o += '\n\n' + getBusStopSummary(route, bound, stop_no)
        bot.sendMessage(chat_id=query.message.chat_id, text=o, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
    return 0


def daily_stock_summary(bot, job):
    if not TodayIsHoliday(): # Check if today is a hoiliday
        o = getMarketSummary()
        bot.send_message(chat_id=job.context, text=o, parse_mode=ParseMode.MARKDOWN)


def callback_timer(bot, update, job_queue):
    job.run_daily(daily_stock_summary, market_close_time, market_days, context=update.message.chat_id)
    bot.send_message(chat_id=update.message.chat_id, text="Timer On")
	
def WakeUp(bot, update):
	MAC_ADDR = '10:C3:7B:A1:E9:B2'
	send_magic_packet('ff.ff.ff.ff.ff.ff',MAC_ADDR)
	update.message.reply_text('Wake Up PC.....', reply_markup=markup)
	
def TodayIsHoliday():
    URL = "http://www.1823.gov.hk/common/ical/gc/tc.ics"
    r = requests.get(URL)
    c = Calendar.from_ical(r.text)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    flag = False
    for component in c.walk():
        if component.name == "VEVENT":
            day = component.decoded('dtstart')
            if (str(day) == today):
                flag = True
    return flag



def stock_list(bot, update):
    stocks_no = config.getStockNo()
    o = "*Stock List*\n"
    o += "-------------------------------------\n"
    i = 0
    for stock_no in stocks_no:
        i += 1
        out = getStockInfo(stock_no)
        o +=  "*{}. {}*({})\n\n".format(i, out['nameChi'],stock_no)
    bot.sendMessage(chat_id=update.message.chat_id, text=o, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)

def stock_add(bot, update, args):
    for arg in args:
        if arg.isdigit():
            out = getStockInfo(arg)
            if (out):
                o = "已加入*{}*({})\n\n".format( out['nameChi'],arg)
                bot.sendMessage(chat_id=update.message.chat_id, text=o,parse_mode=ParseMode.MARKDOWN)
                config.addStockNo(int(arg))
            else:
                o = "{} 不是有效股票號碼!!!".format(arg)
                bot.sendMessage(chat_id=update.message.chat_id, text=o)
        else:
            o = "股票號碼必須是數字!!!"
            bot.sendMessage(chat_id=update.message.chat_id, text=o)
    return 0

def stock_remove(bot, update, args):
    for arg in args:
        if arg.isdigit() and config.removeStockNo(int(arg)):
            out = getStockInfo(arg)
            o = "已刪除*{}*({})\n\n".format(out['nameChi'], arg)
        else:
            o = "*{}*不在股票監測明單內".format(arg)
        bot.sendMessage(chat_id=update.message.chat_id, text=o, parse_mode=ParseMode.MARKDOWN)

config = BotConfig()
BOT_TOKEN = config.getTelegramBotToken()
ROSWELLEVENT_ID = config.getMyTelegramID()

market_close_time = datetime.time(16, 0, 0)
market_open_time = datetime.time(9, 30, 0)
market_morning_session_close_time = datetime.time(13, 0, 0)
market_days = (0, 1, 2, 3, 4)

updater = Updater(BOT_TOKEN)
job = updater.job_queue
job.run_daily(daily_stock_summary, market_open_time, market_days, context=ROSWELLEVENT_ID)
job.run_daily(daily_stock_summary, market_close_time, market_days, context=ROSWELLEVENT_ID)
job.run_daily(daily_stock_summary, market_morning_session_close_time, market_days, context=ROSWELLEVENT_ID)

dp = updater.dispatcher
dp.add_handler(CommandHandler('start', start))
dp.add_handler(CommandHandler('timer', callback_timer, pass_job_queue=True))
dp.add_handler(CommandHandler('wol', WakeUp))
dp.add_handler(CommandHandler('stock_list', stock_list))
dp.add_handler(CommandHandler('stock_add', stock_add,pass_args=True))
dp.add_handler(CommandHandler('stock_remove', stock_remove,pass_args=True))

dp.add_handler(CallbackQueryHandler(click_button))
updater.start_polling()
dp.add_error_handler(error)
updater.idle()
