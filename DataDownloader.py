import os
import time
from string import whitespace

import requests

from DataAcquirer import sleep
from Recorder import Logger
from StringCleaner import Cleaner


class Download:
    def __init__(self, log: Logger):
        self.log = log  # 日志记录模块
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.37"}  # 请求头
        self.video_id_api = "https://aweme.snssdk.com/aweme/v1/play/"  # 官方视频下载接口
        self.item_ids_api = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"  # 官方信息接口
        self.type_ = {"video": "", "images": ""}
        self.clean = Cleaner()
        self.length = 128  # 文件名称长度限制
        self.chunk = 1048576  # 单次下载文件大小，单位字节
        self._nickname = None  # 账号昵称
        self._root = None
        self._name = None
        self._time = None
        self._split = None
        self._folder = None
        self._music = False
        self.video_data = []
        self.image_data = []
        self.illegal = "".join(self.clean.rule.keys()) + whitespace[1:]

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, value):
        if value:
            try:
                _ = time.strftime(value, time.localtime())
                self._time = value
                self.log.info(f"时间格式设置成功: {value}", False)
            except ValueError:
                self.log.warning(f"时间格式错误: {value}，将使用默认时间格式（年-月-日 时.分.秒）")
                self._time = "%Y-%m-%d %H.%M.%S"
        else:
            self.log.warning("非法的时间格式，将使用默认时间格式（年-月-日 时.分.秒）")
            self._time = "%Y-%m-%d %H.%M.%S"

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if value:
            dict_ = {
                "id": 0,
                "desc": 1,
                "create_time": 2,
                "author": 3,
            }
            name = value.strip().split(" ")
            try:
                self._name = [dict_[i] for i in name]
                self.log.info(f"命名格式设置成功: {value}", False)
            except KeyError:
                self.log.warning(f"命名格式错误: {value}，将使用默认命名格式（创建时间 作者 描述）")
                self._name = [2, 3, 1]
        else:
            self.log.warning("非法的命名格式，将使用默认命名格式（创建时间 作者 描述）")
            self._name = [2, 3, 1]

    def get_name(self, data: list) -> str:
        return self.clean.filter(self.split.join(data[i] for i in self.name))

    @property
    def split(self):
        return self._split

    @split.setter
    def split(self, value):
        if value:
            for s in value:
                if s in self.illegal:
                    self.log.warning(f"无效的文件命名分隔符: {value}，默认使用“-”作为分隔符！")
                    self._split = "-"
                    return
            self._split = value
            self.log.info(f"命名分隔符设置成功: {value}", False)
        else:
            self.log.warning("非法的文件命名分隔符，默认使用“-”作为分隔符！")
            self._split = "-"

    @property
    def folder(self):
        return self._folder

    @folder.setter
    def folder(self, value):
        if value:
            for s in value:
                if s in self.illegal:
                    self.log.warning(
                        f"无效的下载文件夹名称: {value}，默认使用“Download”作为下载文件夹名称！")
                    self._folder = "Download"
                    return
            self._folder = value
            self.log.info(f"下载文件夹名称设置成功: {value}", False)
        else:
            self.log.warning("非法的下载文件夹名称！默认使用“Download”作为下载文件夹名称！")
            self._folder = "Download"

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        if os.path.exists(value) and os.path.isdir(value):
            self._root = value
            self.log.info(f"文件保存路径设置成功: {value}", False)
        else:
            self.log.warning(f"文件保存路径错误: {value}，将使用当前路径作为保存路径！")
            self._root = "./"

    @property
    def music(self):
        return self._music

    @music.setter
    def music(self, value):
        if isinstance(value, bool):
            self._music = value
            self.log.info(f"是否下载视频/图集的音乐: {value}", False)
        else:
            self.log.warning(f"音乐下载设置错误: {value}，默认不下载视频/图集的音乐！")
            self._music = False

    @property
    def nickname(self):
        return self._nickname

    @nickname.setter
    def nickname(self, value):
        if name := self.clean.filter(value):
            self._nickname = name
            self.log.info(f"账号昵称: {value}, 去除非法字符后: {name}", False)
        else:
            self.log.error(f"无效的账号昵称，原始昵称: {value}, 去除非法字符后: {name}")

    def create_folder(self, folder):
        if not folder:
            self.log.warning("无效的账号昵称！")
            return False
        root = os.path.join(self.root, folder)
        if not os.path.exists(root):
            os.mkdir(root)
        self.type_["video"] = os.path.join(root, "video")
        if not os.path.exists(self.type_["video"]):
            os.mkdir(self.type_["video"])
        self.type_["images"] = os.path.join(root, "images")
        if not os.path.exists(self.type_["images"]):
            os.mkdir(self.type_["images"])
        return True

    def get_data(self, item):
        params = {
            "item_ids": item,
        }
        response = requests.get(
            self.item_ids_api,
            params=params,
            headers=self.headers, timeout=10)
        sleep()
        if response.status_code == 200:
            self.log.info(f"资源 {item} 获取 item_list 成功！", False)
            return response.json()["item_list"][0]
        self.log.error(
            f"资源 {item} 获取 item_list 失败！响应码: {response.status_code}")

    def get_info(self, data, type_):
        for item in data:
            item = self.get_data(item)
            id_ = item["aweme_id"]
            desc = self.clean.filter(item["desc"] or id_)
            create_time = time.strftime(
                self.time,
                time.localtime(
                    item["create_time"]))
            music_title = item["music"]["title"]
            music = item["music"]["play_url"]["url_list"][0]
            if type_ == "Video":
                video_id = item["video"]["play_addr"]["uri"]
                self.log.info(
                    "视频: " + ",".join([id_, desc, create_time, self.nickname, video_id]), False)
                self.video_data.append(
                    [id_, desc, create_time, self.nickname, video_id, [music_title, music]])
            elif type_ == "Image":
                images = item["images"]
                images = [i['url_list'][3] for i in images]
                self.log.info(
                    "图集: " + ",".join([id_, desc, create_time, self.nickname, images]), False)
                self.image_data.append(
                    [id_, desc, create_time, self.nickname, images, [music_title, music]])
            else:
                raise ValueError("type_ 参数错误！应该为 Video 或 Image 其中之一！")

    def download_images(self):
        root = self.type_["images"]
        for item in self.image_data:
            for index, image in enumerate(item[4]):
                with requests.get(
                        image,
                        stream=True,
                        headers=self.headers) as response:
                    name = self.get_name(item)
                    self.save_file(response, root, f"{name}({index})", "webp")
                sleep()
            if self.music:
                with requests.get(
                        item[5][1],
                        stream=True,
                        headers=self.headers) as response:
                    self.save_file(
                        response, root, self.clean.filter(
                            item[5][0]), "mp3")
                sleep()

    def download_video(self):
        root = self.type_["video"]
        for item in self.video_data:
            params = {
                "video_id": item[4],
                "ratio": "1080p",
            }
            with requests.get(
                    self.video_id_api,
                    params=params,
                    stream=True,
                    headers=self.headers) as response:
                name = self.get_name(item)
                self.save_file(response, root, name, "mp4")
            sleep()
            if self.music:
                with requests.get(
                        item[5][1],
                        stream=True,
                        headers=self.headers) as response:
                    self.save_file(
                        response, root, self.clean.filter(
                            item[5][0]), "mp3")
                sleep()

    def save_file(self, data, root: str, name: str, type_: str):
        file = os.path.join(root, f"{name[:self.length]}.{type_}")
        if os.path.exists(file):
            self.log.info(f"{name[:self.length]}.{type_} 已存在，跳过下载！")
            self.log.info(f"{name[:self.length]}.{type_} 文件路径: {file}", False)
            return True
        with open(file, "wb") as f:
            for chunk in data.iter_content(chunk_size=self.chunk):
                f.write(chunk)
        self.log.info(f"{name[:self.length]}.{type_} 下载成功！")
        self.log.info(f"{name[:self.length]}.{type_} 文件路径: {file}", False)

    def run(self, video: list[str], image: list[str]):
        if self.create_folder(self.nickname):
            self.get_info(video, "Video")
            self.get_info(image, "Image")
            self.download_video()
            self.download_images()
        else:
            self.log.warning("未下载任何资源！")

    def run_alone(self, id_: str):
        if not self.folder:
            self.log.warning("未设置下载文件夹名称！")
            return False
        self.create_folder(self.folder)
        data = self.get_data(id_)
        self.nickname = data["author"]["nickname"]
        if len(data["video"]["play_addr"]["url_list"]) < 4:
            self.get_info([id_], "Video")
            self.download_images()
        else:
            self.get_info([id_], "Image")
            self.download_video()


if __name__ == "__main__":
    video_data = []
    image_data = []
    demo = Download(Logger())
    demo.root = ""
    demo.name = ""
    demo.time = ""
    demo.split = ""
    demo.nickname = "Demo"
    demo.run(video_data, image_data)