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
import time
import pickle

class ML_Model(Enum):
    KNN = 1
    RANDOM_FOREST = 2
    SVM = 3
    XGBOOST = 4

def preprocessing_stats(train, test):
    # Preprocessing
    data_train = train.drop(columns=['is_attack'])
    label_train = train['is_attack']
    
    feature_names = data_train.columns

    data_test = test.drop(columns=['is_attack'])
    label_test = test['is_attack']

    # Standardizing the data
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data_train)
    data_test = scaler.transform(data_test)

    return data_train, data_test, label_train, label_test, feature_names

# it takes history_batch and returns data_train, data_test, label_train, label_test
def preprocessing_batches(train, test):
    # Drop non-numeric columns
    data_train = train.drop(columns=['timestamp', 'flow_table_stats', 'removed_table_stats', 'flow_table_stats_durations', 'removed_table_stats_durations', 'is_attack'])
    label_train = train['is_attack']

    feature_names = data_train.columns
    
    data_test = test.drop(columns=['is_attack'])
    label_test = test['is_attack']


    # Standardizing the data
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data_train)
    data_test = scaler.transform(data_test)

    return data_train, data_test, label_train, label_test, feature_names

def apply_model(data_train, data_test, label_train, label_test, model_type, feature_names, is_batch):
    model = None
    model_filename = ""
    if (is_batch):
        model_filename = f"history_batches_ml_models/{model_type.name.lower()}_model.pkl"
    else:
        model_filename = f"flow_rules_ml_models/{model_type.name.lower()}_model.pkl"
    
    # Check if the model file exists, if not, train and save the model
    try:
        with open(model_filename, 'rb') as file:
            model = pickle.load(file)
        print(f"Loaded {model_type.name} model from {model_filename}")
    
    # if file does not exists, train the model and save it under the ml_models folder
    except FileNotFoundError:
        start_time = time.time()
        if model_type == ML_Model.KNN:
            model = KNeighborsClassifier(n_neighbors=5)
        elif model_type == ML_Model.RANDOM_FOREST:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
        elif model_type == ML_Model.SVM:
            model = SVC(kernel='linear', random_state=42)
        else:
            model = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=42)

        model.fit(data_train, label_train)
        with open(model_filename, 'wb') as file:
            pickle.dump(model, file)
        print(f"Saved {model_type.name} model to {model_filename}")
        print(model_type.name + " training time: " + str(time.time() - start_time))

    prediction = model.predict(data_test)
    print(model_type.name + " Accuracy:", accuracy_score(label_test, prediction))
    print(classification_report(label_test, prediction))
    print(model_type.name + " Confusion Matrix:\n", confusion_matrix(label_test, prediction))
    
    feature_importance(model_type, model, feature_names)

def feature_importance(model_type, model, feature_names):
    # Feature importance for Random Forest
    if model_type == ML_Model.RANDOM_FOREST:
        importances = model.feature_importances_
        feature_importance = pd.Series(importances, index=feature_names).sort_values(ascending=False)
        print(model_type.name + " Feature Importance:\n", feature_importance)

    # Feature importance for SVM
    if model_type == ML_Model.SVM:
        if model.kernel == 'linear':
            importances = np.abs(model.coef_[0])
            feature_importance = pd.Series(importances, index=feature_names).sort_values(ascending=False)
            print(model_type.name + " Feature Importance:\n", feature_importance)

    # Feature importance for XGBoost
    if model_type == ML_Model.XGBOOST:
        importances = model.feature_importances_
        feature_importance = pd.Series(importances, index=feature_names).sort_values(ascending=False)
        print(model_type.name + " Feature Importance:\n", feature_importance)

# it creates model stats
def create_model_stats(train, test, is_batch):
    print("Run ML models for history_batches? " + str(is_batch))
    data_train, data_test, label_train, label_test, feature_names = None, None, None, None, None
    if (is_batch):
        data_train, data_test, label_train, label_test, feature_names = preprocessing_batches(train, test)
    else:
        data_train, data_test, label_train, label_test, feature_names = preprocessing_stats(train, test)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.KNN, feature_names, is_batch)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.RANDOM_FOREST, feature_names, is_batch)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.SVM, feature_names, is_batch)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.XGBOOST, feature_names, is_batch)



is_batch = False
test_path = 'test_data/test_data_new1.csv'
train_path = 'train_data/train_data_new1.csv'
train_data = pd.read_csv(train_path)
test_data = pd.read_csv(test_path)
create_model_stats(train_data, test_data, is_batch)
