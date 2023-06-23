import argparse
import glob
import json
import os
from pathlib import Path
import random
import logging
import time
import threading

import cv2
import numpy as np

def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper

class DataManager:
    def __init__(self, data_root: str, n_frames: int, grip_pt_h: bool = False) -> None:
        super().__init__()
        self.media_dir = "./webapp/static/"
        for cam in ["gripper", "static"]:
            make_dir = os.path.join(self.media_dir, "%s_cam" % cam)
            os.makedirs(make_dir, exist_ok=True)
        self.save_data_dir = Path("./webapp/static/")
        self.n_frames = n_frames
        self.grip_pt_h = grip_pt_h
        self.n_seq_percentage = 1.0
        self.n_workers = 8
        self._c = 1
        _data_filename = self.save_data_dir / "data.json"
        print("checking if file exists...", _data_filename)
        _json_data = self.read_json(_data_filename)
        self.video_tags = {}
        if _json_data is None:
            print("Iterating through the dataset to create a new json file...")
            self.data = self.read_data_preprocessed(Path(data_root))
        else:
            self.data = _json_data
            for d in self.data:
                start = self.filename_to_idx(d["indx"][0])
                end = self.filename_to_idx(d["indx"][1])
                self.video_tags[(start, end)] = d["video_tag"]

    def read_json(self, data_filename):
        data = None
        if data_filename.is_file():
            with open(data_filename, "r") as read_file:
                data = json.load(read_file)
                print("found json file %s" % data_filename)
        else:
            print("Could not find previous data: %s" % data_filename)
        return data

    def save_json(self, data):
        data_filename = os.path.join(self.save_data_dir, "data.json")
        with open(data_filename, "w") as fout:
            json.dump(data, fout, indent=2)

    def check_exists(self, video_name):
        exists = True
        for cam in ["static", "gripper"]:
            folder_path = os.path.join(self.media_dir, "%s_cam" % cam)
            video_filename = os.path.join(folder_path, video_name)
            exists and os.path.isfile(video_filename)
        return exists

    def create_tmp_video(self, start, end, dir):
        start_idx = self.filename_to_idx(start)
        end_idx = self.filename_to_idx(end)
        video_tag = self.video_tags[(start_idx, end_idx)]

        # Check if exists
        gripper_imgs, static_imgs = [], []
        for i in range(start_idx, end_idx + 1):
            frame_i = self.idx_to_filename(i)
            filename = os.path.join(dir, frame_i)
            imgs = self.extract_imgs(filename)
            gripper_imgs.append(imgs["gripper"])
            static_imgs.append(imgs["static"])

        self.make_video(gripper_imgs, video_name=video_tag, cam="gripper")
        self.make_video(static_imgs, video_name=video_tag, cam="static")
        return video_tag

    def make_video(self, seq_imgs, fps=80, video_name="v", cam="static"):
        folder_path = os.path.join(self.media_dir, "%s_cam" % cam)
        video_path = os.path.join(folder_path, video_name)

        w, h = seq_imgs[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc("V", "P", "8", "0")
        video = cv2.VideoWriter(video_path, fourcc, fps, (w, h))  # 30 fps
        print("writing video to %s" % video_path)
        for img in seq_imgs:
            video.write(img[:, :, ::-1])
        cv2.destroyAllWindows()
        video.release()

    def extract_imgs(self, filename):
        data = np.load(filename, allow_pickle=True)
        imgs = {}
        for cam in ["gripper", "static"]:
            img = data["rgb_%s" % cam]
            img = cv2.resize(img, (300, 300))
            imgs[cam] = img
        # cv2.imshow("static", img[:, :, ::-1])  # W, H, C
        # cv2.waitKey(1)
        return imgs

    def filename_to_idx(self, filename):
        return int(filename.split("_")[-1][:-4])

    def idx_to_filename(self, idx):
        return "episode_%07d.npz" % idx

    def read_data_unprocessed(self, play_data_path):
        """
        play_data_path -> day -> time
        _data:(list)
            - {'indx': [start_filename, end_filename],
               'dir': directory of previous files,
               'n_frames': end_frame - start_frame}
        """
        # Get all posible initial_frames
        initial_frames = []
        date_folder = glob.glob("%s/*" % play_data_path, recursive=True)
        for path in date_folder:
            data_path = os.path.basename(path)

            # Get files in subdirectory
            time_folder = glob.glob("%s/*" % path, recursive=True)
            for dir in time_folder:
                files = glob.glob("%s/**/frame_*.npz" % dir, recursive=True)
                files.sort()
                indices = range(0, len(files) - self.n_frames, self.n_frames // 2)
                files = [files[i] for i in indices]
                files = files[: -self.n_frames]
                initial_frames.extend(files)

        # Select n_seq random sequences
        n_seq = min(len(initial_frames), self.n_seq)
        initial_frames = np.random.choice(initial_frames, size=n_seq, replace=False)
        frames_info = {}
        _data = []
        for frame_dir in initial_frames:
            head, start_filename = os.path.split(frame_dir)
            frame_idx = self.filename_to_idx(start_filename)
            end_frame_idx = frame_idx + self.n_frames
            end_filename = "episode_%06d.npz" % end_frame_idx
            frames_info = {"indx": [start_filename, end_filename], "dir": head, "n_frames": self.n_frames}
            _data.append(frames_info)
        self.save_json(_data)
        return _data

    @threaded
    def create_videos_threading(self, sequences):
        for seq_dct in sequences:
            start, end = seq_dct["indx"]
            data_dir = seq_dct["dir"]
            self.create_tmp_video(start, end, data_dir)

    def read_data_preprocessed(self, play_data_path):
        """
        play_data_path -> day -> time
        _data:(list)
            - {'indx': [start_filename, end_filename],
               'dir': directory of previous files,
               'n_frames': end_frame - start_frame}
        """
        # Get all posible initial_frames
        initial_frames = []
        _data_filename = play_data_path/"split.json"
        if os.path.isfile(_data_filename):
            ep_start_end_ids = self.read_json(_data_filename)
            ep_start_end_ids = [*ep_start_end_ids["training"], *ep_start_end_ids["validation"]]
        else:
            ep_start_end_ids = np.load(play_data_path / "ep_start_end_ids.npy").tolist()
        # iterate over each episode
        for ep in ep_start_end_ids:
            indices = list(range(ep[0], ep[1] - self.n_frames, self.n_frames // 3))
            # Select n_seq random sequences
            rand_seqs = random.sample(indices, round(len(indices) * self.n_seq_percentage))
            initial_frames.extend(rand_seqs)

        frames_info = {}
        _data = []
        # shuffle sequences from every episode
        initial_frames.shuffle()
        for seq_id, start_idx in enumerate(initial_frames):
            start_filename = self.idx_to_filename(start_idx)
            end_idx = start_idx + self.n_frames
            end_filename = self.idx_to_filename(end_idx)
            video_tag = "tmp_%d.webM" % seq_id
            frames_info = {
                "indx": [start_filename, end_filename],
                "dir": str(play_data_path),
                "n_frames": self.n_frames,
                "video_tag": video_tag
            }
            if (start_idx, end_idx) not in self.video_tags:
                _data.append(frames_info)
                self.video_tags[(start_idx, end_idx)] = video_tag

        logging.info("Starting workers")
        if len(_data) > self.n_workers:
            data_indices = np.array_split(np.arange(len(_data)), self.n_workers)
        else:
            data_indices = np.expand_dims(np.arange(len(_data)), -1)
        for indices in data_indices:
            sequences = [_data[i] for i in indices]
            self.create_videos_threading(sequences)
        self.save_json(_data)
        return _data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_root", type=str, default="data", help="directory where raw dataset is allocated")
    args = parser.parse_args()
    data_manager = DataManager(args.dataset_root, n_frames=256, grip_pt_h=False)
