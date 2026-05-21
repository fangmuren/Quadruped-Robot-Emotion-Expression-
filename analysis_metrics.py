def overall_accuracy(rows):
    total = len(rows)
    if total == 0:
        return 0.0
    correct = sum(1 for row in rows if row['emotion'] == row['prediction'])
    return correct / total


def per_class_accuracy(rows):
    counts_by_emotion = {}
    correct_by_emotion = {}

    for row in rows:
        emotion = row['emotion']
        counts_by_emotion[emotion] = counts_by_emotion.get(emotion, 0) + 1
        if row['prediction'] == emotion:
            correct_by_emotion[emotion] = correct_by_emotion.get(emotion, 0) + 1

    return {
        emotion: correct_by_emotion.get(emotion, 0) / count
        for emotion, count in counts_by_emotion.items()
    }


def balanced_accuracy(rows):
    class_accuracy = per_class_accuracy(rows)
    if not class_accuracy:
        return 0.0
    return sum(class_accuracy.values()) / len(class_accuracy)


def confusion_matrix(rows):
    matrix = {}

    for row in rows:
        actual = row['emotion']
        predicted = row['prediction']
        if actual not in matrix:
            matrix[actual] = {}
        matrix[actual][predicted] = matrix[actual].get(predicted, 0) + 1

    return matrix


def confusion_pair_rate(rows, target_emotion, confused_as):
    target_rows = [row for row in rows if row['emotion'] == target_emotion]
    if not target_rows:
        return 0.0
    confused_count = sum(1 for row in target_rows if row['prediction'] == confused_as)
    return confused_count / len(target_rows)


def mean_pad_by_emotion(rows):
    totals = {}
    counts = {}

    for row in rows:
        emotion = row['emotion']
        if emotion not in totals:
            totals[emotion] = {'pleasure': 0.0, 'arousal': 0.0, 'dominance': 0.0}
            counts[emotion] = 0
        totals[emotion]['pleasure'] += row['pleasure']
        totals[emotion]['arousal'] += row['arousal']
        totals[emotion]['dominance'] += row['dominance']
        counts[emotion] += 1

    return {
        emotion: {
            'pleasure': values['pleasure'] / counts[emotion],
            'arousal': values['arousal'] / counts[emotion],
            'dominance': values['dominance'] / counts[emotion],
        }
        for emotion, values in totals.items()
    }
