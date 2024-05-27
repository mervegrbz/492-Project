import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from enum import Enum

class ML_Model(Enum):
    KNN = 1
    RANDOM_FOREST = 2
    SVM = 3
    XGBOOST = 4

# it takes history_batch and returns data_train, data_test, label_train, label_test
def preprocessing_data(history_batch):
    # Drop non-numeric columns
    numeric_data = history_batch.drop(columns=['timestamp', 'flow_table_stats', 'removed_table_stats', 'flow_table_stats_durations', 'removed_table_stats_durations'])

    # Preprocessing
    X = numeric_data.drop(columns=['is_attack'])
    y = numeric_data['is_attack']

    # Splitting the data into training and testing sets
    data_train, data_test, label_train, label_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Standardizing the data
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data_train)
    data_test = scaler.transform(data_test)

    return data_train, data_test, label_train, label_test

def apply_model(data_train, data_test, label_train, label_test, model_type):
    model = None
    if model_type == ML_Model.KNN:
        model = KNeighborsClassifier(n_neighbors=5)
    elif model_type == ML_Model.RANDOM_FOREST:
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == ML_Model.SVM:
        model = SVC(kernel='linear', random_state=42)
    else:
        model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)

    model.fit(data_train, label_train)
    prediction = model.predict(data_test)
    print(model_type.name + " Accuracy:", accuracy_score(label_test, prediction))
    print(classification_report(label_test, prediction))
    print(model_type.name + " Confusion Matrix:\n", confusion_matrix(label_test, prediction))

def create_model(history_batch):
    data_train, data_test, label_train, label_test = preprocessing_data(history_batch)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.KNN)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.RANDOM_FOREST)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.SVM)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.XGBOOST)
    
def load_model():
    return None