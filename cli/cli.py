import os
import shutil
from datetime import datetime
from functools import wraps
from pathlib import Path
from signal import signal, SIGINT

import click

try:
    import click
except ModuleNotFoundError as e:
    print(e)
    print(
        "You should try running pipenv shell and pipenv install per the install instructions"
    )
    print("Or you should only use Python 3.8.X per the instructions.")
    print(
        "If you are attempting to run multiple bots, this is not supported, so you are on your own to figure out that one."
    )
    exit(0)
import time

from notifications.notifications import NotificationHandler, TIME_FORMAT
from utils.logger import log
from common.globalconfig import GlobalConfig, AMAZON_CREDENTIAL_FILE
from utils.version import is_latest, version
from stores.amazon import Amazon
from stores.bestbuy import BestBuyHandler


def get_folder_size(folder):
    return sizeof_fmt(sum(file.stat().st_size for file in Path(folder).rglob("*")))


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


def handler(signal, frame):
    log.info("Caught the stop, exiting.")
    exit(0)


def notify_on_crash(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:
            pass
        except:
            notification_handler.send_notification(f"FairGame has crashed.")
            raise

    return decorator


@click.group()
def main():
    pass


# @click.command()
# @click.option(
#     "--gpu",
#     type=click.Choice(GPU_DISPLAY_NAMES, case_sensitive=False),
#     prompt="What GPU are you after?",
#     cls=QuestionaryOption,
# )
# @click.option(
#     "--locale",
#     type=click.Choice(CURRENCY_LOCALE_MAP.keys(), case_sensitive=False),
#     prompt="What locale shall we use?",
#     cls=QuestionaryOption,
# )
# @click.option("--test", is_flag=True)
# @click.option("--interval", type=int, default=5)
# @notify_on_crash
# def nvidia(gpu, locale, test, interval):
#     nv = NvidiaBuyer(
#         gpu,
#         notification_handler=notification_handler,
#         locale=locale,
#         test=test,
#         interval=interval,
#     )
#     nv.run_items()


@click.command()
@click.option("--no-image", is_flag=True, help="Do not load images")
@click.option("--headless", is_flag=True, help="Unsupported headless mode. GLHF")
@click.option(
    "--test",
    is_flag=True,
    help="Run the checkout flow, but do not actually purchase the item[s]",
)
@click.option(
    "--delay", type=float, default=3.0, help="Time to wait between checks for item[s]"
)
@click.option(
    "--checkshipping",
    is_flag=True,
    help="Factor shipping costs into reserve price and look for items with a shipping price",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Take more screenshots. !!!!!! This could cause you to miss checkouts !!!!!!",
)
@click.option(
    "--used",
    is_flag=True,
    help="Show used items in search listings.",
)
@click.option("--single-shot", is_flag=True, help="Quit after 1 successful purchase")
@click.option(
    "--no-screenshots",
    is_flag=True,
    help="Take NO screenshots, do not bother asking for help if you use this... Screenshots are the best tool we have for troubleshooting",
)
@click.option(
    "--disable-presence",
    is_flag=True,
    help="Disable Discord Rich Presence functionallity",
)
@click.option(
    "--disable-sound",
    is_flag=True,
    default=False,
    help="Disable local sounds.  Does not affect Apprise notification " "sounds.",
)
@click.option(
    "--slow-mode",
    is_flag=True,
    default=False,
    help="Uses normal page load strategy for selenium. Default is none",
)
@click.option(
    "--p",
    type=str,
    default=None,
    help="Pass in encryption file password as argument",
)
@click.option(
    "--log-stock-check",
    is_flag=True,
    default=False,
    help="writes stock check information to terminal and log",
)
@click.option(
    "--shipping-bypass",
    is_flag=True,
    default=False,
    help="Will attempt to click ship to address button. USE AT YOUR OWN RISK!",
)
@click.option(
    "--clean-profile",
    is_flag=True,
    default=False,
    help="Purge the user profile that Fairgame uses for browsing",
)
@click.option(
    "--clean-credentials",
    is_flag=True,
    default=False,
    help="Purge Amazon credentials and prompt for new credentials",
)
@notify_on_crash
def amazon(
    no_image,
    headless,
    test,
    delay,
    checkshipping,
    detailed,
    used,
    single_shot,
    no_screenshots,
    disable_presence,
    disable_sound,
    slow_mode,
    p,
    log_stock_check,
    shipping_bypass,
    clean_profile,
    clean_credentials,
):
    notification_handler.sound_enabled = not disable_sound
    if not notification_handler.sound_enabled:
        log.info("Local sounds have been disabled.")

    if clean_profile and os.path.exists(global_config.get_browser_profile_path()):
        log.info(
            f"Removing existing profile at '{global_config.get_browser_profile_path()}'"
        )
        profile_size = get_folder_size(global_config.get_browser_profile_path())
        shutil.rmtree(global_config.get_browser_profile_path())
        log.info(f"Freed {profile_size}")

    if clean_credentials and os.path.exists(AMAZON_CREDENTIAL_FILE):
        log.info(f"Removing existing Amazon credentials from {AMAZON_CREDENTIAL_FILE}")
        os.remove(AMAZON_CREDENTIAL_FILE)

    amzn_obj = Amazon(
        headless=headless,
        notification_handler=notification_handler,
        checkshipping=checkshipping,
        detailed=detailed,
        used=used,
        single_shot=single_shot,
        no_screenshots=no_screenshots,
        disable_presence=disable_presence,
        slow_mode=slow_mode,
        no_image=no_image,
        encryption_pass=p,
        log_stock_check=log_stock_check,
        shipping_bypass=shipping_bypass,
    )
    try:
        amzn_obj.run(delay=delay, test=test)
    except RuntimeError:
        del amzn_obj
        log.error("Exiting Program...")
        time.sleep(5)


@click.command()
@click.option("--sku", type=str, required=True)
@click.option("--headless", is_flag=True)
@notify_on_crash
def bestbuy(sku, headless):
    bb = BestBuyHandler(
        sku, notification_handler=notification_handler, headless=headless
    )
    bb.run_item()


@click.option(
    "--disable-sound",
    is_flag=True,
    default=False,
    help="Disable local sounds.  Does not affect Apprise notification " "sounds.",
)
@click.command()
def test_notifications(disable_sound):
    enabled_handlers = ", ".join(notification_handler.enabled_handlers)
    message_time = datetime.now().strftime(TIME_FORMAT)
    notification_handler.send_notification(
        f"Beep boop. This is a test notification from FairGame. Sent {message_time}."
    )
    log.info(f"A notification was sent to the following handlers: {enabled_handlers}")
    if not disable_sound:
        log.info("Testing notification sound...")
        notification_handler.play_notify_sound()
        time.sleep(2)  # Prevent audio overlap
        log.info("Testing alert sound...")
        notification_handler.play_alarm_sound()
        time.sleep(2)  # Prevent audio overlap
        log.info("Testing purchase sound...")
        notification_handler.play_purchase_sound()
    else:
        log.info("Local sounds disabled for this test.")

    # Give the notifications a chance to get out before we quit
    time.sleep(5)


signal(SIGINT, handler)

main.add_command(amazon)
main.add_command(bestbuy)
main.add_command(test_notifications)

# Global scope stuff here
if is_latest():
    log.info(f"FairGame v{version}")
elif version.is_prerelease:
    log.warning(f"FairGame PRE-RELEASE v{version}")
else:
    log.warning(
        f"You are running FairGame v{version.release}, but the most recent version is v{version.get_latest_version()}. "
        f"Consider upgrading "
    )

global_config = GlobalConfig()
notification_handler = NotificationHandler()
