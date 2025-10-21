import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import Dataset, DataLoader
from ai.transformer_predictor import TransformerAIPredictor, TransformerModel
from models.database import create_tables, get_db, Tick
from sqlalchemy.orm import Session
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Define a custom dataset
class PriceDataset(Dataset):
    def __init__(self, prices, seq_length=10):
        self.prices = prices
        self.seq_length = seq_length

    def __len__(self):
        return len(self.prices) - self.seq_length - 1

    def __getitem__(self, idx):
        # Input sequence
        src_sequence = torch.tensor(self.prices[idx:idx + self.seq_length]).float()
        # Target sequence (shifted by one)
        tgt_sequence = torch.tensor(self.prices[idx + 1:idx + self.seq_length + 1]).float()
        return src_sequence, tgt_sequence

def train_transformer_model(model_path='transformer_model.pth', seq_length=10, batch_size=32, num_epochs=10):
    """
    Train the Transformer model using historical price data from the database.
    """
    # Fetch historical price data from the database
    db_session = next(get_db())
    prices = [tick.price for tick in db_session.query(Tick).order_by(Tick.timestamp).all()]
    db_session.close()

    # Prepare the dataset and data loader
    dataset = PriceDataset(prices, seq_length)
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    # Initialize the model, loss function, and optimizer
    input_size = seq_length  # Dimension of the input sequence
    hidden_size = 256  # Hidden layer size
    num_layers = 2  # Number of transformer layers
    output_size = seq_length  # Dimension of the output sequence

    model = TransformerModel(input_size, hidden_size, num_layers, output_size)
    criterion = nn.MSELoss()  # Mean Squared Error loss
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # Training loop
    model.train()  # Set the model to training mode
    for epoch in range(num_epochs):
        total_loss = 0
        for src_seq, tgt_seq in data_loader:
            # Reshape for Transformer: (seq_len, batch_size, num_features)
            # DataLoader provides (batch_size, seq_len), so we permute and add a feature dimension.
            src_seq = src_seq.permute(1, 0).unsqueeze(2) # Shape: (seq_length, batch_size, 1)
            tgt_seq = tgt_seq.permute(1, 0).unsqueeze(2) # Shape: (seq_length, batch_size, 1)

            # Zero the gradients
            optimizer.zero_grad()

            # Forward pass
            output = model(src_seq, tgt_seq)

            # Calculate the loss
            loss = criterion(output, tgt_seq)
            total_loss += loss.item()

            # Backward pass and optimize
            loss.backward()
            optimizer.step()

        # Print the average loss for the epoch
        avg_loss = total_loss / len(data_loader)
        logger.info(f"Epoch [{epoch + 1}/{num_epochs}], Loss: {avg_loss:.4f}")

    # Save the trained model
    torch.save(model.state_dict(), model_path)
    logger.info(f"Trained Transformer model saved to {model_path}")

if __name__ == '__main__':
    # Run the training process
    model_path = 'transformer_model.pth'
    seq_length = 10
    batch_size = 32
    num_epochs = 10

    # Create the database tables
    create_tables()

    # Train the model
    train_transformer_model(model_path, seq_length, batch_size, num_epochs)