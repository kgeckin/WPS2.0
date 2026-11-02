"""
WhatsApp Phishing Awareness Simulator — sender.py

Purpose
-------
Send WhatsApp phishing campaign messages via Selenium automation.
Optimized for 200–1000 sends per run. English-only code & logs.

Key fixes in this patch
-----------------------
- Clickable links: always use "/redirect" and URL-encode the token.
- Reliable chat open: pass digits-only phone to WA (no '+'), use /send endpoint.
- Stale driver protection: consider a driver dead when it has no windows.
- Resilient Chrome start: expand %VARS% in profile path, ensure folder exists,
  clean lock files, and fall back to a temp profile if Chrome crashes with
  "DevToolsActivePort file doesn't exist".
"""

from __future__ import annotations

import os
import re
import time
import tempfile
import logging
import threading
from typing import Iterable, Optional
from urllib.parse import quote

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import SessionNotCreatedException

from db_utils import fetch_all_users, fetch_all_campaigns, log_action
from encrypt_utils import generate_encrypted_token
from campaign_approval import approved_batch, record_audit

# ============================================================================
# Environment & globals
# ============================================================================
load_dotenv()

BASE_URL = os.getenv("AWARENESS_BASE_URL", "http://127.0.0.1:5000")

# Prefer an explicit path from .env; otherwise use %LOCALAPPDATA%\WPSWA (Windows) or a local folder
_default_profile_root = os.getenv("LOCALAPPDATA", os.getcwd())
CHROME_PROFILE_DIR = os.getenv("CHROME_PROFILE_DIR", os.path.join(_default_profile_root, "WPSWA"))

# Shared logger; GUI attaches a Tk handler to this name.
logger = logging.getLogger("WPS")

# ============================================================================
# Path helpers
# ============================================================================

def _resolve_dir(path: str) -> str:
    """Expand %VARS% and ~, then return an absolute path."""
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))

# ============================================================================
# Phone normalization
# ============================================================================

def normalize_phone(raw: str, default_cc: str = "90") -> str:
    """Return a best-effort E.164-like phone number.

    Rules:
      - If it starts with '+', keep '+' and digits only.
      - If it starts with '00', convert to '+' and keep digits after '00'.
      - If digits start with the default country code, prefix '+'.
      - If it is exactly 10 digits (typical local mobile length), prefix '+<default_cc>'.
      - If it has 11–15 digits (likely includes country code without '+'), prefix '+'.
      - Otherwise, fallback to '+<default_cc><digits>'.
    """
    if not raw:
        return ""
    s_raw = raw.strip()
    digits = re.sub(r"\D", "", s_raw)

    if s_raw.startswith("+"):
        return "+" + digits
    if s_raw.startswith("00"):
        return "+" + re.sub(r"\D", "", s_raw[2:])
    if digits.startswith(default_cc):
        return "+" + digits
    if len(digits) == 10:
        return f"+{default_cc}{digits}"
    if 11 <= len(digits) <= 15:
        return "+" + digits
    return f"+{default_cc}{digits}"


def phone_digits_for_wa(phone: str) -> str:
    """Return digits-only MSISDN for WhatsApp Web URL (no '+', spaces or punctuation)."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("00"):
        digits = digits[2:]
    return digits

# ============================================================================
# WebDriver setup
# ============================================================================

def _clean_profile_locks(profile_dir: str) -> None:
    """Best-effort removal of Chrome profile lock files to avoid startup errors."""
    try:
        abs_profile = _resolve_dir(profile_dir)
        for name in ("SingletonLock", "SingletonCookie", "SingletonSockets", "DevToolsActivePort"):
            p = os.path.join(abs_profile, name)
            if os.path.exists(p):
                os.remove(p)
    except Exception as e:
        logger.warning(f"Could not clean Chrome profile locks: {e}")


def setup_driver(profile_dir: str = CHROME_PROFILE_DIR) -> webdriver.Chrome:
    """Create a Selenium Chrome driver using a persistent profile.

    - Expands %VARS%/~/relative paths.
    - Ensures the profile directory exists.
    - Cleans known lock files.
    - If Chrome fails to start (DevToolsActivePort), falls back to a temporary profile.
    """
    # Resolve and prepare the profile directory
    abs_profile = _resolve_dir(profile_dir)
    os.makedirs(abs_profile, exist_ok=True)
    _clean_profile_locks(abs_profile)

    def _new_driver(user_data_dir: Optional[str]) -> webdriver.Chrome:
        chrome_options = Options()
        if user_data_dir:
            chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
            chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--lang=en")
        chrome_options.add_argument("--remote-debugging-port=0")  # choose free port automatically
        chrome_options.page_load_strategy = "eager"
        drv = webdriver.Chrome(options=chrome_options)
        return drv

    try:
        driver = _new_driver(abs_profile)
    except SessionNotCreatedException as e:
        # Common on Windows when the profile is locked, corrupted, OneDrive-synced, or path contains unexpanded vars.
        logger.error(
            "Chrome failed to start with the configured profile (%s). Will retry with a TEMP profile.\n"
            "Details: %s",
            abs_profile,
            e,
        )
        tmp_dir = tempfile.mkdtemp(prefix="WPSProfile_")
        driver = _new_driver(tmp_dir)
        logger.info("Using temporary Chrome profile for this run: %s", tmp_dir)
    except Exception as e:
        logger.error("Chrome failed to start: %s", e)
        tmp_dir = tempfile.mkdtemp(prefix="WPSProfile_")
        driver = _new_driver(tmp_dir)
        logger.info("Using temporary Chrome profile for this run: %s", tmp_dir)

    driver.get("https://web.whatsapp.com/")
    logger.info("Please scan the QR code in the Chrome window if prompted.")

    # Wait until either the QR or the chat UI appears
    try:
        WebDriverWait(driver, 30).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']")
            or d.find_elements(By.CSS_SELECTOR, "div[aria-label='Search or start new chat'], div[data-tab='3']")
        )
    except Exception:
        logger.error("WhatsApp Web initial UI did not load in time.")
        return driver

    # Poll until logged in (QR disappears and chat UI is visible), max 3 min
    deadline = time.time() + 180
    while time.time() < deadline:
        qr_present = bool(driver.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']"))
        chat_ready = bool(
            driver.find_elements(By.CSS_SELECTOR, "div[aria-label='Search or start new chat'], div[data-tab='3']")
        )
        if not qr_present and chat_ready:
            logger.info("WhatsApp Web is ready (logged in).")
            return driver
        if qr_present:
            logger.info("Waiting for QR scan...")
        time.sleep(1.2)

    logger.error("Login timeout: QR was not scanned in time.")
    return driver

# ============================================================================
# Link builders
# ============================================================================

def build_campaign_link(user_id: int, campaign_id: int) -> str:
    """Return a clickable, URL-safe phishing link for a given user/campaign."""
    token = generate_encrypted_token(user_id, campaign_id)
    return f"{BASE_URL.rstrip('/')}/redirect?data={quote(token, safe='')}"


def build_message_text(campaign_message: str, user_id: int, campaign_id: int) -> str:
    """Compose the WhatsApp message body with the phishing link on its own line."""
    link = build_campaign_link(user_id, campaign_id)
    return (
        f"{campaign_message}\n"
        f"{link}\n"
        f"(This is a security awareness simulation.)"
    )

# ============================================================================
# Compose & send
# ============================================================================

def _wait_for_compose(driver, timeout: int = 20):
    """Return the message compose box (not the search box)."""
    end = time.time() + timeout
    while time.time() < end:
        elems = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='conversation-compose-box-input']")
        if not elems:
            elems = driver.find_elements(By.CSS_SELECTOR, "footer div[contenteditable='true'][data-tab='10']")
        if not elems:
            elems = driver.find_elements(By.CSS_SELECTOR, "footer div[contenteditable='true'][aria-multiline='true']")
        if not elems:
            elems = driver.find_elements(By.CSS_SELECTOR, "footer [role='textbox']")
        if elems:
            return elems[0]
        time.sleep(0.5)
    return None


def _click_send_button(driver, timeout: int = 10) -> bool:
    """Click the green send button when it is enabled using language-agnostic selectors."""
    locators = [
        (By.CSS_SELECTOR, "button[data-testid='compose-btn-send'][aria-disabled='false']"),
        (By.XPATH, "//span[@data-icon='send']/ancestor::button[not(@disabled)]"),
    ]
    end = time.time() + timeout
    while time.time() < end:
        for by, sel in locators:
            try:
                btn = driver.find_element(by, sel)
                aria = (btn.get_attribute("aria-disabled") or "").lower()
                if aria in ("true", "1"):
                    break  # still disabled; keep waiting
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                driver.execute_script("arguments[0].click();", btn)
                return True
            except Exception:
                continue
        time.sleep(0.3)
    return False


def send_message(driver, phone: str, message: str, per_step_timeout: int = 20) -> bool:
    """Open chat, type message as a single bubble, and send once (no delivery verification)."""
    msisdn = phone_digits_for_wa(phone)
    if not msisdn:
        logger.error("Invalid recipient phone after normalization.")
        return False

    url = f"https://web.whatsapp.com/send/?phone={msisdn}&app_absent=0"
    driver.get(url)

    # Wait until the chat page is ready (conversation panel or compose box visible)
    def _chat_page_ready(drv) -> bool:
        try:
            if drv.find_elements(By.CSS_SELECTOR, "div[data-testid='conversation-panel-messages']"):
                return True
            if drv.find_elements(By.CSS_SELECTOR, "div[aria-label='Message list']"):
                return True
            if _wait_for_compose(drv, timeout=1):
                return True
        except Exception:
            pass
        return False

    try:
        WebDriverWait(driver, per_step_timeout).until(lambda d: _chat_page_ready(d))
    except Exception:
        logger.error("Chat did not open within timeout.")
        return False

    compose = _wait_for_compose(driver, timeout=12)
    if not compose:
        logger.error("Message compose box not found.")
        return False

    # Focus, clear, type fresh
    driver.execute_script("arguments[0].focus();", compose)
    time.sleep(0.1)
    compose.send_keys(Keys.CONTROL, "a")
    compose.send_keys(Keys.DELETE)

    # Type as single bubble (SHIFT+ENTER for new lines)
    lines = message.splitlines()
    for idx, line in enumerate(lines):
        if line:
            compose.send_keys(line)
        if idx < len(lines) - 1:
            compose.send_keys(Keys.SHIFT, Keys.ENTER)

    # Small nudge so send button becomes enabled
    compose.send_keys(" ")
    compose.send_keys(Keys.BACK_SPACE)

    # Send once: prefer button, fallback ENTER
    if not _click_send_button(driver, timeout=8):
        compose.send_keys(Keys.ENTER)

    time.sleep(0.8)
    logger.info("Message dispatched to one approved recipient.")
    return True

# ============================================================================
# Driver reuse (singleton) + run mutex
# ============================================================================

_DRIVER_SINGLETON: webdriver.Chrome | None = None
_SEND_MUTEX = threading.Lock()  # serialize runs on the same driver


def _driver_is_alive(driver) -> bool:
    """Return True if the session is live and at least one window is open."""
    try:
        handles = driver.window_handles
        return bool(handles)
    except Exception:
        return False


def get_or_create_driver(keep_open: bool, profile_dir: str = CHROME_PROFILE_DIR):
    """Reuse the existing driver when possible. If none (or dead), create a new one."""
    global _DRIVER_SINGLETON

    if _DRIVER_SINGLETON and _driver_is_alive(_DRIVER_SINGLETON):
        return _DRIVER_SINGLETON

    # No live driver -> create a new one
    driver = setup_driver(profile_dir=profile_dir)
    if keep_open:
        _DRIVER_SINGLETON = driver
    return driver

# ============================================================================
# Main campaign runner
# ============================================================================

def run_whatsapp_campaign(
    campaign_id: int,
    target_user_ids: Optional[Iterable[int]] = None,
    country_code: str = "90",
    keep_open: bool = False,
    dry_run: bool = True,
) -> None:
    """Send the selected campaign via WhatsApp Web.

    Args:
        campaign_id: Campaign to send.
        target_user_ids: If provided, only these user IDs (and Active) are targeted.
        country_code: Default country code used to normalize local numbers (e.g., "90").
        keep_open: If True, keep Chrome open after the run (manual close).
        dry_run: True by default. GUI enables delivery only after explicit approval.
    """
    # Load active users
    try:
        users = fetch_all_users(active_only=True)
    except TypeError:
        # If db_utils doesn't support the argument, fallback and filter manually
        users = [u for u in (fetch_all_users() or []) if u.get("is_active", 1)]

    # Never silently expand selection to all active contacts.
    approval, users = approved_batch(
        campaign_id=campaign_id,
        selected_user_ids=target_user_ids,
        active_users=users,
        country_code=country_code,
    )

    # Load campaign
    campaigns = fetch_all_campaigns()
    campaign = next((c for c in campaigns if c["campaign_id"] == campaign_id), None)
    if not campaign:
        logger.error(f"Campaign ID {campaign_id} not found.")
        return

    message_template = campaign["message"]
    logger.info(
        "Approved awareness campaign %s, scope %s, recipient count %d.",
        campaign_id, approval.authorization_reference, len(users),
    )
    if dry_run:
        record_audit("preview", campaign_id, approval, len(users))
        logger.info("DRY RUN: no Chrome session opened and no messages delivered.")
        return

    record_audit("start", campaign_id, approval, len(users))
    driver = get_or_create_driver(keep_open=keep_open, profile_dir=CHROME_PROFILE_DIR)

    dispatched = 0
    try:
        with _SEND_MUTEX:  # prevent concurrent runs from sharing the driver at the same time
            for i, user in enumerate(users, start=1):
                # Normalize phone to E.164-like format
                phone = normalize_phone(user.get("phone", ""), default_cc=country_code)
                if not phone:
                    logger.warning(f"[{i}/{len(users)}] User #{user['user_id']} has no valid phone; skipping")
                    continue

                # Build user-specific message with a proper clickable link
                message = build_message_text(message_template, user["user_id"], campaign_id)

                logger.info("[%d/%d] Sending approved awareness exercise to recipient_id=%s", i, len(users), user["user_id"])
                if send_message(driver, phone, message):
                    dispatched += 1
                    try:
                        log_action("system", "add", "send")
                    except Exception:
                        pass
                time.sleep(5.0)  # conservative pacing for an approved, explicitly scoped exercise

        logger.info("[SUMMARY] Attempted: %d, Dispatched: %d", len(users), dispatched)
        record_audit("complete", campaign_id, approval, dispatched, detail=f"attempted={len(users)}")
        logger.info("All messages have been processed.")
    finally:
        global _DRIVER_SINGLETON
        try:
            if not keep_open:
                if _DRIVER_SINGLETON is driver:
                    _DRIVER_SINGLETON = None
                driver.quit()
                logger.info("Chrome session closed.")
            else:
                _DRIVER_SINGLETON = driver  # keep cached for next run
                logger.info("Keeping Chrome session open (keep_open=True). Close it manually when done.")
        except Exception as e:
            logger.warning(f"Failed to close Chrome cleanly: {e}")


if __name__ == "__main__":
    print("Start the desktop application to review a campaign's authorized recipient scope.")
    print("Direct execution does not dispatch any messages.")
