from argparse import ArgumentParser, Namespace
import enum
from pathlib import Path
from typing import Dict
from datetime import datetime
import os

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.utils.data import random_split
import logging
import dataset
from model import *
from utils import R2_score
from utils import *
import matplotlib.pyplot as plt



def main(args):

	print(f"Using device: {args.device}")
	args.ckpt_dir = os.path.join(args.ckpt_dir, datetime.now().strftime("%Y_%m_%d__%H_%M_%S"))
	os.mkdir(args.ckpt_dir)
	logger = get_loggings(args.ckpt_dir)

	# dataset, split
	d = dataset.DSCOVRMagneticFieldToWindProtonDataset(args.data_path, args.start_year, args.end_year)
	logger.info(f"Dataset length: {len(d)}")
	data_num = len(d)
	train_ratio, valid_ratio, test_ratio = 0.7, 0.2, 0.1
	train_num, valid_num = int(data_num*train_ratio), int(data_num*valid_ratio)
	test_num = data_num - train_num - valid_num
	train_dataset, valid_dataset, test_dataset = random_split(d, [train_num, valid_num, test_num])
	# train_dataset, valid_dataset, test_dataset = d.split()
	logger.info(f"train, valid, test dataset len: {len(train_dataset)}, {len(valid_dataset)}, {len(test_dataset)}")

	# crecate DataLoader for train / dev datasets
	train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
	valid_loader = DataLoader(valid_dataset, batch_size=args.batch_size, shuffle=False)
	test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False)

	model_args = {"input_dim": 3, "hidden_dim": args.hidden_dim, "output_dim": 3, "num_layers": args.num_layers}
	model = Seq2Val(**model_args).to(args.device)
	logger.info(model)

	# init optimizer
	optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
	scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', factor=0.5, patience=10, min_lr=5e-5)
	criterion = torch.nn.MSELoss()
	best_eval_loss = np.inf

	for epoch in range(1, args.num_epoch+1):
		# Training loop - iterate over train dataloader and update model weights
		model.train()
		loss_train, acc_train, iter_train = 0, 0, 0
		for x, y in train_loader:
			x, y = x.to(args.device), y.to(args.device)

			half_seq_len = x.shape[1] // 2
			outputs = model(x[:, :half_seq_len, :])
			# calculate loss and update parameters
			loss = criterion(outputs, y[:, half_seq_len-1, :])
			optimizer.zero_grad()
			loss.backward()
			optimizer.step()

			# accumulate loss, accuracy
			iter_train += 1
			loss_train += loss.item()
			acc_train += R2_score(outputs, y[:, half_seq_len-1, :])
		
		loss_train /= iter_train
		acc_train /= iter_train

		# Evaluation loop - calculate accuracy and save model weights
		model.eval()
		with torch.no_grad():
			loss_eval, acc_eval, iter_eval = 0, 0, 0
			for x, y in valid_loader:
				x, y = x.to(args.device), y.to(args.device)
				# outputs = model(x)
				half_seq_len = x.shape[1] // 2
				outputs = model(x[:, :half_seq_len, :])

				# calculate loss and update parameters
				loss = criterion(outputs, y[:, half_seq_len-1, :])

				# accumulate loss, accuracy
				iter_eval += 1
				loss_eval += loss.item()
				acc_eval += R2_score(outputs, y[:, half_seq_len-1, :])
			
			loss_eval /= iter_eval
			acc_eval /= iter_eval

		logger.info(f"epoch: {epoch:4d}, train_acc: {acc_train:.4f}, eval_acc: {acc_eval:.4f}, train_loss: {loss_train:.4f}, eval_loss: {loss_eval:.4f}")
		scheduler.step(loss_eval)

		# save model
		if loss_eval < best_eval_loss:
			best_eval_loss = loss_eval
			logger.info(f"Trained model saved, eval loss: {best_eval_loss:.4f}")
			torch.save(model.state_dict(), os.path.join(args.ckpt_dir, "model.pt"))
		

	# Inference on test set
	# first load-in best model
	model = Seq2Val(**model_args).to(args.device)
	model.load_state_dict(torch.load(os.path.join(args.ckpt_dir, "model.pt")))
	model.eval()
	with torch.no_grad():
		loss_test, acc_test, iter_test = 0, 0, 0
		for x, y in test_loader:
			x, y = x.to(args.device), y.to(args.device)
			# outputs = model(x)
			half_seq_len = x.shape[1] // 2
			outputs = model(x[:, :half_seq_len, :])

			# calculate loss and update parameters
			loss = criterion(outputs, y[:, half_seq_len-1, :])

			# accumulate loss, accuracy
			iter_test += 1
			loss_test += loss.item()
			acc_test += R2_score(outputs, y[:, half_seq_len-1, :])
		
		loss_test /= iter_test
		acc_test /= iter_test

	logger.info("-----------------------------------------------")
	logger.info(f"Test, test_acc: {acc_test:.4f}, test_loss: {loss_test:.4f}")

	# visualize
	visualize_path = os.path.join(args.ckpt_dir, "visualize")
	if not os.path.exists(visualize_path):
		os.mkdir(visualize_path)
	with torch.no_grad():
		predictions = torch.tensor([]).to(args.device)
		truthy = torch.tensor([]).to(args.device)
		
		for x, y in test_loader:
			x, y = x.to(args.device), y.to(args.device)
			middle_point = x.shape[1] // 2
			view_size = x.shape[1] // 2
			for timestep in range(0, middle_point):
				# print(timestep)
				x_input = x[:, timestep:min(timestep+view_size, x.shape[1]), :]
				print("testin-input", flush=True)
				print(x_input[:10], flush=True)
				print(x_input.shape, flush=True)
				y_output = model(x_input)
				print(y_output, flush=True)
				print(y_output.shape, flush=True)
				y_output = y_output.unsqueeze(1)
				print(y_output, flush=True)
				print(y_output.shape, flush=True)
				

				predictions = torch.cat([predictions, (y_output)], dim=1)
				truthy = torch.cat([truthy, y[:, min(timestep+view_size, y.shape[1]) - 1, :].reshape(-1,1,3)], dim=1)
			
			# print(predictions.shape)
			# print(truthy.shape)
			for idx, (i, j) in enumerate(zip(truthy, predictions)):
				# print("asdfadsdfasdfasdfasdf")
				# print(i.shape)
				# print(j.shape)
				visualize_seq2seq2(i.squeeze(), j.squeeze(), visualize_path, idx)
			break
			'''
			dic = dict({
				'truthY':truthy,
				'prediY': predictions
			})
			with open(os.path.join(visualize_path, 'visual.pt'), "wb") as file:
				torch.save(dic, file)
				print("save file to:", os.path.join(visualize_path, 'visual.pt'))
			break
			'''

		# for x, y in test_loader:
		# 	x, y = x.to(args.device), y.to(args.device)
		# 	outputs = model(x)
		# 	for index in range(20):
		# 		visualize_test(x[index, :, :], y[index, :, :], outputs[index, :, :], visualize_path, index)
		# 	break
		


def parse_args() -> Namespace:
	parser = ArgumentParser()
	parser.add_argument(
		"--data_path",
		type=Path,
		help="Directory to the dataset.",
		default="./Data/processed/",
	)

	parser.add_argument(
		"--ckpt_dir",
		type=Path,
		help="Directory to save the model file.",
		default="./Results/",
	)

	# year
	parser.add_argument("--start_year", type=int, default=2017)
	parser.add_argument("--end_year", type=int, default=2017)

	# model
	parser.add_argument("--hidden_dim", type=int, default=128)
	parser.add_argument("--num_layers", type=int, default=2)

	# optimizer
	parser.add_argument("--lr", type=float, default=1e-3)

	# data loader
	parser.add_argument("--batch_size", type=int, default=64)

	# training
	parser.add_argument(
		"--device", type=torch.device, help="cpu, cuda, cuda:0, cuda:1", default="cpu"
	)
	parser.add_argument("--num_epoch", type=int, default=100)

	args = parser.parse_args()
	return args


def get_loggings(ckpt_dir):
	logger = logging.getLogger(name='TASK1-Seq2Val')
	logger.setLevel(level=logging.INFO)
	# set formatter
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	# console handler
	stream_handler = logging.StreamHandler()
	stream_handler.setFormatter(formatter)
	logger.addHandler(stream_handler)
	# file handler
	file_handler = logging.FileHandler(os.path.join(ckpt_dir, "record.log"))
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	return logger


if __name__ == "__main__":
	args = parse_args()
	args.ckpt_dir.mkdir(parents=True, exist_ok=True)
	main(args)