import requests

# API的完整URL
url = "http://021.node.internetapi.cn:21030/SCIDE/SCManager"

def doi_identifier(id):
    params = {
        "action": "executeContract",
        "contractID": "BDBrowser",
        "operation": "sendRequestDirectly",
        # arg参数是一个JSON字符串
        "arg": '{"doipUrl":"tcp://8.130.140.101:21051","op":"ListOps","id":"' + id + '"}'
    }
    try:
        # 发送GET请求
        response = requests.get(url, params=params)
        # 检查请求是否成功（状态码200表示成功）
        if response.status_code == 200:
            return response.text  # 返回结果
        else:
            print(f"调用失败，状态码：{response.status_code}")
    except Exception as e:
        print(f"调用出错：{str(e)}")

def cstr_identifier(id):
    params = {
        "action": "executeContract",
        "contractID": "BDBrowser",
        "operation": "sendRequestDirectly",
        # arg参数是一个JSON字符串
        "arg": '{"doipUrl":"tcp://8.130.140.101:21051","op":"ListOps","id":"' + id + '"}'
    }
    try:
        # 发送GET请求
        response = requests.get(url, params=params)
        
        # 检查请求是否成功（状态码200表示成功）
        if response.status_code == 200:
            return response.text  # 返回结果
        else:
            print(f"调用失败，状态码：{response.status_code}")
    except Exception as e:
        print(f"调用出错：{str(e)}")

def patent_identifier(id):
    params = {
        "action": "executeContract",
        "contractID": "BDBrowser",
        "operation": "sendRequestDirectly",
        # arg参数是一个JSON字符串
        "arg": '{"doipUrl":"tcp://8.130.140.101:21051","op":"ListOps","id":"' + id + '"}'
    }
    try:
        # 发送GET请求
        response = requests.get(url, params=params)
        
        # 检查请求是否成功（状态码200表示成功）
        if response.status_code == 200:
            return response.text  # 返回结果
        else:
            print(f"调用失败，状态码：{response.status_code}")
    except Exception as e:
        print(f"调用出错：{str(e)}") 