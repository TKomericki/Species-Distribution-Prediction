from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.svm import OneClassSVM
import numpy as np


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def generate_model(x):
    scaler = StandardScaler()
    scaler.fit(x)
    x = scaler.transform(x)

    pca = PCA(n_components=2)
    pca.fit(x)
    x = pca.transform(x)

    model = OneClassSVM(kernel='sigmoid', max_iter=5000, nu=0.01)
    model.fit(x)

    return scaler, pca, model


def predict(x_predict, scaler, pca, model):
    x_predict = pca.transform(scaler.transform(x_predict))
    return [sigmoid(x) for x in model.decision_function(x_predict)]
