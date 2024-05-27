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

class ML_Model(Enum):
    KNN = 1
    RANDOM_FOREST = 2
    SVM = 3
    XGBOOST = 4

# it takes history_batch and returns data_train, data_test, label_train, label_test
def preprocessing_batches(history_batch):
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

def preprocessing_stats_no_label(train, test):

    # Preprocessing
    data_train = train.drop(columns=['is_attack'])
    label_train = train['is_attack']

    # Standardizing the data
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data_train)
    data_test = scaler.transform(test)

    return data_train, data_test, label_train

def apply_model(data_train, data_test, label_train, label_test, model_type, feature_names):
    model = None
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
    prediction = model.predict(data_test)
    print(model_type.name + " time: " + str(time.time() - start_time))
    print(model_type.name + " Accuracy:", accuracy_score(label_test, prediction))
    print(classification_report(label_test, prediction))
    print(model_type.name + " Confusion Matrix:\n", confusion_matrix(label_test, prediction))
    
    feature_importance(model_type, model, feature_names)

def apply_model_no_label(data_train, data_test, label_train, model_type):
    model = None
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
    prediction = model.predict(data_test)
    print(model_type.name + " time: " + str(time.time() - start_time))
    print(prediction)
    

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


def create_model_batches(history_batch):
    data_train, data_test, label_train, label_test, feature_names = preprocessing_batches(history_batch)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.KNN, feature_names)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.RANDOM_FOREST, feature_names)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.SVM, feature_names)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.XGBOOST, feature_names)
    

def create_model_stats(train, test):
    data_train, data_test, label_train, label_test, feature_names = preprocessing_stats(train, test)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.KNN, feature_names)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.RANDOM_FOREST, feature_names)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.SVM, feature_names)
    apply_model(data_train, data_test, label_train, label_test, ML_Model.XGBOOST, feature_names)

def create_model_no_label(train, test):
    data_train, data_test, label_train  = preprocessing_stats_no_label(train, test)
    apply_model_no_label(data_train, data_test, label_train, ML_Model.KNN)
    apply_model_no_label(data_train, data_test, label_train, ML_Model.RANDOM_FOREST)
    apply_model_no_label(data_train, data_test, label_train, ML_Model.SVM)
    apply_model_no_label(data_train, data_test, label_train, ML_Model.XGBOOST)

def load_model():
    return None

is_supervised = True
if (is_supervised):
    train_data = pd.read_csv('data/train_flow_table.csv')
    test_data = pd.read_csv('data/test_flow_table.csv')
    create_model_stats(train_data, test_data)
else:
    train_data = pd.read_csv('data/train_flow_table.csv')
    test_data = pd.read_csv('data/yeni_flow_table_1.csv')
    create_model_no_label(train_data, test_data)
