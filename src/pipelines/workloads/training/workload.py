# Based on https://pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html

import torch
import torchvision
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from tqdm import tqdm
from src.pipelines.utils import to_s3, from_s3
from src.pipelines.instrumentation import profiler

experiment_id = "training"


classes = ('plane', 'car', 'bird', 'cat',
           'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

batch_size = 4


transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 10)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = torch.flatten(x, 1)  # flatten all dimensions except batch
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def train_model(tool):
    # Prepare data
    trainset = torchvision.datasets.CIFAR10(root='./data', train=True,
                                            download=True, transform=transform)
    trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size,
                                              shuffle=True, num_workers=2)
    # Define a Convolutional Neural Network
    net = Net()

    # Define a Loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=0.001, momentum=0.9)

    # Train the network
    train_loop(epochs=4, trainloader=trainloader, net=net, criterion=criterion,
               optimizer=optimizer)
    print('Finished Training')

    print('Saving model')
    to_s3(net, f"experiment/{experiment_id}/{tool}/model")


def train_loop(epochs, trainloader, net, criterion, optimizer):
    for epoch in tqdm(range(epochs), desc="Training", position=0):  # loop over the dataset multiple times

        running_loss = 0.0
        for i, data in tqdm(enumerate(trainloader, 0), desc="Epoch", position=1):
            # get the inputs; data is a list of [inputs, labels]
            inputs, labels = data

            # zero the parameter gradients
            optimizer.zero_grad()

            # forward + backward + optimize
            outputs = net(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            # print statistics
            running_loss += loss.item()
            if i % 2000 == 1999:    # print every 2000 mini-batches
                print(f'[{epoch + 1}, {i + 1:5d}] loss: {running_loss / 2000:.3f}')
                running_loss = 0.0


def validate_model(tool):
    # Prepare data
    testset = torchvision.datasets.CIFAR10(root='./data', train=False,
                                       download=True, transform=transform)
    testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size,
                                         shuffle=False, num_workers=2)
    # Load model
    net = from_s3(f"experiment/{experiment_id}/{tool}/model")

    # Validate model
    validate_loop(testloader=testloader, net=net)


def validate_loop(testloader, net):
    correct = 0
    total = 0
    with torch.no_grad():
        for data in tqdm(testloader, desc="Validating", position=0):
            images, labels = data
            outputs = net(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)  # number of labels
            correct += (predicted == labels).sum().item()
    print(f'Accuracy of the network on the 10000 test images: {100 * correct / total}%')


# Steps
def step_1_train(tool, run_id):
    @profiler(tool=tool, experiment_id=experiment_id,
              run_id=run_id, step_id="train")
    def training():
        print("Starting training")
        train_model(tool)
    training()


def step_2_validate(tool, run_id):
    @profiler(tool=tool, experiment_id=experiment_id,
              run_id=run_id, step_id="validate")
    def validate():
        print("Starting validation")
        validate_model(tool)
    validate()
