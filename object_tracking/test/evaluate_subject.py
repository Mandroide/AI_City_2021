"""Evaluate performance of re-locating main subject in video given tracking results
Experiments are in subject_v*.py files
"""
from types import new_class
from dataset.data_manager import train_track_map, test_query_map
from utils import json_load, json_save, AverageMeter

from object_tracking.test.test_utils import calculate_iou, calculate_distance, is_box_in_box

TRAIN_SRL_DIR = '/home/ntphat/projects/AI_City_2021/srl_handler/results/train_srl'
TRAIN_SVO_KEYS = '/home/ntphat/projects/AI_City_2021/srl_handler/results/train_stat.json'
TEST_SVO_KEYS = '/home/ntphat/projects/AI_City_2021/srl_handler/results/test_stat.json'

train_svo_data = json_load(TRAIN_SVO_KEYS)
TRAIN_SVO_IDS = train_svo_data['svo_query']
# TRAIN_SVO_IDS = [str(i) for i in TRAIN_SVO_IDS]

ACCEPT_IOU_THRES = 0.7
def evaluate(gt_boxes: list, cand_tracks: list):
    N = len(gt_boxes)

    score_map = []
    for track in cand_tracks:
        track_res = {
            'track_id': track.track_id,
            'score': 0, 'iou_avg': -1, 'dist_avg': -1, 'start_frame': -1, 'end_frame': -1,
        }
        iou_meter, dist_meter = AverageMeter(), AverageMeter()
        start_frame = -1
        end_frame = -1
        for i, frame_idx in enumerate(track.frame_order):
            track_box = track.boxes[i]
            gt_box = gt_boxes[frame_idx]
            inside = is_box_in_box(gt_box, track_box)
            if inside == True:
                iou = 1.0
            else:
                iou = calculate_iou(gt_box, track_box)
            dist = calculate_distance(gt_box, track_box)
            
            if (iou > ACCEPT_IOU_THRES): #or (inside == True):
                if start_frame == -1:
                    start_frame = frame_idx
                end_frame = frame_idx
                track_res['score'] += 1
                
            iou_meter.update(iou)
            dist_meter.update(dist)
                
        track_res['score'] /= N 
        track_res['iou_avg'] = iou_meter.avg
        track_res['dist_avg'] = dist_meter.avg
        track_res['start_frame'] = start_frame 
        track_res['end_frame'] = end_frame
        track_res['total'] = N

        score_map.append(track_res)

    return score_map