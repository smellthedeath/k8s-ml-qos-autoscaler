import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


DATASET = "dataset/final_ml_training.csv"


df = pd.read_csv(DATASET)


# Features used by ML
features = [
    "cpu_percent",
    "total_memory_mi",
    "requests",
    "failed_rate_percent",
    "avg_latency_ms",
    "p95_latency_ms"
]


X = df[features]

y = df["target_replicas"]


# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)


models = {

    "Decision Tree": DecisionTreeClassifier(
        max_depth=5,
        random_state=42,
        class_weight="balanced"
    ),

    "Random Forest": RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42,
        class_weight="balanced"
    )
}


for name, model in models.items():

    print("\n======================")
    print(name)
    print("======================")


    model.fit(
        X_train,
        y_train
    )


    prediction = model.predict(
        X_test
    )


    print(
        "\nAccuracy:"
    )

    print(
        round(
            accuracy_score(
                y_test,
                prediction
            ),
            3
        )
    )


    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            prediction,
            zero_division=0
        )
    )


    print(
        "\nConfusion Matrix:"
    )

    print(
        confusion_matrix(
            y_test,
            prediction
        )
    )


    print(
        "\nFeature Importance:"
    )


    for feature, value in zip(
        features,
        model.feature_importances_
    ):
        print(
            f"{feature}: {value:.3f}"
        )
