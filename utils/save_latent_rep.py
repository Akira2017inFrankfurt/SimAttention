from network.encoder import PCT_Encoder
import torch
import numpy as np
from dataloader import ModelNetDataSet
import os
from utils.provider import *
from tqdm import tqdm

# original dataset file path
root = '/home/akira/下载/Pointnet2_PyTorch-master/PCT/Point-Transformers-master/data/modelnet40_normal_resampled'
# pretrained weights path
model_save_path = r'/home/akira/下载/Pointnet2_PyTorch-master/SimAttention/scripts/weights/model-35-lr-x10.pth'
# save txt file path
file_path = r'/home/akira/下载/Pointnet2_PyTorch-master/SimAttention/jupyter_tests/mydata'
if not os.path.exists(file_path):
    os.mkdir(file_path)
loaded_paras = torch.load(model_save_path)

# get encoder model
encoder = PCT_Encoder().cuda()
encoder_dict = encoder.state_dict()
new_state_dict = {}
for k in loaded_paras.keys():
    if k.startswith('online_encoder'):
        new_k = k[15:]
        new_state_dict[new_k] = loaded_paras[k]
encoder_dict.update(new_state_dict)
encoder.load_state_dict(encoder_dict)

# data preparation
train_dataset = ModelNetDataSet(root, split='train')
BATCH_SIZE = 16
trainDataLoader = torch.utils.data.DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
trainDataLoader = tqdm(trainDataLoader)


def save_txt(x, label, file_path, step):
    file_name = os.path.join(file_path, str(step) + '.txt')
    l = torch.unsqueeze(label, 1)  # [B] ---> [B, 1]
    data = torch.cat((x, l), 1)  # [B, 1024] ---> [B, 1025]
    data = data.detach().cpu().numpy()  # [B, 1025]
    np.savetxt(file_name, data, delimiter=',')


for step, data in enumerate(trainDataLoader):
    points, target = data
    points = points.data.numpy()
    points = random_point_dropout(points)
    points[:, :, 0:3] = random_scale_point_cloud(points[:, :, 0:3])
    points[:, :, 0:3] = shift_point_cloud(points[:, :, 0:3])
    points = torch.Tensor(points)
    target = target[:, 0]  # [B]
    points, target = points.cuda(), target.cuda()
    get_global_feature = encoder.eval()
    latent_rep = encoder(points).reshape(points.shape[0], -1)
    save_txt(latent_rep, target, file_path, step)
