from aiohttp import (
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    BasicAuth
)
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from urllib.parse import urlencode
from datetime import datetime
from colorama import *
import asyncio, random, string, json, re, os, pytz

wib = pytz.timezone('Asia/Jakarta')

class Mytier:
    def __init__(self) -> None:
        self.BASE_API = "https://mytier.io"
        self.MAIL_API = "https://api.mail.tm"
        self.SITE_KEY = "6LcsN4krAAAAACAufUk4hzfz7DvEOdE2YtDBp8lO"
        self.CAPTCHA_KEY = None
        # reCAPTCHA v3 tuning (override via env):
        self.RECAPTCHA_ACTION = os.getenv("RECAPTCHA_ACTION", "submit")
        self.RECAPTCHA_PAGEURL = os.getenv("RECAPTCHA_PAGEURL", self.BASE_API)
        self.RECAPTCHA_MINSCORE = os.getenv("RECAPTCHA_MINSCORE", "0.5")
        self.RECAPTCHA_ENTERPRISE = os.getenv("RECAPTCHA_ENTERPRISE", "0")
        # Account pacing to avoid 429
        self.ACC_DELAY_MIN = int(os.getenv("ACC_DELAY_MIN", "2"))
        self.ACC_DELAY_MAX = int(os.getenv("ACC_DELAY_MAX", "5"))
        self.HEADERS = {}
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.header_cookies = {}

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def log_status(self, action, status, message="", error=None):
        if status == "success":
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Action :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {action} {Style.RESET_ALL}"
                f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}"
                f"{(Fore.MAGENTA+Style.BRIGHT + '- ' + Style.RESET_ALL + Fore.WHITE+Style.BRIGHT + message + Style.RESET_ALL) if message else ''}"
            )
        elif status == "failed":
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Action :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {action} {Style.RESET_ALL}"
                f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Failed {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(error)} {Style.RESET_ALL}"
            )
        elif status == "retry":
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Action :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {action} {Style.RESET_ALL}"
                f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} Retrying {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {message} {Style.RESET_ALL}"
            )
        elif status == "info":
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Action :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {action} {Style.RESET_ALL}"
                f"{Fore.CYAN+Style.BRIGHT}Status :{Style.RESET_ALL}"
                f"{Fore.BLUE+Style.BRIGHT} Info {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {message} {Style.RESET_ALL}"
            )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}Mytier {Fore.BLUE + Style.BRIGHT}Auto Ref BOT
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Rey? {Fore.YELLOW + Style.BRIGHT}<INI WATERMARK>
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    def load_sctg_key(self):
        # Prefer env var, fallback to sctg_key.txt
        key = os.getenv("SCTG_KEY")
        if key:
            return key.strip()
        try:
            with open("sctg_key.txt", 'r') as file:
                captcha_key = file.read().strip()
            return captcha_key
        except Exception:
            return None

    def save_accounts(self, new_accounts):
        filename = "refs.json"
        try:
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                with open(filename, 'r') as file:
                    existing_accounts = json.load(file)
            else:
                existing_accounts = []

            account_dict = {acc["username"]: acc for acc in existing_accounts}

            for new_acc in new_accounts:
                account_dict[new_acc["username"]] = new_acc

            updated_accounts = list(account_dict.values())

            with open(filename, 'w') as file:
                json.dump(updated_accounts, file, indent=4)

            self.log_status("Save accounts", "success", "accounts saved to file")

        except Exception as e:
            self.log_status("Save accounts", "failed", error=e)
            return []

    async def load_proxies(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]

            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )

        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None

        if proxy.startswith("socks"):
            connector = ProxyConnector.from_url(proxy)
            return connector, None, None

        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                username, password, host_port = match.groups()
                clean_url = f"http://{host_port}"
                auth = BasicAuth(username, password)
                return None, clean_url, auth
            else:
                return None, proxy, None

        raise Exception("Unsupported Proxy Type.")

    def validate_password(self, password: str):
        errors = []
        if len(password) < 10:
            errors.append("must be at least 10 characters long")
        if not re.search(r'[A-Z]', password):
            errors.append("must contain at least one uppercase letter (A-Z)")        if not re.search(r'[a-z]', password):
            errors.append("must contain at least one lowercase letter (a-z)")        if not re.search(r'\d', password):
            errors.append("must contain at least one number (0-9)")
        if not re.search(r'[^A-Za-z0-9]', password):
            errors.append("must contain at least one special character (e.g. !@#$%^&*)")
        return (len(errors) == 0, errors)

    def generate_username(self, min_len=8, max_len=10, digits_count=2, lowercase=True):
        vowels = "aeiou"
        consonants = "".join(c for c in string.ascii_lowercase if c not in vowels)
        letters_v = vowels if lowercase else vowels + vowels.upper()
        letters_c = consonants if lowercase else consonants + consonants.upper()

        if min_len < digits_count + 2:
            raise ValueError("Panjang minimal terlalu kecil.")

        length = random.randint(min_len, max_len)
        letters_len = length - digits_count

        chars = []
        for i in range(letters_len):
            if i % 2 == 0:
                chars.append(random.choice(letters_c))
            else:
                chars.append(random.choice(letters_v))

        digits = [random.choice(string.digits) for _ in range(digits_count)]
        return "".join(chars) + "".join(digits)

    def generate_random_country_id(self):
        return random.choice([
            "ID", "US", "GB", "CA", "AU", "DE", "FR", "IT", "ES", "NL",
            "BE", "CH", "AT", "SE", "NO", "DK", "FI", "NZ", "JP", "KR",
            "CN", "IN", "PK", "BD", "LK", "MY", "SG", "PH", "TH", "VN",
            "RU", "UA", "PL", "CZ", "HU", "RO", "BG", "GR", "TR", "SA",
            "AE", "EG", "ZA", "NG", "KE", "TZ", "GH", "AR", "BR"
        ])

    def mask_account(self, account):
        if "@" in account:
            local, domain = account.split('@', 1)
            mask_account = local[:3] + '*' * 3 + local[-3:]
            return f"{mask_account}@{domain}"

    def print_question(self):
        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. Run With Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Run Without Proxy{Style.RESET_ALL}")
                proxy_choice = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1/2] -> {Style.RESET_ALL}").strip())

                if proxy_choice in [1, 2]:
                    proxy_type = (
                        "With" if proxy_choice == 1 else
                        "Without"
                    )
                    print(f"{Fore.GREEN + Style.BRIGHT}Run {proxy_type} Proxy Selected.{Style.RESET_ALL}")
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Please enter either 1 or 2.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1 or 2).{Style.RESET_ALL}")

        rotate_proxy = False
        if proxy_choice == 1:
            while True:
                rotate_proxy = input(f"{Fore.BLUE + Style.BRIGHT}Rotate Invalid Proxy? [y/n] -> {Style.RESET_ALL}").strip()

                if rotate_proxy in ["y", "n"]:
                    rotate_proxy = rotate_proxy == "y"
                    break
                else:
                    print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")

        return proxy_choice, rotate_proxy

    async def solve_recaptcha(self, site_key: str, page_url: str = None, action: str = None, min_score: float = None, retries=5):
        """Solve Google reCAPTCHA v3 using SCTG API (2captcha-compatible endpoints).

        - in.php with method=userrecaptcha, version=v3, action, min_score
        - res.php polling until token ready
        Returns the g-recaptcha-response token on success.
        """
        in_url = "https://api.sctg.xyz/in.php"
        res_url = "https://api.sctg.xyz/res.php"
        page = page_url or self.RECAPTCHA_PAGEURL
        act = action or self.RECAPTCHA_ACTION
        score = str(min_score if min_score is not None else float(self.RECAPTCHA_MINSCORE))
        enterprise = self.RECAPTCHA_ENTERPRISE

        for attempt in range(retries):
            try:
                if not self.CAPTCHA_KEY:
                    self.log_status("Recaptcha", "failed", error="SCTG key missing. Set SCTG_KEY or sctg_key.txt")
                    return None

                async with ClientSession(timeout=ClientTimeout(total=60)) as session:
                    # Create task (v3)
                    form_v3 = {
                        "key": self.CAPTCHA_KEY,
                        "method": "userrecaptcha",
                        "googlekey": site_key,
                        "pageurl": page,
                        "version": "v3",
                        "action": act,
                        "min_score": score,
                    }
                    if enterprise == "1":
                        form_v3["enterprise"] = "1"
                    async with session.post(in_url, data=form_v3) as resp:
                        resp.raise_for_status()
                        text_v3 = await resp.text()

                    task_id = None
                    if "|" in text_v3:
                        _, task_id = text_v3.split("|", 1)
                        self.log_status("Recaptcha", "success", f"Task(v3) Id: {task_id}")
                    else:
                        # Fallback to v2 invisible if v3 creation failed
                        self.log_status("Recaptcha", "info", f"v3 create failed: {text_v3}. Trying v2 invisible...")
                        form_v2inv = {
                            "key": self.CAPTCHA_KEY,
                            "method": "userrecaptcha",
                            "googlekey": site_key,
                            "pageurl": page,
                            "invisible": "1",
                        }
                        if enterprise == "1":
                            form_v2inv["enterprise"] = "1"
                        async with session.post(in_url, data=form_v2inv) as resp2:
                            resp2.raise_for_status()
                            text_v2 = await resp2.text()
                        if "|" not in text_v2:
                            self.log_status("Recaptcha", "failed", error=f"Create task v2 invisible failed: {text_v2} | page={page}")
                            await asyncio.sleep(5)
                            continue
                        _, task_id = text_v2.split("|", 1)
                        self.log_status("Recaptcha", "success", f"Task(v2inv) Id: {task_id}")

                    # Poll for result
                    for _ in range(90):
                        await asyncio.sleep(2)
                        async with session.get(f"{res_url}?key={self.CAPTCHA_KEY}&id={task_id}") as res:
                            res.raise_for_status()
                            body = await res.text()
                        if body == "CAPCHA_NOT_READY":
                            continue
                        if "|" not in body:
                            self.log_status("Recaptcha", "failed", error=f"Solve failed: {body} | page={page} action={act} score={score} enterprise={enterprise}")
                            break
                        _, token = body.split("|", 1)
                        self.log_status("Recaptcha", "success", "Solved Successfully")
                        return token

                # If polling loop didn't return, retry
                if attempt < retries - 1:
                    self.log_status("Recaptcha", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    return None

            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Recaptcha", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Recaptcha", "failed", error=e)
                    return None

    async def check_connection(self, proxy_url=None):
        try:
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get(url="https://api.ipify.org?format=json", proxy=proxy, proxy_auth=proxy_auth) as response:
                    self.log_status("Check Connection", "success", "Connection OK")
                    return True
        except (Exception, ClientResponseError) as e:
            self.log_status("Check Connection", "failed", error=e)
            return None

    async def get_domain(self, proxy_url=None):
        url = f"{self.MAIL_API}/domains"
        try:
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                async with session.get(url=url, proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    result = await response.json()
                    domain = result["hydra:member"][0]["domain"]
                    self.log_status("Temp Mail", "success", f"GET Domain Success, Domain: {domain}")
                    return domain
        except (Exception, ClientResponseError) as e:
            self.log_status("Temp Mail", "failed", f"GET Domain Failed: {e}")            return None

    async def create_temp_email(self, email: str, password: str, proxy_url=None):
        url = f"{self.MAIL_API}/accounts"
        data = json.dumps({"address":email, "password":password})
        headers = {"Content-Type": "application/json"}
        try:
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    self.log_status("Temp Mail", "success", f"Create Temp Mail Success, Email: {self.mask_account(email)}")
                    return True
        except (Exception, ClientResponseError) as e:
            self.log_status("Temp Mail", "failed", f"Create Temp Mail Failed: {e}")
            return None

    async def get_token_email(self, email: str, password: str, proxy_url=None):
        url = f"{self.MAIL_API}/token"
        data = json.dumps({"address":email, "password":password})
        headers = {"Content-Type": "application/json"}
        try:
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    result = await response.json()
                    token = result["token"]
                    self.log_status("Temp Mail", "success", f"GET Token Email Success")
                    return token
        except (Exception, ClientResponseError) as e:
            self.log_status("Temp Mail", "failed", f"GET Token Email Failed: {e}")
            return None

    async def wait_for_verification_email(self, token: str, proxy_url=None, retries=100):
        headers = {"Authorization": f"Bearer {token}"}
        try:
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                for attempt in range(1, retries):
                    await asyncio.sleep(3)

                    inbox_url = f"{self.MAIL_API}/messages"
                    async with session.get(url=inbox_url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        result = await response.json()
                        for msg in result["hydra:member"]:
                            if msg["from"]["address"] == "support@mytier.io":                                msg_id = msg["id"]
                                self.log_status("Check Inbox", "success", "Email Verification Found")

                                message_url = f"{self.MAIL_API}/messages/{msg_id}"
                                async with session.get(url=message_url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as resp_detail:
                                    resp_detail.raise_for_status()
                                    detail = await resp_detail.json()
                                    text = detail.get("text", "")
                                    html = " ".join(detail.get("html", []))

                                    combined = text + "\n" + html

                                    match = re.search(r"https:\/\/mytier\.io\/service\/auth\/verify\?token=([\w\-._~]+)", combined)
                                    if match:
                                        token = match.group(1)
                                        self.log_status("Verification", "success", f"Token: {token[:20]}...")
                                        return token

                    self.log_status("Check Inbox", "retry", f"Attempt {attempt}/{retries}")
                    continue
        except (Exception, ClientResponseError) as e:
            self.log_status("Check Inbox", "failed", error=e)
            return None

    async def user_signup(self, idx: int, nickname: str, password: str, email: str, country_id: str, recaptcha_token: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/api/signup"
        data = json.dumps({
            "nickname": nickname,
            "password": password,
            "email": email,
            "referral": self.REF_CODE,
            "age": 19,
            "country": country_id,
            "uuid": "web",
            "recaptchaToken": recaptcha_token
        })
        headers = {
            **self.HEADERS[idx],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        if response.status == 429:
                            retry_after = response.headers.get("Retry-After")                            try:
                                wait_s = int(retry_after) if retry_after else 5
                            except Exception:
                                wait_s = 5
                            jitter = random.randint(1, 3)
                            self.log_status("Signup", "retry", f"429 rate limited. Waiting {wait_s + jitter}s")
                            await asyncio.sleep(wait_s + jitter)
                            continue
                        response.raise_for_status()
                        self.log_status("Signup", "success", "Signup successfully")
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Signup", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Signup", "failed", error=e)
                    return None

    async def user_login(self, idx: int, nickname: str, password: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/api/login"
        data = urlencode({"nickname":nickname, "password":password, "os":"web"})
        headers = {
            **self.HEADERS[idx],
            "Content-Length": str(len(data)),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        self.log_status("Login", "success", "Login successfully")
                        result = await response.text()
                        return { "token": result }
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Login", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Login", "failed", error=e)
                    return None

    async def send_verification(self, idx: int, nickname: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/api/resend-verification"
        data = json.dumps({"nickname":nickname})
        headers = {
            **self.HEADERS[idx],
            "Content-Length": str(len(data)),
            "Content-Type": "application/json",
            "Cookie": self.header_cookies[nickname]
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, data=data, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        self.log_status("Request Verification", "success", "Verification requested successfully")
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Request Verification", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Request Verification", "failed", error=e)
                    return None

    async def complete_verification(self, idx: int, nickname: str, token_verfification: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/api/verify-email?token={token_verfification}"        headers = {
            **self.HEADERS[idx],
            "Content-Length": "0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": self.header_cookies[nickname]
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        result = await response.text()
                        if result.strip() == "Email verified successfully":
                            self.log_status("Verification", "success", result)
                            return True

                        self.log_status("Verification", "failed", result)
                        return False
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Verification", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Verification", "failed", error=e)
                    return None

    async def user_dashboard(self, idx: int, nickname: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/api/dashboard"
        headers = {
            **self.HEADERS[idx],
            "Content-Length": "0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": self.header_cookies[nickname]
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        result = await response.json()
                        balance = result.get("balance", 0)
                        self.log_status("Dashboard", "info", f"Balance: {balance} MT")
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Dashboard", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Dashboard", "failed", error=e)
                    return None

    async def attendence_check(self, idx: int, nickname: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/api/event_attendance_check"
        headers = {
            **self.HEADERS[idx],
            "Content-Length": "0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": self.header_cookies[nickname]
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        self.log_status("Check-In", "success", "Claimed Successfully")
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Check-In", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Check-In", "failed", error=e)
                    return None

    async def start_mining(self, idx: int, nickname: str, proxy_url=None, retries=5):
        url = f"{self.BASE_API}/api/mining"
        headers = {
            **self.HEADERS[idx],
            "Content-Length": "0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": self.header_cookies[nickname]
        }
        for attempt in range(retries):
            connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as response:
                        response.raise_for_status()
                        self.log_status("Mining", "success", "Started Successfully")
                        return await response.json()
            except (Exception, ClientResponseError) as e:
                if attempt < retries - 1:
                    self.log_status("Mining", "retry", f"Attempt {attempt + 1}/{retries}")
                    await asyncio.sleep(5)
                    continue
                else:
                    self.log_status("Mining", "failed", error=e)
                    return None

    async def process_check_connection(self, idx: int, use_proxy: bool, rotate_proxy: bool):
        while True:
            proxy = self.get_next_proxy_for_account(idx) if use_proxy else None
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Proxy  :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {proxy if proxy else 'No Proxy'} {Style.RESET_ALL}"
            )

            is_valid = await self.check_connection(proxy)
            if is_valid: return True

            if rotate_proxy:
                proxy = self.rotate_proxy_for_account(idx)
                await asyncio.sleep(1)
                continue

            return False

    async def process_accounts(self, idx: int, use_proxy: bool, rotate_proxy: bool):
        is_valid = await self.process_check_connection(idx, use_proxy, rotate_proxy)
        if is_valid:
            proxy = self.get_next_proxy_for_account(idx) if use_proxy else None

            nickname = self.generate_username()
            country_id = self.generate_random_country_id()

            domain = await self.get_domain(proxy)
            if not domain: return False

            email = f"{nickname}@{domain}"

            create = await self.create_temp_email(email, self.PASSWORD, proxy)
            if not create: return False

            token = await self.get_token_email(email, self.PASSWORD, proxy)
            if not token: return False

            recaptcha_token = await self.solve_recaptcha(self.SITE_KEY)
            if not recaptcha_token: return False

            signup = await self.user_signup(idx, nickname, self.PASSWORD, email, country_id, recaptcha_token, proxy)
            if not signup: return False

            login = await self.user_login(idx, nickname, self.PASSWORD, proxy)
            if not login: return False

            self.header_cookies[nickname] = f"uid_tt={login['token']}"

            send = await self.send_verification(idx, nickname, proxy)
            if not send: return False

            token_verfification = await self.wait_for_verification_email(token, proxy)
            if not token_verfification: return False

            complete = await self.complete_verification(idx, nickname, token_verfification, proxy)
            if not complete: return False

            await self.user_dashboard(idx, nickname, proxy)
            await self.attendence_check(idx, nickname, proxy)
            await self.start_mining(idx, nickname, proxy)

            account_data = [{"username":nickname, "email":email, "password":self.PASSWORD}]
            self.save_accounts(account_data)
            self.log_status("Process Account", "success", f"Account {self.mask_account(email)} processed successfully")

            return True

    async def main(self):
        try:
            ref_counts = int(input(f"{Fore.BLUE + Style.BRIGHT}Enter Ref Count -> {Style.RESET_ALL}"))

            self.REF_CODE = str(input(f"{Fore.BLUE + Style.BRIGHT}Enter Ref Code -> {Style.RESET_ALL}")).strip().lower()

            while True:
                password = str(input(f"{Fore.BLUE + Style.BRIGHT}Enter Password -> {Style.RESET_ALL}")).strip()
                valid, problems = self.validate_password(password)
                if valid:
                    self.PASSWORD = password
                    break
                else:
                    print(Fore.RED + Style.BRIGHT + "\nInvalid password. Please fix the following:" + Style.RESET_ALL)
                    for p in problems:
                        print(f"  - {p}")
                    print()

            captcha_key = self.load_sctg_key()
            if captcha_key: self.CAPTCHA_KEY = captcha_key

            proxy_choice, rotate_proxy = self.print_question()

            self.clear_terminal()
            self.welcome()

            use_proxy = True if proxy_choice == 1 else False
            if use_proxy:
                await self.load_proxies()

            success = 0
            failed = 0

            separator = "=" * 25
            for idx in range(ref_counts):
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT} {idx+1} {Style.RESET_ALL}"
                    f"{Fore.CYAN + Style.BRIGHT}Of{Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT} {ref_counts} {Style.RESET_ALL}"
                    f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}"
                )

                self.HEADERS[idx] = {
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",                    "Connection": "keep-alive",
                    "Host": "mytier.io",
                    "Origin": "https://mytier.io",
                    "Referrer": "https://mytier.io/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "User-Agent": FakeUserAgent().random
                }

                process = await self.process_accounts(idx, use_proxy, rotate_proxy)
                if process: success += 1
                else: failed += 1

                self.log_status("Main Process", "info", f"Success: {success} - Failed: {failed}")

                await asyncio.sleep(random.randint(self.ACC_DELAY_MIN, self.ACC_DELAY_MAX))

        except Exception as e:
            self.log_status("Main Process", "failed", error=e)
            raise e

if __name__ == "__main__":
    try:
        bot = Mytier()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Mytier - BOT{Style.RESET_ALL}                                       "
        )
