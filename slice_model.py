import torch
import copy
import torch.nn as nn

from model import loss_fn


class SimAttention_All_Slices(nn.Module):
    """
    crop method uses all slices 
    """
    def __init__(self,
                 aug_function,
                 sub_function,
                 slice_function,
                 online_encoder,
                 crossed_attention_method):
            super().__init__()
            self.aug_function = aug_function
            self.sub_function = sub_function
            self.slice_function = slice_function
        
        self.online_encoder = online_encoder
        self.target_encoder = None

        self.online_x_attn = crossed_attention_method
        self.target_x_attn = None

    def forward(self, x):
        x = x.cpu().numpy()
        # numpy
        aug1 = self.aug_function(x)
        aug2 = self.aug_function(x)

        # B, 1024, 3, tensor
        _, sub1 = self.sub_function(torch.Tensor(aug1).cuda(), 1024)
        _, sub2 = self.sub_function(torch.Tensor(aug2).cuda(), 1024)
        
        # B, 1024, 3, tensor
        online_slice_x_1, online_slice_x_2 = self.slice_function(aug1, 0)
        online_slice_y_1, online_slice_y_2 = self.slice_function(aug1, 1)
        online_slice_z_1, online_slice_z_2 = self.slice_function(aug1, 2)

        target_slice_x_1, target_slice_x_2 = self.slice_function(aug2, 0)
        target_slice_y_1, target_slice_y_2 = self.slice_function(aug2, 1)
        target_slice_z_1, target_slice_z_2 = self.slice_function(aug2, 2)

        # [B, 1, N_f] N_f: output dimension of mlp: 1024
        sub_feature_1 = self.online_encoder(sub1)
        sub_feature_3 = self.online_encoder(sub2)

        # with momentum encoder
        with torch.no_grad():
            if self.target_encoder is None:
                self.target_encoder = copy.deepcopy(self.online_encoder)
            else:
                for online_params, target_params in zip(self.online_encoder.parameters(),
                                                        self.target_encoder.parameters()):
                    target_weight, online_weight = target_params.data, online_params.data
                    # moving average decay is tao
                    tao = 0.99
                    target_params.data = target_weight * tao + (1 - tao) * online_weight
            for parameter in self.target_encoder.parameters():
                parameter.requires_grad = False
            sub_feature_2 = self.target_encoder(sub2)
            sub_feature_4 = self.target_encoder(sub1)


        # slice feature online branch [B, 1, N_f]
        slice_feature_1_1 = self.online_encoder(online_slice_x_1)
        slice_feature_1_2 = self.online_encoder(online_slice_x_2)
        slice_feature_1_3 = self.online_encoder(online_slice_y_1)
        slice_feature_1_4 = self.online_encoder(online_slice_y_2)
        slice_feature_1_5 = self.online_encoder(online_slice_z_1)
        slice_feature_1_6 = self.online_encoder(online_slice_z_2)
        
        # slice feature target branch [B, 1, N_f]
        slice_feature_2_1 = self.online_encoder(target_slice_x_1)
        slice_feature_2_2 = self.online_encoder(target_slice_x_2)
        slice_feature_2_3 = self.online_encoder(target_slice_y_1)
        slice_feature_2_4 = self.online_encoder(target_slice_y_2)
        slice_feature_2_5 = self.online_encoder(target_slice_z_1)
        slice_feature_2_6 = self.online_encoder(target_slice_z_2)

        # crop feature concat [B, 6, N_f]
        crop_feature_1 = torch.cat((slice_feature_1_1, slice_feature_1_2,
                                    slice_feature_1_3, slice_feature_1_4,
                                    slice_feature_1_5, slice_feature_1_6,), dim=1)
        crop_feature_2 = torch.cat((slice_feature_2_1, slice_feature_2_2,
                                    slice_feature_2_3, slice_feature_2_4,
                                    slice_feature_2_5, slice_feature_2_6,), dim=1)
        # [B, 12, N_f]
        crop_feature = torch.cat((crop_feature_1, crop_feature_2), dim=1)

        # momentum attention feature
        with torch.no_grad():
            if self.target_x_attn is None:
                self.target_x_attn = copy.deepcopy(self.online_x_attn)
            else:
                for online_params, target_params in zip(self.online_x_attn.parameters(),
                                                        self.target_x_attn.parameters()):
                    target_weight, online_weight = target_params.data, online_params.data
                    # moving average decay is tao
                    tao = 0.99
                    target_params.data = target_weight * tao + (1 - tao) * online_weight
            for parameter in self.target_x_attn.parameters():
                parameter.requires_grad = False
            # target feature
            attn_feature_2 = self.target_x_attn(sub_feature_2, crop_feature)
            attn_feature_4 = self.target_x_attn(sub_feature_4, crop_feature)
            
        # online feature
        attn_feature_1 = self.online_x_attn(sub_feature_1, crop_feature)
        attn_feature_3 = self.online_x_attn(sub_feature_3, crop_feature)

        # loss
        loss_1 = loss_fn(attn_feature_1, attn_feature_2)
        loss_2 = loss_fn(attn_feature_3, attn_feature_4)
        loss = loss_1 + loss_2

        return loss.mean()
    