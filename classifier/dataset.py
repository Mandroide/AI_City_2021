import os, json, cv2
import os.path as osp 
import pandas as pd 
from tqdm.notebook import tqdm
from glob import glob
import seaborn as sns 
import numpy as np
import matplotlib.pyplot as plt
import PIL
from PIL import Image

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torch.utils.data import Subset, DataLoader, Dataset

import torchvision
from torchvision import datasets, models, transforms
from torchvision.datasets import ImageFolder
from sklearn.model_selection import StratifiedKFold

from efficientnet_pytorch import EfficientNet
from config import CONFIG

VEH_TRAIN_CSV = '/content/SOURCE/extract_object/data/VEHICLE/train_fraction.csv'
COL_TRAIN_CSV = '/content/SOURCE/extract_object/data/COLOR/train_fraction.csv'
VEH_GROUP_JSON = '/content/SOURCE/extract_object/data/VEHICLE/vehicle_group_v1.json'
COL_GROUP_JSON = '/content/SOURCE/extract_object/data/COLOR/color_group_v1.json'
VEH_BOX_DIR = '/content/TMP/classifier/data/veh_boxes'
COL_BOX_DIR = '/content/TMP/classifier/data/col_boxes'

n_splits = 5
n_get = 1
count = 1
skf = StratifiedKFold(n_splits, shuffle=True, random_state=88)


class VehicleDataset(Dataset):
    def __init__(self, df, mode='train'):
        self.img_paths = df['paths'].values
        self.labels = df['labels'].values
        self._setup_transform()
        self.mode = mode

    def _setup_transform(self):
        self.train_transform = transforms.Compose([
            transforms.Resize(CONFIG['image_size'], PIL.Image.BICUBIC),
            transforms.CenterCrop(CONFIG['image_size']),
            transforms.RandomHorizontalFlip(p=0.8),
            transforms.RandomAffine(30, translate=[0.1, 0.1], scale=[0.9, 1.1]), 
            transforms.ColorJitter(brightness=(0.8, 1.2), contrast=(0.75, 1.25)),
            transforms.ToTensor(),
            transforms.Normalize(CONFIG['imagenet_mean'], CONFIG['imagenet_std']),
        ])
        self.val_transform = transforms.Compose([
            transforms.Resize(CONFIG['image_size'], PIL.Image.BICUBIC),
            transforms.ToTensor(),
            transforms.Normalize(CONFIG['imagenet_mean'], CONFIG['imagenet_std']),
        ])
        
    def __len__(self):
        return len(self.img_paths)

    def __getitem__(self, idx):
        img_path = self.img_paths[idx]
        img = Image.open(img_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        if self.mode == 'train':    
            img = self.train_transform(img)
        else:
            img = self.val_transform(img)

        y_true = self.labels[idx]
        if isinstance(y_true, str):
            y_true = np.array(eval(y_true)).astype(np.float)
        y = torch.Tensor(y_true)

        if self.mode == 'test':
            return {'img': img, 'label': y, 'img_path': img_path}

        return {'img': img, 'label': y,}


#TODO: veh_box_v1, col_box_v3 --> choose new_dir

def get_dataset(csv_path: str, group_json: str, box_data_dir):
    def replace_box_dir(cur_dir: str):
        if box_data_dir == VEH_BOX_DIR:
            cur_dir = cur_dir.replace('/home/ntphat/projects/aic21/aic2021/results/veh_class_2/train', box_data_dir)
        else:
            cur_dir = cur_dir.replace('/home/ntphat/projects/aic21/aic2021/results/col_class/train', box_data_dir)
            pass
        
        return cur_dir 

    df_full = pd.read_csv(csv_path)
    df_full['paths'] = df_full['paths'].apply(replace_box_dir)
    df_filtered = df_full.drop_duplicates(subset='query_id', keep="first")
    df_filtered.head()
    
    veh_group = json.load(open(group_json, 'r'))
    id_map = {} # {'group-1': 0}
    for k in veh_group.keys():
        i = int(k.split('-')[1]) - 1
        id_map[k] = i

    N_CLASSES = len(list(id_map.keys()))
    veh_map = {} # {'suv': 2}
    for k in veh_group.keys():
        i = id_map[k]
        for veh in veh_group[k]:
            veh_map[veh] = i 

    filtered_labels = df_filtered['labels']
    full_train_ids = []
    full_val_ids = []
    count = 1
    for train_ids, val_ids in skf.split(df_filtered, filtered_labels):
        if count > n_get:
            break
        for val in train_ids:
            full_train_ids.extend(list(range(val*4, (val+1)*4)))
        for val in val_ids:
            full_val_ids.extend(list(range(val*4, (val+1)*4)))
        df_train, df_val = df_full.iloc[full_train_ids], df_full.iloc[full_val_ids]
        count += 1

    return df_train, df_val
    
