"""FAIL
"""

import json, pickle, os
import os.path as osp 
import cv2 
from tqdm import tqdm
import torch 
import multiprocessing as mp

from box_extractor import init_model
from config import cfg_veh, cfg_col
from utils import get_feat_from_subject_box, pickle_load, pickle_save

## GLOBAL VARIABLES

## Use this below code when you have placed the dataset folder inside this project
ROOT_DIR = '/content/AIC21_Track5_NL_Retrieval'
# ROOT_DIR = '/scratch/ntphat/dataset'
# ROOT_DIR = '../dataset'

# SAVE_DIR = '/scratch/ntphat/results'
SAVE_DIR = './results'
TRAIN_TRACK_JSON = './data/Centernet2_train_veh_boxes.json'
TEST_TRACK_JSON = './data/Centernet2_test_veh_boxes.json'
SAVE_PERIOD = 10
os.makedirs(SAVE_DIR, exist_ok=True)

train_track = json.load(open(TRAIN_TRACK_JSON))
test_track = json.load(open(TEST_TRACK_JSON))
data_track = {'train': train_track, 'test': test_track}

veh_model, col_model = init_model(cfg_veh, cfg_col, load_ckpt=True)
veh_model = veh_model.cuda()
col_model = col_model.cuda()

def process_track(key_sample):
    key = key_sample['key']
    key_data = key_sample['key_data']
    data_dir = key_sample['data_dir']
    mode_save_dir = key_sample['mode_save_dir']
    
    global veh_model 
    global col_model

    track_save_path = osp.join(mode_save_dir, f'{key}.pkl')
    if osp.isfile(track_save_path):
        return 

    track_feat = {}
    with torch.no_grad():
        for frame_dict in key_data:
            frame_path = list(frame_dict.keys())[0]
            frame_feat = []
            for box_coor in frame_dict[frame_path]:
                img_path = osp.join(data_dir, frame_path)
                cv_img = cv2.imread(img_path)
                cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                
                box_coor = [int(x) for x in box_coor]
                x_0, y_0, x_1, y_1 = box_coor
                crop = cv_img[y_0:y_1, x_0:x_1, :]
                box_feat = get_feat_from_subject_box(crop, veh_model, col_model)
                box_feat = box_feat.detach().numpy()
                frame_feat.append(box_feat)
            track_feat[frame_path] = frame_feat
        
        pickle_save(track_feat, track_save_path, verbose=False)
    pass


def extract_feature(data_track, data_dir, mode_save_dir: str):    
    list_samples = []
    for key in data_track:
        list_samples.append({
            'key': key,
            'key_data': data_track[key],
            'data_dir': data_dir,
            'mode_save_dir': mode_save_dir,
        })
    
    with mp.Pool() as pool:
        pool.map(process_track, list_samples)
    
    pass



if __name__ == '__main__':
    print(f'Run with {mp.cpu_count()} cpus')
    for mode in ["train", "test"]:
        print(f"Extracting {mode} data")
        save_path = osp.join(SAVE_DIR, f'{mode}_feat.pkl')
        mode_save_dir = osp.join(SAVE_DIR, f'{mode}_feat_mp')
        os.makedirs(mode_save_dir, exist_ok=True)

        feat = extract_feature(data_track[mode], ROOT_DIR, mode_save_dir)
        pickle_save(feat, save_path)