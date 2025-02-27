import os, json 
import os.path as osp 
import spacy

from .vehicle import Vehicle
from .text_utils import (
    get_color, refine_srl_args, get_args_from_srl_sample, extract_noun_phrase
)
from utils.constant import (
    VEHICLE_VOCAB, COLOR_VOCAB, ACTION_VOCAB
)

nlp_model = spacy.load('en_core_web_sm')

class Caption(object):
    def __init__(self, cap_content: dict, cap_id: str):
        self.cap_id = cap_id
        self.__dict__.update(cap_content)
        
        self.sv_format, self.svo_format = [], []
        # self.nlp_model = spacy.load('en')
        self._setup()
        pass

    def _extract_object(self, srl_content):
        """
        Args:
            srl_content ([type]): [description]
        Returns:
            [type]: [description]
        """
        args = get_args_from_srl_sample(srl_content)
        if args is None:
            return None
        
        list_objs = []
        main_object = None
        for arg in args:
            # tokens = self.nlp_model(arg)
            # tokens = nlp_model(arg)
            tokens = arg.split(' ')
            colors = get_color(tokens)
            for tok in tokens:
                if tok in VEHICLE_VOCAB:
                # if ('NN' in tok.pos_) and (tok in VEHICLE_VOCAB):
                    # list_colors.append(colors)
                    main_object = Vehicle(vehicle=tok, colors=colors)
                    # list_objs.append(Vehicle(vehicle=tok, color=colors))
        
        return main_object
    
    def _create_sv_sample(self, action):
        return {'S': self.subject, 'V': action}

    def _create_svo_sample(self, action, main_object):
        return {'S': self.subject, 'V': action, 'O': main_object}
    
    def _init_main_subject(self):
        all_colors, obj_colors = [], []
        for srl in self.srl:
            action = srl['action']
            if srl['is_main_subject']:
                obj_colors.extend(srl['subject_color'])
        
        self.subject = Vehicle(vehicle=self.main_subject, colors=obj_colors)
        
    def _setup(self):
        if len(self.srl) <= 1:
            self.is_svo = False 
        
        if len(self.srl) == 0:
            extract_result = extract_noun_phrase(self.cleaned_caption, nlp_model, VEHICLE_VOCAB)
            if extract_result is not None:
                self.subject = Vehicle(vehicle=extract_result['S'], colors=extract_result['colors'])
            else:
                self.subject = Vehicle(vehicle=self.main_subject, colors=[])
            
        else:
            self._init_main_subject()
            for srl in self.srl:
                action = srl['action']
                obj = self._extract_object(srl)

                if (action in ACTION_VOCAB) and (srl['is_main_subject'] is True):
                    self.sv_format.append(self._create_sv_sample(action))
                else:
                    self.svo_format.append(self._create_svo_sample(action, obj))
                pass

            
            