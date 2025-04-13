import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Actions
from DrissionPage.common import Settings
from PySide6.QtCore import Signal, QObject, QTimer
from requests.exceptions import SSLError, ConnectionError

# 线程池最大线程数，可根据机器和网络情况调节
MAX_WORKERS = 5

# 目标网址
URL = 'https://partner.us.tiktokshop.com/affiliate-cmp/creator?market=100'
COOKIES_FILE = 'cookies.txt'
CREATORS_FILE = 'processed_creators.txt'  # 保存已处理的 nickname

find_creators = []


DOWNLOADED_FILE = 'downloaded_videos.txt'

def load_downloaded_urls():
    """加载已下载的视频 URL"""
    if not os.path.exists(DOWNLOADED_FILE):
        return set()
    with open(DOWNLOADED_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f.readlines())

def save_downloaded_url(url):
    """保存已下载的视频 URL"""
    with open(DOWNLOADED_FILE, 'a', encoding='utf-8') as f:
        f.write(url + '\n')

downloaded_urls = load_downloaded_urls()  # 在开始前读取

# 设置保存目录
SAVE_DIR = 'downloads'
os.makedirs(SAVE_DIR, exist_ok=True)


import hashlib

def url_to_filename(url):
    # 使用 MD5 摘要算法，输出是固定 32 字符
    md5_hash = hashlib.md5(url.encode()).hexdigest()
    return f'{md5_hash}.mp4'


# 下载函数
# def download_file(url, path):
#     import requests
#     print(f"开始下载: {url}")
#     response = requests.get(url, stream=True)
#     with open(path, 'wb') as f:
#         for chunk in response.iter_content(chunk_size=8192):
#             if chunk:
#                 f.write(chunk)
#     print(f"完成下载: {url}")

# 用于多线程下载的任务封装
def download_task(video_src, user_id):
    try:
        # print('video_src=', video_src)
        # filename = os.path.join(SAVE_DIR, video_src[-19:] + '.mp4')
        print('filename=', user_id+'.mp4')
        filename = os.path.join(SAVE_DIR, user_id + '.mp4')
        download_file(video_src, filename)
    except Exception as e:
        print(f"下载失败 {video_src}, 错误: {e}")


# 获取视频链接（这个部分你是串行爬取页面，只提取视频链接，不下载）
def extract_video_src(page, video_page_url):
    page.get(video_page_url)
    page.wait.load_start()
    video_ele = page.ele('.xg-video-container')
    for source in video_ele.child().children():
        video_src = source.attr('src')
        if video_src and 'https://www.douyin.com/aweme/v1/play/?file_id' in video_src:
            return video_src
    return None


# 获取视频真实地址
def get_video_url(page, video_page_url, executor):
    page.get(video_page_url)
    page.wait.load_start()


    video_ele = page.ele('.xg-video-container')
    # print('video_ele=', video_ele)
    # print(video_ele.child().children())

    for source in video_ele.child().children():
        video_src = source.attr('src')
        # print(video_src)

        # # if 'https://www.douyin.com/aweme/v1/play/' in video_src:
        # try:
        #     download_file(video_src, os.path.join(SAVE_DIR, video_src[-19:]+'.mp4'))
        #     break
        # except Exception as e:
        #     print('e=', e)

        if video_src and 'https://www.douyin.com/aweme/v1/play/?file_id' in video_src:
            print('video_src=', video_src)

            executor.submit(download_task, video_src)
            break  # 如果你只想下载第一个，保留 break


def convert_cookies(cookie_list):
    return '; '.join(
        f"{cookie['name']}={cookie['value']}"
        for cookie in cookie_list
        if cookie.get('name') and cookie.get('value')
    )

def thread_get_video_url(main_page, video_page_url, self_content, idx):
    print('video_page_url=', video_page_url)

    match = re.search(r'/video/([a-zA-Z0-9\-_]+)', video_page_url)
    user_id = ''
    if match:
        user_id = match.group(1)
        print(user_id)

    page = main_page.new_tab()
    page.listen.start('/aweme/detail')

    # # 设置监听请求完成的钩子函数
    # def hook_response(request):
    #     print('request.url=', request.url)
    #     # 可以判断 URL 是否是我们感兴趣的 GET 请求
    #     if '/aweme/detail' in request.url:
    #         print("监听到请求：", request.url)
    #         print("返回内容：", request.response_body)
    #
    # page.set_hooks(hook_response)

    page.get(video_page_url)
    page.wait.load_start()

    packet_url = ''
    for packet in page.listen.steps():
        print(packet)  # 打印数据包url
        if packet:
            packet_url = packet.url
            break

    # print('packet_url=', packet_url)
    for _ in range(1):
        if packet_url:
            cookies = page.cookies()  # 这是一个 dict 格式的 cookies
            user_agent = page.user_agent
            # print('get packet_url=', packet_url, cookies)
            cookie_header = convert_cookies(cookies)
            headers = {
                "Cookie": cookie_header,
                "User-Agent": user_agent,
                # 'Cookie': 'live_use_vvc=%22false%22; __live_version__=%221.1.2.67%22; UIFID_TEMP=9e5c45806baed1121aef2e4ebdb50ae0783a7b9267143d29acaade7dde1bacd5f9a2b4862b202118c9c624900e00a404aafaf961511ed5db1a4642c9a5690b626618ed292075ecdd12216e8a56103fb6; hevc_supported=true; fpk1=U2FsdGVkX19AJq/4rXqQWlrcDUF/aOZpbvF9v37D65FkaHRar/QrdJy66ni2P0XkGPIULF8V59Tf2VOFHItihA==; fpk2=fe0673f2a48d047b912b27e2a0c02f9f; passport_csrf_token=876d547622eb7b203e3ca93771426c27; passport_csrf_token_default=876d547622eb7b203e3ca93771426c27; __security_mc_1_s_sdk_crypt_sdk=4f7a2968-4d88-83e7; bd_ticket_guard_client_web_domain=2; passport_assist_user=CkAL7PVa9ThoGODgEtXB8-nx2BYQ-Yun0lbLFcFdnjKhlzKQx1_tcyHB6Aa-rZRQ_EkUhSj4MFvhPqS0tDz00OjcGkoKPAAAAAAAAAAAAABOwqCXje-2tspekCsn5B1mvjl-m6vOb9UB4Qy-B-HVXadHZEgQ9w848ZvVIfqFJePIzRDciOwNGImv1lQgASIBA2KWZjg%3D; n_mh=Ba2PAf43MAeQFn6Vi4P43NmdmWdL7RBO5gOuwUAFmc8; uid_tt=f086d9487a1bc418dcbb2c1f612703e9; uid_tt_ss=f086d9487a1bc418dcbb2c1f612703e9; sid_tt=9bd1bedb9f9148fe42e1b249ad7f3ffe; sessionid=9bd1bedb9f9148fe42e1b249ad7f3ffe; sessionid_ss=9bd1bedb9f9148fe42e1b249ad7f3ffe; is_staff_user=false; store-region=cn-hk; store-region-src=uid; login_time=1742020687214; SelfTabRedDotControl=%5B%5D; _bd_ticket_crypt_cookie=1ca0d98faa6560781eefc3155a758a41; __security_mc_1_s_sdk_sign_data_key_web_protect=de5e356e-4387-a317; __security_mc_1_s_sdk_cert_key=0da4bd3e-4c64-8161; __security_server_data_status=1; xgplayer_device_id=20335665188; xgplayer_user_id=477586564266; UIFID=9e5c45806baed1121aef2e4ebdb50ae0783a7b9267143d29acaade7dde1bacd5d61cdbe7beef0abcaaea16f8d976a2a8f52aa499d0f862c437bd766d76c5218abbb8ed9c0ef6794d63f3a1b1b4633f92cd08ad79abc546cd7830f429f4546f8757ca7b550e5d3f0d91226d33c63ae5fce99f8f679c6354c85c2f8868004f6a6952898dd4841f6510a3a50816ba9e211eb93bee8e7d38406399aad6e52a06dd99; s_v_web_id=verify_m89uc1lz_WdPN3R70_5kJV_44MZ_8HRX_YuknWblmswQr; ttwid=1%7Ctq_qeMzRgBT9O1lUWEvmeVK-b9_5E0sGlWIY4XrM_mU%7C1743129453%7Cbc97308484c5a5b1b2887e15428741ac7979c57230855700edb45d1ca38d1c1d; dy_swidth=2048; dy_sheight=1280; sid_guard=9bd1bedb9f9148fe42e1b249ad7f3ffe%7C1744090219%7C5184000%7CSat%2C+07-Jun-2025+05%3A30%3A19+GMT; sid_ucp_v1=1.0.0-KGE1ZDVkN2M1ZTA5NzQyOTU5NmI5MmQwMmIzMzY3NjQ0NTRhYTk1YzcKIAj46ICnoYxIEOvo0r8GGO8xIAwwytqUgQY4B0D0B0gEGgJsZiIgOWJkMWJlZGI5ZjkxNDhmZTQyZTFiMjQ5YWQ3ZjNmZmU; ssid_ucp_v1=1.0.0-KGE1ZDVkN2M1ZTA5NzQyOTU5NmI5MmQwMmIzMzY3NjQ0NTRhYTk1YzcKIAj46ICnoYxIEOvo0r8GGO8xIAwwytqUgQY4B0D0B0gEGgJsZiIgOWJkMWJlZGI5ZjkxNDhmZTQyZTFiMjQ5YWQ3ZjNmZmU; is_dash_user=1; my_rd=2; publish_badge_show_info=%221%2C0%2C0%2C1744090218160%22; SearchMultiColumnLandingAbVer=1; SEARCH_RESULT_LIST_TYPE=%22multi%22; download_guide=%223%2F20250411%2F0%22; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.975%7D; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAkB50PwS9Hu9fSVe1HakAYJAOypwguJBy__Mrz6_oCR0%2F1744387200000%2F0%2F1744370224859%2F0%22; WallpaperGuide=%7B%22showTime%22%3A1744379968743%2C%22closeTime%22%3A0%2C%22showCount%22%3A2%2C%22cursor1%22%3A16%2C%22cursor2%22%3A4%7D; SearchSingleColumnExitCount=0; csrf_session_id=fd42e4edb48beccd2a21c0c59382942d; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAkB50PwS9Hu9fSVe1HakAYJAOypwguJBy__Mrz6_oCR0%2F1744560000000%2F0%2F1744532758645%2F0%22; douyin.com; xg_device_score=7.658235294117647; device_web_cpu_core=8; device_web_memory_size=8; strategyABtestKey=%221744532764.08%22; biz_trace_id=74bc779e; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2048%2C%5C%22screen_height%5C%22%3A1280%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A8%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A100%7D%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCRjUrbzYzdkpOSW95UXNIOUIxMjR2blNva21GTlhxdkM4Z2xFbjFzT1lVWkFKUUlaeXVmY1kxNFlRdFRFbFhtRWl5MVFkakRGbHRvZlpxK3NGRFBYWm89IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; home_can_add_dy_2_desktop=%221%22; odin_tt=5760da957424470ae5b9f8e58e785bd5fb157ce4289619e66f03b29b9bee6cf72cc5eccfc5d34d4c4630d544b0acfb89a12465c389c9e5417aea2d37c23f1014; IsDouyinActive=false; passport_fe_beating_status=false; __ac_nonce=067fba1bb0070c3bbd18; __ac_signature=_02B4Z6wo00f01ZfBA9wAAIDBcMFUyednGVWX4QdAAAIM9EcXqlA1P9BBTyDZ6638Vp3nVvWSKIS4Rld2u9zv0KiqT2dBTH0J4b4ogJFJzcuq2vYmzqcjPvI-TbAxvdY8Izo-YeHr-Gyw16Ho85',
                # 'Cookie': 'bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTlU2VzVnQ0c1N3kreVFLbmdjYXhucW1jWjBjVXdLaW5yeTVMUU82Z2N6WDIzeW5Ra1hvWG1HVTR1S0Q5Q2lzeFZYdUY1ZHRyQ3FBalMrTXE3SjNOYUU9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2048%2C%5C%22screen_height%5C%22%3A1280%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A8%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A2.55%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; IsDouyinActive=true; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAkB50PwS9Hu9fSVe1HakAYJAOypwguJBy__Mrz6_oCR0%2F1744387200000%2F0%2F0%2F1744376192313%22; xg_device_score=7.425841170280904; __ac_nonce=067f90aec000af3a5ade; my_rd=2; passport_fe_beating_status=true; xgplayer_device_id=61116896565; strategyABtestKey=%221744305466.568%22; h265ErrorNum=-1; live_can_add_dy_2_desktop=%221%22; __security_server_data_status=1; __security_mc_1_s_sdk_cert_key=0a080fbf-4e06-b018; __security_mc_1_s_sdk_sign_data_key_web_protect=f4599d29-4cf0-ac73; _bd_ticket_crypt_cookie=ae80e3e2d371ae6ac71053b902e12c31; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; SelfTabRedDotControl=%5B%5D; live_use_vvc=%22false%22; login_time=1744087323538; fpk2=b977e10d1cb26107909e97d51a688323; ssid_ucp_v1=1.0.0-KGFhZjJjZGE0NDU5OGRlOGY4YjEzMjUyMGIwZjZhNWE0ZDhkNGZmZmUKIAj46ICnoYxIEJvS0r8GGO8xIAwwytqUgQY4B0D0B0gEGgJsZiIgYjg2N2JiZDcyMGNmODhhNzUyNDcwMDExMDNhNDYxMGM; sid_ucp_v1=1.0.0-KGFhZjJjZGE0NDU5OGRlOGY4YjEzMjUyMGIwZjZhNWE0ZDhkNGZmZmUKIAj46ICnoYxIEJvS0r8GGO8xIAwwytqUgQY4B0D0B0gEGgJsZiIgYjg2N2JiZDcyMGNmODhhNzUyNDcwMDExMDNhNDYxMGM; publish_badge_show_info=%220%2C0%2C0%2C1744375657200%22; pwa2=%220%7C0%7C1%7C0%22; __live_version__=%221.1.3.363%22; sessionid_ss=b867bbd720cf88a75247001103a4610c; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Atrue%2C%22volume%22%3A0.5%7D; device_web_memory_size=8; sessionid=b867bbd720cf88a75247001103a4610c; n_mh=Ba2PAf43MAeQFn6Vi4P43NmdmWdL7RBO5gOuwUAFmc8; uid_tt=a9e7cbbd5a14280f8365d8418d9ca016; is_dash_user=1; UIFID=37c879f32637ebc5496b02d59029bbf7616da5849e10d44e1e2ee2dac28cdd6b8d4e9ce70295e9420e5ae08ca3b3b1932a01f6976acdc6dbaa5711e293fb6d284a701d8bfc4ec22a9dcbf3a67664b00dd70b14ff00d90fa7d20f1cb5daf2df382babf318cadf4c8073e18b06534c5fd254070233c49165406d974e4263962d8b74502545ebd8979d2fcb74589d81b862ed0a32f6a9eba40a286005c52f4d11c7; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%2C%22isForcePopClose%22%3A1%7D; passport_csrf_token=f5d2daf1827a787cca47305859d61a9b; sid_guard=b867bbd720cf88a75247001103a4610c%7C1744087323%7C5184000%7CSat%2C+07-Jun-2025+04%3A42%3A03+GMT; device_web_cpu_core=8; passport_csrf_token_default=f5d2daf1827a787cca47305859d61a9b; home_can_add_dy_2_desktop=%221%22; bd_ticket_guard_client_web_domain=2; uid_tt_ss=a9e7cbbd5a14280f8365d8418d9ca016; dy_sheight=1280; fpk1=U2FsdGVkX1/EZ1ogMd23jFoJKnZBvk7eKdSURT6p+NCQ+9H2rsX0c6dFmQBfJUvzyYXrVF77PLZVJBBdQLLGxQ==; passport_assist_user=CkB6hO2TP0Ty81vfRkZovhMo0OQPOo4O5HY-Kcg03W0AHDlEdNRWuuyv_rPHK1ff1eDEyrho3MMiWyKT29lpkmZ9GkoKPAAAAAAAAAAAAABO2m74vDCt6mucQPTWP851iWbosnSzc9jrqzT5ty2ueSrbR63o2tS1SDB9X89uqnwTxxCMle4NGImv1lQgASIBAySz0uA%3D; hevc_supported=true; is_staff_user=false; UIFID_TEMP=37c879f32637ebc5496b02d59029bbf7616da5849e10d44e1e2ee2dac28cdd6b474d73809d447f84230b3641355330eabafc09772ff3520233731044026998c7cedd75388f4210dbc36214c1891f1b7e; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAkB50PwS9Hu9fSVe1HakAYJAOypwguJBy__Mrz6_oCR0%2F1744387200000%2F1744363231421%2F0%2F1744376792314%22; __ac_signature=_02B4Z6wo00f01dGbTfAAAIDBNpsa5rT6WC3Ru0lAABOh3b; d_ticket=d5e00550c74cf11ab80adb5198149ca42fb79; odin_tt=7f44b722cdbd861170f7c9936470c721e86bb3550b73ddcb5c9189124a3153431764b5db3614ab358e1c80bf770e001cc099228881c8cbb762c2d2a891c558dc; __security_mc_1_s_sdk_crypt_sdk=4dd23c26-4c9e-9017; sid_tt=b867bbd720cf88a75247001103a4610c; xgplayer_user_id=817911049794; passport_mfa_token=CjYkP6is0aFOHhtQNXSkdWRX3uS8Z6C6RV2%2B%2B9jI7D2gs3%2FlTrnhDyR0SPtWHj%2BOhLp0%2BeTs0XgaSgo8AAAAAAAAAAAAAE7aGlFdBHxjh7YludSRpkD32%2BW2EkhLGYv84O78upi5P%2B9P5Y0alMhp7Av%2BMhRmxYocEOaV7g0Y9rHRbCACIgED3Gi6pg%3D%3D; download_guide=%223%2F20250408%2F0%22; s_v_web_id=verify_m980fzb8_i7FkUy72_PP2D_4mt3_AxzN_5KhyVXLn3JJ2; dy_swidth=2048; ttwid=1%7Cbabi7eL9MWadACFLUEvdQkxtY9h1w1nQhJVX04NqZMU%7C1744087123%7C2a234466d847e4dde3c692f828b4746671a19487e977596161b5ba35b93dd428',
                # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
            }
            print('url=', packet_url)
            print('headers=', headers)
            # resp = requests.get(packet_url, headers=headers)
            resp = requests.request("GET", url=packet_url, headers=headers, data={})
            # print(resp)
            print('text=', resp.text)
            # print('json=', resp.json())

            resp_json = resp.json()
            video_add_url = resp_json['aweme_detail']['video']['play_addr']['url_list'][-1]
            self_content.log_signal.emit('🍺开始下载第 ' + str(idx) + ' 个视频')
            download_task(video_add_url, user_id)
            self_content.log_signal.emit('✅完成下载第 ' + str(idx) + ' 个视频')
            page.close()

    # time.sleep(30000)
    #
    # video_ele = page.ele('.xg-video-container')
    #
    # print(video_ele)
    #
    # for source in video_ele.child().children():
    #     video_src = source.attr('src')
    #     print(video_src)
    #
    #     # # if 'https://www.douyin.com/aweme/v1/play/' in video_src:
    #     # try:
    #     #     download_file(video_src, os.path.join(SAVE_DIR, video_src[-19:]+'.mp4'))
    #     #     break
    #     # except Exception as e:
    #     #     print('e=', e)
    #
    #     try:
    #         if video_src:
    #             print('video_src=', video_src)
    #             download_task(video_src, user_id)
    #             page.close()
    #             break  # 如果你只想下载第一个，保留 break
    #     except Exception as e:
    #         print("e=", e)
    #
    # time.sleep(10000)

    # time.sleep(10000)
    # if video_ele:
    #     return video_ele.attr('src')
    # return None





def download_file(url, save_path, max_retries=5, delay=2):
    """
    下载文件，并在遇到 SSL 相关错误时进行重试
    :param url: 文件的下载 URL
    :param save_path: 保存路径
    :param max_retries: 最大重试次数
    :param delay: 每次重试的等待时间（秒）
    """
    attempt = 0
    while attempt < max_retries:
        try:
            print(f"📥 尝试下载: {url} \n (第 {attempt + 1} 次尝试, 最大次数 {max_retries})")
            response = requests.get(url, verify=False, stream=True, timeout=10)  # 禁用 SSL 验证
            response.raise_for_status()  # 检查请求是否成功

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            print(f"✅ 下载成功: {save_path}")
            return True  # 下载成功，退出循环

        except (SSLError, ConnectionError) as e:
            print(f"⚠️ 下载失败: {e}, {delay} 秒后重试...")
            attempt += 1
            time.sleep(delay)

    print(f"❌ 失败超过 {max_retries} 次，跳过此文件: {url}")
    return False  # 超过最大重试次数，返回失败


# 下载视频
def download_video(url, filename, video_id):
    if video_id in downloaded_urls:
        print(f"⏭ 已下载过，跳过: {url}")
        return

    # print('url=', url)
    #
    # time.sleep(10000)

    filename = os.path.join(SAVE_DIR, url_to_filename(url))
    print('filename=', filename)

    if os.path.exists(filename):
        print(f"⚠️ 文件已存在: {filename}")
        return

    success = download_file(url, filename)
    if success:
        save_downloaded_url(video_id)
        downloaded_urls.add(video_id)

    # download_file(url, filename)

    # print(f'开始下载: {filename}')
    # headers = {
    #     'User-Agent': 'Mozilla/5.0',
    #     'Referer': 'https://www.kuaishou.com'
    # }
    # response = requests.get(url, headers=headers, stream=True, verify=False)
    # with open(filename, 'wb') as f:
    #     for chunk in response.iter_content(1024):
    #         f.write(chunk)
    # print(f'下载完成: {filename}')


# 多线程下载逻辑
def start_multithread_download(video_links):
    def worker(i, link):
        print(f'正在处理第 {i + 1} 个视频...')
        video_url = get_video_url('https://www.kuaishou.com/short-video/' + link)
        print(f'video_url={video_url}')
        if video_url:
            filename = os.path.join(SAVE_DIR, f'video_{i + 1}.mp4')
            download_video(video_url, filename)
        else:
            print(f'⚠️ 获取视频地址失败: {link}')

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(worker, i, link) for i, link in enumerate(video_links)]

        # 可选：等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"❌ 线程执行出错: {e}")

    print("✅ 所有视频下载完成（多线程）！")


class Core(QObject):

    log_signal = Signal(str)  # Signal to emit logs

    def __init__(self, /):
        # 设置语言
        super().__init__()
        Settings.set_language('en')
        # 目标标题（请修改为你要找的标题）
        self.target_title = "TikTok Shop"

        # # 总运行次数
        # self.run_total_count = 0
        # # 间隔时间
        # self.run_interval_time = 0
        # # 搜索的关键字
        # self.search_keyword = ''
        # # 发送的内容
        # self.send_content = ''
        #
        # # 运行次数
        # self.run_count = 0
        # # 连接到已打开的浏览器
        # self.browser = Chromium()
        # # 加载已处理的 creators
        # self.find_creators = self.load_processed_creators()

        self.page = None


    def Set_run_total_count(self, count):
        """运行总次数"""
        self.run_total_count = count

    def Set_run_interval_time(self, interval_time):
        self.run_interval_time = interval_time

    def Set_search_keyword(self, search_keyword):
        """搜索的关键字"""
        self.search_keyword = search_keyword

    def Set_send_content(self, send_content):
        """发送的内容"""
        self.send_content = send_content

    def Set_profile_url(self, profile_url):
        self.profile_url = profile_url

    def Init(self):
        self.init_task()

    def Start(self):
        self.log_signal.emit("任务开始...")
        """开始任务"""
        self.start_task()

    def Stop(self):
        """停止任务"""
        pass

    def Close(self):
        self.page.quit()

    def load_processed_creators(self):
        """从本地文件加载已处理的 nickname"""
        if not os.path.exists(CREATORS_FILE):
            return set()

        with open(CREATORS_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f.readlines())

    def save_processed_creator(self, nickname):
        """保存新的 nickname 到本地文件"""
        with open(CREATORS_FILE, 'a', encoding='utf-8') as f:
            f.write(nickname + '\n')
        self.find_creators.add(nickname)

    def load_cookies(self):
        """从文件加载 cookies"""
        if not os.path.exists(COOKIES_FILE):
            return []

        cookies = []
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            for line in f.read().strip().split('; '):
                if '=' in line:
                    name, value = line.split('=', 1)
                    cookies.append({'name': name, 'value': value, 'domain': '.tiktokshop.com', 'path': '/'})
        return cookies

    def save_cookies(self, browser):
        """从浏览器提取最新的 cookies 并保存到文件"""
        cookies = browser.cookies()  # 从浏览器获取 cookies
        if cookies:
            with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
                f.write('; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies]))
            print("Cookies saved successfully!")
        else:
            print("Failed to get cookies!")

    def init_task(self):
        chrome_options = ChromiumOptions()
        # 静音
        chrome_options.mute(True)
        print(chrome_options.is_headless)
        # chrome_options.set_argument('--headless')
        # 启动浏览器
        page = ChromiumPage(addr_or_opts=chrome_options)
        self.page = page
        page.get('https://www.douyin.com')



    def start_task(self):

        # 加载最新 Cookies
        cookies = self.load_cookies()

        chrome_options = ChromiumOptions()
        # if cookies:
        #     print('无痕模式')
        #     # 无痕模式
        #     chrome_options.incognito()
        #     # 无头模式
        #     chrome_options.headless(True)
        #     # 无图
        #     chrome_options.no_imgs(True)
        # 静音
        chrome_options.mute(True)
        print(chrome_options.is_headless)
        # chrome_options.set_argument('--headless')
        self.log_signal.emit("启动浏览器...")
        # 启动浏览器
        page = ChromiumPage(addr_or_opts=chrome_options)
        self.page = page
        page.get('https://www.douyin.com')

        tab = page.get_tabs()[0]

        self.log_signal.emit("加载最新 Cookies...")
        # # 加载最新 Cookies
        # cookies = self.load_cookies()
        if cookies:
            tab.set.cookies(cookies)
            tab.refresh()
        else:
            # # 手动扫码登录快手
            # input("请在浏览器中扫码登录抖音，登录后按回车继续...")
            # self.save_cookies(page)

            self.log_signal.emit("cookies不能为空,重新登录...")
            page.close()
            return

        # self.profile_url = 'https://www.douyin.com/user/MS4wLjABAAAAY842S2QSA2De1lTrKf3v7GNTl67XrSmsTGmOXibilR186ieeUfRs_oNnzUfm57zM?from_tab_name=live'
        # self.profile_url = 'https://www.douyin.com/user/MS4wLjABAAAAH9Ymawk6gthuV4DePfjF4upWrC3_JRi_dZL-3IOnASw?from_tab_name=main'
        # self.profile_url = 'https://www.douyin.com/user/MS4wLjABAAAAottAzrge0kbDJHl_HgaaB5nExRAlGkQTPWtQwgC9ADo'
        # self.profile_url = 'https://www.douyin.com/user/MS4wLjABAAAAOypOKOJb4hIkkgEqLnhU4KXc7-TwYj4mcZ1I9MZXFF0'
        # self.profile_url = 'https://www.douyin.com/user/MS4wLjABAAAAogJUdSA2kbn4pVj325B2FsGq49m-26Bmb2GTzcEL3Os'
        print('profile_url=', self.profile_url)
        # 访问个人主页
        # page.get('https://www.kuaishou.com/profile/3xz2qp4wz6uj2hc')
        # page.get('https://www.kuaishou.com/profile/3xc8z7h9a2uj7yk')
        page.get(self.profile_url)

        # 等待页面加载完全
        page.wait.load_start()


        rg_element = page.ele('@id=MS3tMtRG')
        if rg_element:
            print('未登录,cookies失效')
            self.log_signal.emit("cookies失效,请移除cookies.txt的内容,重新登录...")
            page.close()
            return




        # 滚动加载所有作品
        print("等待 正在加载所有作品...")
        self.log_signal.emit('获取所有作品个数')
        # for _ in range(10):  # 适当增加滚动次数
        #     page.scroll.down(2000)
        #     time.sleep(2)

        run_count = 0
        while True:
            # spinning_element = page.ele('.spinning', timeout=10)
            user_post_list_element = page.ele("xpath://div[@data-e2e='user-post-list']")
            user_post_list_bottom_container_element = user_post_list_element.children()[1]
            bottom_text = user_post_list_bottom_container_element.child().text
            print(bottom_text)
            if bottom_text == '暂时没有更多了':
                break
            else:
                print('滑动')
                # user_post_list_element.scroll.down(2000)
                ac = Actions(tab)
                ac.move_to(ele_or_loc=user_post_list_element, offset_y=run_count * 500).scroll(delta_y=500)
                run_count += 1
                time.sleep(2)

        print("完成 正在加载所有作品...")


        url_list = []
        li_elements = page.ele("xpath://div[@data-e2e='user-post-list']").child().children()
        for li in li_elements:
            url = li.child().child().attr('href')
            print('url=', url)
            if '/video/' in url:
                url_list.append(url)

        MAX_CONCURRENT_DOWNLOADS = 5

        self.log_signal.emit('当前可下载的视频数:' + str(len(url_list)))
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
            for idx, u in enumerate(url_list, start=1):
                executor.submit(thread_get_video_url, page, u, self, idx)

        # video_pages = url_list
        #
        # video_urls = []
        #
        # # 第一步：串行提取视频链接
        # for url in video_pages:
        #     video_src = extract_video_src(page, url)
        #     if video_src:
        #         video_urls.append(video_src)
        #
        # print(f"提取到 {len(video_urls)} 个视频链接，开始并发下载...")
        #
        # # 第二步：并发下载
        # with ThreadPoolExecutor(max_workers=10) as executor:
        #     executor.map(download_file, video_urls)

        # time.sleep(10000)
        #
        #
        # # 获取所有封面的 <img> 标签  .user-photo-list
        # img_elements = page.eles('.poster-img', timeout=10)
        # print(img_elements)
        #
        # # 提取 clientCacheKey 值
        # pattern = re.compile(r'clientCacheKey=([^&]+)\.jpg')
        # client_keys = []
        #
        # for img in img_elements:
        #     src = img.attr('src')
        #     match = pattern.search(src)
        #     if match:
        #         client_keys.append(match.group(1))  # 提取 xxx 部分
        #
        # # 输出结果
        # print(f'共找到 {len(client_keys)} 个 clientCacheKey 值:')
        # print(client_keys)
        #
        # video_links = client_keys
        #
        #
        # is_single = True
        # if is_single:
        #     # 开始批量下载
        #     for i, link in enumerate(video_links):
        #         print(f'正在处理第 {i + 1} 个视频...')
        #         video_url = get_video_url('https://www.kuaishou.com/short-video/' + link)
        #         print('video_url=', video_url)
        #         if video_url:
        #             filename = os.path.join(SAVE_DIR, f'video_{i + 1}.mp4')
        #             download_video(video_url, filename, link)
        #         else:
        #             print(f'⚠️ 获取视频地址失败: {link}')
        #         time.sleep(3)  # 避免请求过快被封
        #
        #     print("✅ 所有视频下载完成！")
        # else:
        #     start_multithread_download(video_links=video_links)


