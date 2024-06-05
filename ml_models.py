import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
# import xgboost as xgb
from enum import Enum
import pickle

class ML_Model(Enum):
    KNN = 1
    RANDOM_FOREST = 2
    SVM = 3
    XGBOOST = 4
def preprocessing_batches(data):
    # Drop non-numeric columns
    # if is_attack column exists in the data_test, drop it
    label_train = data['is_attack']
    data = data.drop(columns=['timestamp', 'flow_table_stats', 'removed_table_stats', 'flow_table_stats_durations', 'removed_table_stats_durations', 'is_attack'])
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data)
    return data_train, label_train

def preprocessing_stats(data):
    # Drop non-numeric columns
    # if is_attack column exists in the data_test, drop it
    label_train = data['is_attack']
    data = data.drop(columns=['is_attack'])
    print(data.columns)
    scaler = StandardScaler()
    data_train = scaler.fit_transform(data)
    return data_train, label_train
# it creates model stats

def get_model(model_type, is_batch):
    model = None
    model_filename = ""
    if (is_batch):
        model_filename = f"history_batches_ml_models/{model_type.name.lower()}_model.pkl"
    else:
        model_filename = f"flow_rules_ml_models/{model_type.name.lower()}_model.pkl"
    print('buradayiz')
    # Check if the model file exists, if not, train and save the model
    try:
        with open(model_filename, 'rb') as file:
            model = pickle.load(file)
        print(f"Loaded {model_type.name} model from {model_filename}")
        # TODO call it if it is labeled
        ## if is_attack column exists in the data_test, drop it
        return model
        #data_test = StandardScaler().transform(data_test)
    # if file does not exists, train the model and save it under the ml_models folder
    except FileNotFoundError:
        if model_type == ML_Model.KNN:
            model = KNeighborsClassifier(n_neighbors=5)
        elif model_type == ML_Model.RANDOM_FOREST:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
        elif model_type == ML_Model.SVM:
            model = SVC(kernel='linear', random_state=42)

        train_path = 'train_data/train_data_new1.csv'
        train_data = pd.read_csv(train_path, index_col=0)
        data_train, label_train = None, None
        if (is_batch):
            #data_train, data_test_2, label_train, feature_names = preprocessing_batches_no_label(train_data, data_test)
            data_train, label_train = preprocessing_batches(train_data)
        else:
            #TODO call the commented one if your data has no label
            # data_train, data_test, label_train, feature_names = preprocessing_stats_no_label(train_data, data_test)
            data_train, label_train = preprocessing_stats(train_data)
        model.fit(data_train, label_train)
        with open(model_filename, 'wb') as file:
            pickle.dump(model, file)
        print(f"Saved {model_type.name} model to {model_filename}")
        return model