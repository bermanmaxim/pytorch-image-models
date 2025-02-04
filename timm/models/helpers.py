import torch
import torch.utils.model_zoo as model_zoo
import os
from collections import OrderedDict


def load_checkpoint(model, checkpoint_path, use_ema=False):
    if checkpoint_path and os.path.isfile(checkpoint_path):
        checkpoint = torch.load(checkpoint_path)
        state_dict_key = ''
        if isinstance(checkpoint, dict):
            state_dict_key = 'state_dict'
            if use_ema and 'state_dict_ema' in checkpoint:
                state_dict_key = 'state_dict_ema'
        if state_dict_key and state_dict_key in checkpoint:
            new_state_dict = OrderedDict()
            for k, v in checkpoint[state_dict_key].items():
                # strip `module.` prefix
                name = k[7:] if k.startswith('module') else k
                new_state_dict[name] = v
            model.load_state_dict(new_state_dict)
        else:
            model.load_state_dict(checkpoint)
        print("=> Loaded {} from checkpoint '{}'".format(state_dict_key or 'weights', checkpoint_path))
    else:
        print("=> Error: No checkpoint found at '{}'".format(checkpoint_path))
        raise FileNotFoundError()


def resume_checkpoint(model, checkpoint_path, start_epoch=None):
    optimizer_state = None
    if os.path.isfile(checkpoint_path):
        checkpoint = torch.load(checkpoint_path)
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            new_state_dict = OrderedDict()
            for k, v in checkpoint['state_dict'].items():
                name = k[7:] if k.startswith('module') else k
                new_state_dict[name] = v
            model.load_state_dict(new_state_dict)
            if 'optimizer' in checkpoint:
                optimizer_state = checkpoint['optimizer']
            start_epoch = checkpoint['epoch'] if start_epoch is None else start_epoch
            print("=> Loaded checkpoint '{}' (epoch {})".format(checkpoint_path, checkpoint['epoch']))
        else:
            model.load_state_dict(checkpoint)
            start_epoch = 0 if start_epoch is None else start_epoch
            print("=> Loaded checkpoint '{}'".format(checkpoint_path))
        return optimizer_state, start_epoch
    else:
        print("=> Error: No checkpoint found at '{}'".format(checkpoint_path))
        raise FileNotFoundError()


def load_pretrained(model, default_cfg, num_classes=1000, in_chans=3, filter_fn=None):
    if 'url' not in default_cfg or not default_cfg['url']:
        print("Warning: pretrained model URL is invalid, using random initialization.")
        return

    state_dict = model_zoo.load_url(default_cfg['url'])

    if in_chans == 1:
        conv1_name = default_cfg['first_conv']
        print('Converting first conv (%s) from 3 to 1 channel' % conv1_name)
        conv1_weight = state_dict[conv1_name + '.weight']
        state_dict[conv1_name + '.weight'] = conv1_weight.sum(dim=1, keepdim=True)
    elif in_chans != 3:
        assert False, "Invalid in_chans for pretrained weights"

    strict = True
    classifier_name = default_cfg['classifier']
    if num_classes == 1000 and default_cfg['num_classes'] == 1001:
        # special case for imagenet trained models with extra background class in pretrained weights
        classifier_weight = state_dict[classifier_name + '.weight']
        state_dict[classifier_name + '.weight'] = classifier_weight[1:]
        classifier_bias = state_dict[classifier_name + '.bias']
        state_dict[classifier_name + '.bias'] = classifier_bias[1:]
    elif num_classes != default_cfg['num_classes']:
        # completely discard fully connected for all other differences between pretrained and created model
        del state_dict[classifier_name + '.weight']
        del state_dict[classifier_name + '.bias']
        strict = False

    if filter_fn is not None:
        state_dict = filter_fn(state_dict)

    model.load_state_dict(state_dict, strict=strict)






