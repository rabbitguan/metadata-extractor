import json
import re


def is_empty_value(value):
    """判断值是否为空：只有 None/null 和空字符串算空"""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def filter_response(data):
    """
    过滤响应数据：所有字段都是必选，没值就显示"未提取到"
    
    参数:
        data: LLM 返回的原始数据
    
    返回:
        过滤后的数据，所有空值都被替换为"未提取到"
    """
    if not isinstance(data, dict):
        return data
    
    def filter_object(obj):
        """递归处理对象，将所有空值替换为"未提取到" """
        if not isinstance(obj, dict):
            return obj
        
        result = {}
        
        for field_key, field_value in obj.items():
            # 处理嵌套对象
            if isinstance(field_value, dict):
                filtered_nested = filter_object(field_value)
                # 如果嵌套对象过滤后为空，也显示"未提取到"
                if filtered_nested:
                    result[field_key] = filtered_nested
                else:
                    result[field_key] = "未提取到"
                continue
            
            # 处理列表
            if isinstance(field_value, list):
                if not is_empty_value(field_value):
                    result[field_key] = field_value
                else:
                    result[field_key] = "未提取到"
                continue
            
            # 处理标量值：所有字段都是必选，空值显示"未提取到"
            if is_empty_value(field_value):
                result[field_key] = "未提取到"
            else:
                result[field_key] = field_value
        
        return result
    
    return filter_object(data)


def apply_requirement_filter(data, schema_name=None):
    """
    应用字段要求过滤（简化版：所有字段必选）
    
    参数:
        data: LLM 返回的原始数据
        schema_name: 元数据类型（保留参数以兼容旧调用，但不使用）
    
    返回:
        过滤后的数据
    """
    return filter_response(data)