from collections import defaultdict


def merge_answers(answers):
    """
    合并多个答案，统计每个字段最常见值并标记。

    参数:
        answers: 包含多个条目的列表，每个条目为符合格式的字典

    返回:
        处理后的结果字典，每个字段包含值和标记（0:问号, 1:正确, 2:错误）
    """
    field_counts = defaultdict(lambda: defaultdict(int))

    def count_fields(data, parent_key=''):
        if isinstance(data, dict):
            for key, value in data.items():
                if parent_key == '' and key == '扩展信息':
                    continue

                current_key = f"{parent_key}.{key}" if parent_key else key
                if isinstance(value, dict):
                    count_fields(value, current_key)
                else:
                    # 只统计纯标量值（字符串、数字等），跳过 list/dict
                    if value is not None and value != "null" and not isinstance(value, (list, dict)):
                        field_counts[current_key][value] += 1

    for ans in answers:
        count_fields(ans)

    result = {}

    def build_result(key, value, label):
        parts = key.split('.')
        current = result
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                current[part] = {"value": value, "label": label}
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]

    for field, counts in field_counts.items():
        total = sum(counts.values())
        most_common = max(counts.items(), key=lambda item: item[1])
        value, count = most_common

        if total == 1:
            label = 0
        elif count / total > 0.5:
            label = 1
        else:
            label = 2

        build_result(field, value, label)

    return result