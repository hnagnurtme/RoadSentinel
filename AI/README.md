# RoadSentinel - AI Module

This directory contains the Artificial Intelligence components for RoadSentinel, focusing on driver state monitoring and distracted driving detection.

## 🧠 Overview

The AI module is responsible for analyzing visual data to detect:
- Distracted driving behaviors (e.g., using a phone, reaching behind, talking to passengers).
- Drowsiness and fatigue.
- Seatbelt usage.

## 📁 Structure

- `data/`: Contains datasets used for training and evaluation (ignored by git).
  - `raw/`: Raw data, including the State Farm Distracted Driver Detection dataset.
  - `processed/`: Data after cleaning and preprocessing.
- `models/`: Saved model weights and architecture definitions (ignored by git).
- `notebooks/`: Jupyter notebooks for experimentation and analysis.
- `src/`: Training and inference scripts.

## 🚀 Getting Started

1. **Environment Setup**:
   It is recommended to use a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Data Preparation**:
   Place your datasets in `data/raw/` and run the preprocessing scripts.

3. **Training**:
   Refer to the scripts in `src/` or notebooks in `notebooks/` for model training.

## 📊 Dataset

Currently utilizing:
- **State Farm Distracted Driver Detection**: A dataset of images representing various distracted driving postures.

## 🛠 Tech Stack

- **Python**
- **TensorFlow / PyTorch**
- **OpenCV**
- **Scikit-learn**
- **Pandas/NumPy**
