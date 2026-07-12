# 元数据提取接口测试报告

- 生成时间：2026-07-12 20:30:08
- 服务地址：`http://127.0.0.1:4000`
- 总用例数：11
- 通过：11
- 失败：0

## /register 测试结果

| 测试例子 | 预期 | 实际 | 结论 |
|---|---|---|---|
| R001：arXiv URL 提取 | HTTP 200；核心元数据；领域元数据；title_non_empty；contains=arXiv | HTTP 200；通过检查：HTTP 200；核心元数据；领域元数据；title_non_empty='Chat-REC: Towards Interactive and Explainable LLMs-Augmented Recommender System'；contains=arXiv；title=Chat-REC: Towards Interactive and Explainable LLMs-Augmented Recommender System | 通过 |
| R002：NCDC 数据集 URL 提取 | HTTP 200；核心元数据；领域元数据；title_non_empty；contains=NCDC | HTTP 200；通过检查：HTTP 200；核心元数据；领域元数据；title_non_empty='湖北巴东试验场实测库水位数据集（2018-2025年）'；contains=NCDC；title=湖北巴东试验场实测库水位数据集（2018-2025年） | 通过 |
| R003：NHEPSDC 高能物理数据 URL 提取 | HTTP 200；核心元数据；领域元数据；title_non_empty；contains=高能 | HTTP 200；通过检查：HTTP 200；核心元数据；领域元数据；title_non_empty='高能同步辐射光源硬X射线成像线站数据（正在建设中）'；contains=高能；title=高能同步辐射光源硬X射线成像线站数据（正在建设中） | 通过 |
| R004：VSSO 空间科学资源 URL 提取 | HTTP 200；核心元数据；领域元数据；title_non_empty | HTTP 200；通过检查：HTTP 200；核心元数据；领域元数据；title_non_empty='微牛冷气推力器工程样机测试数据集数据'；title=微牛冷气推力器工程样机测试数据集数据 | 通过 |
| R005：上传 JSON 文件提取 | HTTP 200；核心元数据；领域元数据；title_non_empty；contains=China Urban Heat Island | HTTP 200；通过检查：HTTP 200；核心元数据；领域元数据；title_non_empty='China Urban Heat Island Observation Dataset 2018-2025'；contains=China Urban Heat Island；title=China Urban Heat Island Observation Dataset 2018-2025 | 通过 |
| R006：URL 为空 | HTTP 400；message=Missing URL | HTTP 400；通过检查：HTTP 400；message='Missing URL'；message=Missing URL | 通过 |

## /query 测试结果

| 测试例子 | 预期 | 实际 | 结论 |
|---|---|---|---|
| Q001：合法 DOI 查询 | HTTP 200；items；items[0].status=ok；any_item_ok；contains=arXiv | HTTP 200；通过检查：HTTP 200；items；items[0].status='ok'；any_item_ok；contains=arXiv；items=10.48550/arXiv.2303.14524:ok | 通过 |
| Q002：VSSO CSTR 查询 | HTTP 200；items；any_item_ok；contains=vsso | HTTP 200；通过检查：HTTP 200；items；any_item_ok；contains=vsso；items=CSTR:14804.11.05.70.00079-V01:ok | 通过 |
| Q003：NCDC CSTR 查询 | HTTP 200；items；any_item_ok；contains=NCDC | HTTP 200；通过检查：HTTP 200；items；any_item_ok；contains=NCDC；items=CSTR:11738.11.NCDC.BNORSG.DB7212.2026:ok | 通过 |
| Q004：DOI 和 CSTR 混合查询 | HTTP 200；items；any_item_ok | HTTP 200；通过检查：HTTP 200；items；any_item_ok；items=10.48550/arXiv.2303.14524:ok, CSTR:14804.11.05.70.00079-V01:ok | 通过 |
| Q005：非法 identifier | HTTP 400；message=No DOI or CSTR identifier found | HTTP 400；通过检查：HTTP 400；message='No DOI or CSTR identifier found'；message=No DOI or CSTR identifier found | 通过 |
