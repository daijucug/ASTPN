import os
import os.path as osp
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.backends.cudnn as cudnn
from torchvision import datasets, transforms
import torchvision.models as models
from torch.autograd import Variable
import numpy as np
from ASTPN import ASTPN
# from attention_network import AttentionNet
import random
import cv2
from dataset import same_pair,different_pair 
from compute_CMC import computeCMC

    
nEpochs = 2000
learning_rate = 0.001
sampleSeqLength = 16

this_dir = osp.dirname(__file__)
person_sequence = osp.join(this_dir, "..", "data", "i-LIDS-VID", "sequences")
optical_sequence = osp.join(this_dir, "..", "data", "i-LIDS-VID-OF-HVP", "sequences")

model = ASTPN()
# model = AttentionNet()
model = model.cuda()

# set for optimizer step
# steps = [90000,500000]
# scales = [0.1,0.1]
# processed_batches = 0

loss_diatance = nn.HingeEmbeddingLoss(3,size_average=True)
loss_identity = nn.CrossEntropyLoss()

#choose trainIDs split=0.5
IDs = os.listdir(osp.join(person_sequence,"cam1"))
# print IDs
# print len(IDs) 300
trainID = []
testID  = []
for i in range(300):
	if i%2 == 0:
		trainID.append(IDs[i])
	else:
		testID.append(IDs[i])

nTrainPersons = len(trainID)

torch.manual_seed(1)
# np.random.seed(1)
# torch.cuda.manual_seed(1)

optimizer = optim.SGD(model.parameters(), lr= learning_rate, momentum=0.9)
# optimizer = optim.RMSprop(model.parameters(), lr=0.001, alpha=0.9)

def adjust_learning_rate(optimizer, batch):
    #Sets the learning rate to the initial LR decayed by 10 every 30 epochs
    lr = learning_rate
    for i in range(len(steps)):
        scale = scales[i] if i < len(scales) else 1
        if batch >= steps[i]:
            lr = lr * scale
            if batch == steps[i]:
                break
        else:
            break

    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
    return lr


# for parameter in model.parameters():
#     print(parameter)

loss_log = []

for ep in range(nEpochs):
    # random every epoch
    loss_add = 0
    order = torch.randperm(nTrainPersons)
    for i in range(nTrainPersons*2):

        # lr = adjust_learning_rate(optimizer, processed_batches)
        # processed_batches = processed_batches + 1

        if (i%2 == 0): 
        # load data from same identity
            netInputA, netInputB, label_same = same_pair(trainID[order[i/2]],sampleSeqLength)	
            labelA = order[i/2]
            labelB = order[i/2]

        else:
	        # load data from different identity random
	        netInputA, netInputB, labelA, labelB ,label_same = different_pair(trainID,sampleSeqLength)

        netInputA = Variable(torch.from_numpy(netInputA).float()).cuda()
        netInputB = Variable(torch.from_numpy(netInputB).float()).cuda()

        # optimizer.zero_grad()
		# v_p,v_g,identity_p,identity_g = model(netInputA,netInputB)
        distance,identity_p,identity_g,v_p,v_g = model(netInputA,netInputB)


        label_same = torch.FloatTensor([label_same])
        label_same = Variable(label_same).cuda()


        label_identity1 = (Variable(torch.LongTensor([labelA]))).cuda()
        label_identity2 = (Variable(torch.LongTensor([labelB]))).cuda()

        loss_pair = loss_diatance(distance,label_same)

        #two loss need to be fixed
        loss_identity1 = loss_identity(identity_p, label_identity1)
        loss_identity2 = loss_identity(identity_g, label_identity2)

        loss = loss_pair+loss_identity1+loss_identity2

        # print "loss:   ",loss
        loss_add = loss_add + loss.data[0]
        # print loss
        # Euclidean_distance = (torch.mean(torch.pow((v_p-v_g),2))*(v_p.size()[0])).data.cpu()
        # zero = torch.FloatTensor([0])
        # label_same = Variable(label_same)
        # loss = label_same*Euclidean_distance+(1-label_same)*torch.max(zero, 3-Euclidean_distance)
        # loss = label_same*Euclidean_distance+(1-label_same)*torch.clamp((3-Euclidean_distance),min=0)
        # loss need to update

        if i%10 == 0:
            loss_log.append(loss.data[0])
            # print('\nepoch: {} - batch: {}/{}'.format(ep, i, len(trainID)*2))
            # print('loss: ', loss.data[0])

        #### clip gradient parameters to train RNN#####

        # nn.utils.clip_grad_norm(model.parameters(), 5)
        # for p in model.parameters():
        #     if p.grad is not None:
        #         p.grad.data.clamp_(-5, 5)

        # torch.nn.utils.clip_grad_norm(model.parameters(),5)

        ##############################################
        optimizer.zero_grad()
        loss.backward() 
        nn.utils.clip_grad_norm(model.parameters(), 5)
        optimizer.step()

    if ep%1 ==0:
        # print('epoch %d, lr %f, loss %f ' % (ep, lr, loss_add))
        print('epoch %d, loss %f ' % (ep , loss_add))

    if (ep+1)%100 == 0: 
 
        model.eval() 
        cmc = computeCMC(testID, model) 
        print cmc 

    # if (ep+1)%500 == 0: 
 
    #     model.eval() 
    #     cmc = computeCMC(testID, model) 
    #     print cmc 


# print loss_log
        
torch.save(model.state_dict(), './siamese.pth')

import matplotlib.pyplot as plt
plt.plot(loss_log)
plt.title('ASTPN Loss')
plt.show()























