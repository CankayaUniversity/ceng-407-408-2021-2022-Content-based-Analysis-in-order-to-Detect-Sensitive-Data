from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import tensorflow_text
import tensorflow_hub
import tensorflow
import pandas
import numpy

epochs = 5
seed = 1337
init_lr = 1e-5
batch_size = 32
tfhub_handle_encoder = "https://tfhub.dev/google/LaBSE/2"
tfhub_handle_preprocess = "https://tfhub.dev/google/universal-sentence-encoder-cmlm/multilingual-preprocess/2"

def build_model():
    text_input = tensorflow.keras.layers.Input(shape = (), dtype = tensorflow.string)
    preprocessing_layer = tensorflow_hub.KerasLayer(tfhub_handle_preprocess)
    encoder_inputs = preprocessing_layer(text_input)
    encoder = tensorflow_hub.KerasLayer(tfhub_handle_encoder, trainable = True)
    outputs = encoder(encoder_inputs)
    net = outputs["pooled_output"]
    net = tensorflow.keras.layers.Dropout(0.1)(net)
    net = tensorflow.keras.layers.Dense(1, activation = "sigmoid")(net)
    return tensorflow.keras.Model(text_input, net)

if __name__ == "__main__":
    tensorflow.config.set_visible_devices([], "GPU")
    df = pandas.read_csv("data.csv")
    X = df["plain_text"]
    y = df["overall_classification"].astype(numpy.float32)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = seed)
    model = build_model()
    model.summary()
    metrics = tensorflow.metrics.BinaryAccuracy()
    loss = tensorflow.keras.losses.BinaryCrossentropy()
    steps_per_epoch = X_train.shape[0] / batch_size
    num_train_steps = steps_per_epoch * epochs
    num_warmup_steps = int(0.1 * num_train_steps)
    optimizer = tensorflow.keras.optimizers.Adam(init_lr)
    model.compile(optimizer = optimizer, loss = loss, metrics = metrics)
    model.fit(X_train, y_train, validation_data = (X_test, y_test), epochs = epochs)
    model.save("dlp_model")
    print(classification_report(y_train, model.predict(X_train) >= 0.5))
    print(classification_report(y_test, model.predict(X_test) >= 0.5))
