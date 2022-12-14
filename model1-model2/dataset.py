import torch
from torch.utils.data import Dataset
from torch.utils.data import random_split
import os

# seq to val
class DSCOVRMagneticFieldToWindProtonDataset(Dataset):
    def __init__(self, data_path, start_year, end_year):
        self.x = torch.tensor([]).float()
        self.y = torch.tensor([]).float()
        self.load_in(data_path, start_year, end_year)

    def load_in(self, data_path, start_year, end_year):
        # x: [bs, seq_len, 3]
        # y: [bs, 3]
        # modify: y: [bs, seq_len, 3]
        for year in range(start_year, end_year+1):
            year_data = torch.load(os.path.join(data_path, f"data_{year}.pt"))
            self.x = torch.cat([self.x, year_data["X"].float()], dim=0)
            self.y = torch.cat([self.y, year_data["Y"].float()], dim=0)
        print("total x shape:", self.x.shape)
        print("total y shape:", self.y.shape)

    def __len__(self) -> int:
        return self.x.shape[0]

    def __getitem__(self, index):
        return self.x[index, :, :], self.y[index, :, :]


# seq to seq
class DSCOVRMagneticFieldToWindMagneticField(Dataset):
    def __init__(self, data_path, start_year, end_year):
        self.x_prime = torch.tensor([]).float()
        self.x = torch.tensor([]).float()
        self.load_in(data_path, start_year, end_year)

    def load_in(self, data_path, start_year, end_year):
        # x_prime: [bs, seq_len, 3]
        # x: [bs, seq_len, 3]
        for year in range(start_year, end_year+1):
            year_data = torch.load(os.path.join(data_path, f"data_{year}.pt"))
            self.x_prime = torch.cat([self.x_prime, year_data["X"].float()], dim=0)
            self.x = torch.cat([self.x, year_data["xx"].float()], dim=0)
        print("total x_prime shape:", self.x_prime.shape)
        print("total x shape:", self.x.shape)

    def __len__(self) -> int:
        return self.x.shape[0]

    def __getitem__(self, index):
        return self.x_prime[index, :, :], self.x[index, :, :]
