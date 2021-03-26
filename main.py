from include import *
from peewee import SqliteDatabase
import argparse
import traceback
import sys
import datetime
import requests
import json
import logging
from shutil import copyfile

from apscheduler.schedulers.background import BackgroundScheduler

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, DispatcherHandlerStop
import telegram


def _get_target(update, context):
    return [user for user in BUPTUser.select() if (user.username in context.args) or (not context.args)]


def _out_sch_check(update, buptuser, force=False):
    if buptuser.out_json is None:
        update.message.reply_markdown("> To enable auto leaving school record, you need to send me a json text")
        update.message.reply_text('/upload \<stu-id\> {"username":"","phone":"","out_loc":"","out_execuse":"","monitor":"","monitor_id":""}')
        return 'More data needed!'
    return buptuser.out_sch_checkin(force=force)[:100]



def private_check(func):
    def inner(update, context, *args, **kwargs):
        if update.message.from_user.id != TG_BOT_MASTER:
            update.message.reply_markdown('# 403 Forbidden')
        else:
            func(update, context, *args, **kwargs)
    return inner


@private_check
def upload_entry(update, context):
    stu_id, sjson = context.args
    try:
        buptuser = BUPTUser.get(BUPTUser.username == stu_id)
        json.loads(sjson)
        buptuser.out_json = sjson
        buptuser.save()
        update.message.reply_text('stored')
    except Exception as e:
        update.message.reply_text(f'Error: {e}')


@private_check
def start_entry(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("Welcome, {}.\nSpecial Thanks to https://github.com/ipid/bupt-ncov-report".format(
        update.message.from_user.username or update.message.from_user.first_name or ''), disable_web_page_preview=True)


@private_check
def list_entry(update, context, admin_all=False):
    first_message = update.message.reply_markdown(f"用户列表查询中 ...")
    users = BUPTUser.select()

    ret_msgs = []
    ret_msg = ''
    for i, user in enumerate(users):
        if i % 10 == 0 and i != 0:
            ret_msgs.append(ret_msg)
            ret_msg = ''
        id = i+1
        ret_msg += f'ID: `{id}`\n'
        if user.username != None:
            # Password: `{user.password}`\n'
            ret_msg += f'Username: `{user.username}`\n'
        else:
            # UUKey: `{user.cookie_uukey}`\n'
            ret_msg += f'eai-sess: `{user.cookie_eaisess}`\n'
        if admin_all:
            ret_msg += f'Owner: `{user.owner.userid}` `{user.owner.username.replace("`","")}`\n'
        if user.status == BUPTUserStatus.normal:
            ret_msg += f'自动签到: `启用`\n'
        else:
            ret_msg += f'自动签到: `暂停`\n'
        if user.latest_response_data == None:
            ret_msg += '从未尝试签到\n'
        else:
            ret_msg += f'最后签到时间: `{user.latest_response_time}`\n'
            ret_msg += f'最后签到返回: `{user.latest_response_data[:100]}`\n'
        ret_msg += "\n"
    ret_msgs.append(ret_msg)

    if len(users) == 0:
        ret_msgs = ['用户列表为空']
    logger.debug(ret_msgs)

    first_message.delete()
    for msg in ret_msgs:
        update.message.reply_markdown(msg)


@private_check
def add_user_entry(update, context):
    if len(context.args) != 2:
        first_message = update.message.reply_markdown(
            f"例：/add `2010211000` `password123`")
        return
    username, password = context.args
    first_message = update.message.reply_markdown(f"Adding ...")

    buptuser, _ = BUPTUser.get_or_create(
        username=username,
        password=password,
        status=BUPTUserStatus.normal
    )

    first_message.edit_text('添加成功！', parse_mode=telegram.ParseMode.MARKDOWN)
    list_entry(update, context)


@private_check
def checkin_out_entry(update, context):
    targets = _get_target(update, context)
    if len(targets) == 0:
        ret_msg = '用户列表为空'
        update.message.reply_markdown(ret_msg)
        return
    for buptuser in targets:
        try:
            ret = _out_sch_check(update, buptuser)
            ret_msg = f"用户：`{buptuser.username}`\n报备成功！\n服务器返回：`{ret}`"
        except Exception as e:
            ret_msg = f"用户：`{buptuser.username}`\n报备异常！\n服务器返回：`{e}`"
        update.message.reply_markdown(ret_msg)


@private_check
def checkin_entry(update, context):
    targets = _get_target(update, context)
    if len(targets) == 0:
        ret_msg = '用户列表为空'
        update.message.reply_markdown(ret_msg)
        return
    for buptuser in targets:
        try:
            ret = buptuser.ncov_checkin(force=True)[:100]
            ret_msg = f"用户：`{buptuser.username}`\n签到成功！\n服务器返回：`{ret}`"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{buptuser.username}`\n签到失败，服务器错误！\n`{e}`"
        except Exception as e:
            ret_msg = f"用户：`{buptuser.username}`\n签到异常！\n服务器返回：`{e}`"
        update.message.reply_markdown(ret_msg)


@private_check
def pause_entry(update, context):
    targets = _get_target(update, context)

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.stopped
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username}`\n已暂停自动签到。"
        update.message.reply_markdown(ret_msg)


@private_check
def resume_entry(update, context):
    targets = _get_target(update, context)

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.normal
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username}`\n已启用自动签到。"
        update.message.reply_markdown(ret_msg)


@private_check
def remove_entry(update, context):
    assert len(context.args) > 0, "错误的命令。"

    targets = _get_target(update, context)

    for buptuser in targets:
        buptuser.delete_instance()
        ret_msg = f"用户：`{buptuser.username}`\n已删除。"
        update.message.reply_markdown(ret_msg)

    list_entry(update, context)


@private_check
def error_callback(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s: %s"', update,
                   context.error.__class__.__name__, context.error)
    update.message.reply_text("{}: {}".format(
        context.error.__class__.__name__, context.error))
    traceback.print_exc()


@private_check
def tg_debug_logging(update, context):
    log_str = 'User %s `%d`: "%s"' % (
        update.message.from_user.username, update.message.from_user.id, update.message.text)
    logger.info(log_str)

    # Skip forwarding when command call.
    if update.message.text is not None and update.message.text.startswith('/'):
        return
    # Skip master message
    if update.message.from_user.id == TG_BOT_MASTER:
        return

    updater.bot.send_message(
        chat_id=TG_BOT_MASTER, text="[LOG] " + log_str, parse_mode=telegram.ParseMode.MARKDOWN)
    # Forward non-text message, like stickers.
    if update.message.text is None:
        updater.bot.forward_message(
            TG_BOT_MASTER, update.message.chat_id, update.message.message_id)


@private_check
def status_entry(update, context):
    cron_data = "\n".join(["name: %s, trigger: %s, handler: %s, next: %s" % (
        job.name, job.trigger, job.func, job.next_run_time) for job in scheduler.get_jobs()])
    update.message.reply_text("Cronjob: " + cron_data)
    update.message.reply_text("System time: " + str(datetime.datetime.now()))


def backup_db():
    logger.info("backup started!")
    copyfile('./my_app.db', './backup/my_app.{}.db'.format(
        str(datetime.datetime.now()).replace(":", "").replace(" ", "_")))
    logger.info("backup finished!")


def checkin_all_retry():
    logger.info("checkin_all_retry started!")
    for user in BUPTUser.select().where(
        (BUPTUser.status == BUPTUserStatus.normal)
        & (BUPTUser.latest_response_time < datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time()))
    ):
        ret_msg = ''
        try:
            ret = user.ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username}`\n重试签到成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username}`\n重试签到失败，服务器错误，请尝试手动签到！\nhttps://app.bupt.edu.cn/ncov/wap/default/index\n`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username}`\n重试签到异常！\n服务器返回：`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        logger.info(ret_msg)
        updater.bot.send_message(
            chat_id=user.owner.userid, text=ret_msg, parse_mode=telegram.ParseMode.MARKDOWN)
    logger.info("checkin_all_retry finished!")


def checkin_all():
    try:
        backup_db()
    except:
        pass
    logger.info("checkin_all started!")
    for user in BUPTUser.select().where(BUPTUser.status == BUPTUserStatus.normal):
        ret_msg = ''
        try:
            ret = user.ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username}`\n自动签到成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username}`\n自动签到失败，服务器错误，将重试！\n`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username}`\n自动签到异常！\n服务器返回：`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        logger.info(ret_msg)
        updater.bot.send_message(
            chat_id=TG_BOT_MASTER, text=ret_msg, parse_mode=telegram.ParseMode.MARKDOWN)
    logger.info("checkin_all finished!")


def checkin_out_all():
    logger.info("checkin_out_all started!")
    for user in BUPTUser.select().where(BUPTUser.status == BUPTUserStatus.normal):
        ret_msg = ''
        try:
            ret = _out_sch_check(updater, user)
            ret_msg = f"用户：`{user.username}`\n自动报备成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except Exception as e:
            ret_msg = f"用户：`{user.username}`\n自动报备异常！\n服务器返回：`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        logger.info(ret_msg)
        updater.bot.send_message(
            chat_id=TG_BOT_MASTER, text=ret_msg, parse_mode=telegram.ParseMode.MARKDOWN)
    logger.info("checkin_out_all finished!")


def main():
    global updater, scheduler
    parser = argparse.ArgumentParser(description='BUPT 2019-nCoV Report Bot')
    parser.add_argument('--initdb', default=False, action='store_true')
    args = parser.parse_args()

    database = SqliteDatabase(config.SQLITE_DB_FILE_PATH)
    database_proxy.initialize(database)

    if args.initdb:
        db_init()
        exit(0)

    updater = Updater(
        TG_BOT_TOKEN, request_kwargs=TG_BOT_PROXY, use_context=True)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(MessageHandler(Filters.all, tg_debug_logging), -10)
    dp.add_handler(CommandHandler("start", start_entry))
    dp.add_handler(CommandHandler("list", list_entry))
    dp.add_handler(CommandHandler("add", add_user_entry))
    dp.add_handler(CommandHandler("checkin", checkin_entry))
    dp.add_handler(CommandHandler("checkinout", checkin_out_entry))
    dp.add_handler(CommandHandler("upload", upload_entry))
    dp.add_handler(CommandHandler("pause", pause_entry))
    dp.add_handler(CommandHandler("resume", resume_entry))
    dp.add_handler(CommandHandler("remove", remove_entry))
    dp.add_handler(CommandHandler("status", status_entry))

    # on noncommand i.e message - echo the message on Telegram
    #dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error_callback)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.

    scheduler.add_job(
        func=checkin_all,
        id='checkin_all',
        trigger="cron",
        hour=CHECKIN_ALL_CRON_HOUR,
        minute=CHECKIN_ALL_CRON_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_retry,
        id='checkin_all_retry',
        trigger="cron",
        hour=CHECKIN_ALL_CRON_RETRY_HOUR,
        minute=CHECKIN_ALL_CRON_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    scheduler.add_job(
        func=checkin_out_all,
        id='checkin_out_all',
        trigger="cron",
        hour=CHECKIN_OUT_ALL_CRON_HOUR,
        minute=CHECKIN_OUT_ALL_CRON_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    scheduler.start()
    logger.info(["name: %s, trigger: %s, handler: %s, next: %s" % (
        job.name, job.trigger, job.func, job.next_run_time) for job in scheduler.get_jobs()])

    updater.idle()


if __name__ == "__main__":
    logging.basicConfig(
        handlers=[
            logging.handlers.TimedRotatingFileHandler(
                "log/main", when='midnight', backupCount=30, encoding='utf-8',
                atTime=datetime.time(hour=0, minute=0)
            ),
            logging.StreamHandler(sys.stdout)
        ],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    scheduler = BackgroundScheduler(timezone=CRON_TIMEZONE)

    main()
