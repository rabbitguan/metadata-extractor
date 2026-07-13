# 元数据接口人工测试报告

- 报告生成时间：2026-07-13 13:46:29
- 结果来源：`tests\cases\register_cases.csv`、`tests\cases\query_cases.csv`
- 最近编辑时间：2026-07-13 13:23:36
- 总用例数：39
- 通过：23
- 不通过：16
- 未填写：0

## /register 人工测试结果

| 用例 | 类别 | 输入 | 预期 | 人工结论 | 原因 | 编辑时间 |
|---|---|---|---|---|---|---|
| R006：URL 为空 | 异常 |  | 输入 URL 模式但 URL 为空时应返回 Missing URL 错误 | 通过 | 无 | 2026-07-13 12:21:11 |
| R007：register https://www.nhepsdc.cn/resource/photon/heps/b7 | 前端捕获 | https://www.nhepsdc.cn/resource/photon/heps/b7 | 应返回元数据结果，并包含资源标题或核心内容：高能同步辐射光源硬X射线成像线站数据（正在建设中） | 不通过 | 英文未正确提取 | 2026-07-12 23:50:10 |
| R008：register https://www.nhepsdc.cn/resource/photon/Other/dataset-20260120111231 | 前端捕获 | https://www.nhepsdc.cn/resource/photon/Other/dataset-20260120111231 | 应返回元数据结果，并包含资源标题或核心内容：劳厄衍射数据_CaSTS-S | 不通过 | 没有提取出v3.0；英文未正确提取 | 2026-07-12 23:50:21 |
| R009：register https://vsso.nssdc.ac.cn/nssdc_zh/html/vssoinfo.html?16242 | 前端捕获 | https://vsso.nssdc.ac.cn/nssdc_zh/html/vssoinfo.html?16242 | 应返回元数据结果，并包含资源标题或核心内容：中国旱区多源降水融合数据集（XGB-RF） | 不通过 | 工作单位、引用格式不对；数据量显示可以再优化；英文未正确显示 | 2026-07-12 23:25:43 |
| R010：register https://vsso.nssdc.ac.cn/nssdc_zh/html/vssoinfo.html?16220 | 前端捕获 | https://vsso.nssdc.ac.cn/nssdc_zh/html/vssoinfo.html?16220 | 应返回元数据结果，并包含资源标题或核心内容：基于张衡一号卫星的电离层 3D电子密度观测模型数据集 | 不通过 | 工作单位、引用格式不对；数据量显示可以再优化；英文未正确显示 | 2026-07-12 23:26:15 |
| R011：register https://nadc.china-vo.org/res/r100451/ | 前端捕获 | https://nadc.china-vo.org/res/r100451/ | 应返回元数据结果，并包含资源标题或核心内容：LAMOST光谱巡天第七次数据发布第2.0版 中分辨率巡天 | 不通过 | 英文提取不对 | 2026-07-12 23:51:43 |
| R012：register https://www.noda.ac.cn/datasharing/datasetDetails/6a51f07f6e9d28541b592582 | 前端捕获 | https://www.noda.ac.cn/datasharing/datasetDetails/6a51f07f6e9d28541b592582 | 应返回元数据结果，并包含资源标题或核心内容：GF3B satellite remote sensing image dataset of flood stricken areas in Nanning, Guangxi on July 9, 2026 | 不通过 | 默认返回了英文的；空间范围不对 | 2026-07-13 00:02:53 |
| R013：register https://datacenter.chinare.org.cn/data-center/metadata?id=f6b318b5-1ba7-46b8-9566-b16728db0989 | 前端捕获 | https://datacenter.chinare.org.cn/data-center/metadata?id=f6b318b5-1ba7-46b8-9566-b16728db0989 | 应返回元数据结果，并包含资源标题或核心内容：中国第14次南极科学考察(1997-1998)长城站常规气象观测数据 | 不通过 | 学科 长城站 不应进入 | 2026-07-13 00:30:35 |
| R014：register https://data.tpdc.ac.cn/zh-hans/data/b0f1d740-0928-4c47-8085-11f55d16f735/ | 前端捕获 | https://data.tpdc.ac.cn/zh-hans/data/b0f1d740-0928-4c47-8085-11f55d16f735/ | 应返回元数据结果，并包含资源标题或核心内容：华北平原农作物种植区分布图（2001-2018） | 不通过 | 创建者机构、邮箱不对；英文有问题；资助项目的分隔符有问题 | 2026-07-13 00:33:19 |
| R015：register https://www.nesdc.org.cn/sdo/detail?id=60f68d757e28174f0e7d8d49 | 前端捕获 | https://www.nesdc.org.cn/sdo/detail?id=60f68d757e28174f0e7d8d49 | 应返回元数据结果，并包含资源标题或核心内容：2000-2022年中国30米年最大NDVI数据集 | 不通过 | 学科错误出现“团队” | 2026-07-13 01:53:05 |
| R016：register https://www.ncdc.ac.cn/portal/metadata/59e517ca-aaf6-44f0-8676-16e647f4f426 | 前端捕获 | https://www.ncdc.ac.cn/portal/metadata/59e517ca-aaf6-44f0-8676-16e647f4f426 | 应返回元数据结果，并包含资源标题或核心内容：2017-2019年藏东南 松宗曲宗臧布 冰川径流观测数据 | 不通过 | 差英文 | 2026-07-13 12:14:02 |
| R017：register https://www.geodata.cn/main/face_science_detail?typeName=face_science&guid=274461948639522 | 前端捕获 | https://www.geodata.cn/main/face_science_detail?typeName=face_science&guid=274461948639522 | 应返回元数据结果，并包含资源标题或核心内容：全球10km高分辨率无缝逐日XCH4数据集(2003-2020年) | 不通过 | cstr未提取到，时间范围奇怪 | 2026-07-13 03:42:35 |
| R018：register https://www.ncmi.cn/phda/dataDetails.do?id=CSTR:A0006.11.A0001.202006.001024 | 前端捕获 | https://www.ncmi.cn/phda/dataDetails.do?id=CSTR:A0006.11.A0001.202006.001024 | 应返回元数据结果，并包含资源标题或核心内容：北京市提供新冠病毒核酸检测服务的医疗卫生机构数据集 | 不通过 | 前端未显示cstr，应该是那个js的bug修完合并的时候丢失了 | 2026-07-13 12:29:00 |
| R019：register https://arxiv.org/abs/2303.14524 | 前端捕获 | https://arxiv.org/abs/2303.14524 | 应返回元数据结果，并包含资源标题或核心内容：Chat-REC: Towards Interactive and Explainable LLMs-Augmented Recommender System | 通过 | arxiv | 2026-07-13 12:30:23 |
| R020：register https://www.nbsdc.cn/general/dataDetail?id=63f4697887c4324cadaeda85&type=1 | 前端捕获 | https://www.nbsdc.cn/general/dataDetail?id=63f4697887c4324cadaeda85&type=1 | 应返回元数据结果，并包含资源标题或核心内容：东锅660MW高效超超临界循环流化床锅炉水动力计算 | 不通过 | 电子邮箱、发布日期来源不明，引用格式不对，资助者有个value | 2026-07-13 12:43:26 |
| R021：register https://www.agridata.cn/data.html#/datadetail?id=292598 | 前端捕获 | https://www.agridata.cn/data.html#/datadetail?id=292598 | 应返回元数据结果，并包含资源标题或核心内容：奶牛个体头部多模态图像深度学习训练数据集 | 通过 | 返回元数据结果，标题/名称包含：孙伟，孔繁涛 | 2026-07-13 13:11:04 |
| R022：register https://www.forestdata.cn/dataDetail.html?id=a47fe3ac-b57d-4a35-81ba-513e15e576d5 | 前端捕获 | https://www.forestdata.cn/dataDetail.html?id=a47fe3ac-b57d-4a35-81ba-513e15e576d5 | 应返回元数据结果，并包含资源标题或核心内容：西南高山峡谷区2000~2022年逐年水土流失风险数据 | 不通过 | 学科、文件内容、使用说明不准确 | 2026-07-13 13:17:06 |
| R023：register https://mds.nmdis.org.cn/pages/dataViewDetail.html?dataSetId=35 | 前端捕获 | https://mds.nmdis.org.cn/pages/dataViewDetail.html?dataSetId=35 | 应返回元数据结果，并包含资源标题或核心内容：水位综合数据集 | 通过 | 返回元数据结果，标题/名称包含：国家海洋信息中心 | 2026-07-13 13:23:36 |

## /query 人工测试结果

| 用例 | 类别 | 输入 | 预期 | 人工结论 | 原因 | 编辑时间 |
|---|---|---|---|---|---|---|
| Q001：合法 DOI 查询 | DOI | 10.48550/arXiv.2303.14524 | 应解析 DOI 并返回至少一个 status=ok 的 items 结果，payload 中应包含 arXiv 相关元数据 | 通过 | 无 | 2026-07-13 12:21:38 |
| Q004：DOI 和 CSTR 混合查询 | 多标识符 | ["10.48550/arXiv.2303.14524","CSTR:14804.11.05.70.00079-V01"] | 应同时处理 DOI 和 CSTR，items 中至少一个结果成功，并保留每个标识符的处理状态 | 通过 | 无 | 2026-07-13 12:31:12 |
| Q005：非法 identifier | 异常 | abc123 | 输入无法识别为 DOI/CSTR 的字符串时应返回 No DOI or CSTR identifier found | 通过 | 无 | 2026-07-13 12:31:27 |
| Q006：query DOI:10.12402/photon/laue/dataset-20260120111231 | 前端捕获 | DOI:10.12402/photon/laue/dataset-20260120111231 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 与网页一致 | 2026-07-12 22:47:34 |
| Q007：query CSTR:17081.11.photon.laue.dataset-20260120111231 | 前端捕获 | CSTR:17081.11.photon.laue.dataset-20260120111231 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：CSTR:17081.11.photon.laue.dataset-20260120111231，与网页结果一致 | 2026-07-12 22:34:07 |
| Q008：query CSTR:17081.11.photon.heps.b7 | 前端捕获 | CSTR:17081.11.photon.heps.b7 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：CSTR:17081.11.photon.heps.b7=error，正常，未登记cstr | 2026-07-12 22:34:36 |
| Q009：query CSTR:14804.11.01.60.00023-V01 | 前端捕获 | CSTR:14804.11.01.60.00023-V01 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 与原网页一致 | 2026-07-12 22:40:46 |
| Q010：query DOI: 10.12176/01.60.00023-V01 | 前端捕获 | DOI: 10.12176/01.60.00023-V01 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 与网页一致 | 2026-07-12 22:47:20 |
| Q011：query CSTR:14804.11.01.06.00143-V01 | 前端捕获 | CSTR:14804.11.01.06.00143-V01 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：CSTR:14804.11.01.06.00143-V01=ok | 2026-07-12 23:26:30 |
| Q012：query DOI: 10.12176/01.06.00143-V01 | 前端捕获 | DOI: 10.12176/01.06.00143-V01 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：10.12176/01.06.00143-V01=ok | 2026-07-12 23:28:02 |
| Q013：query CSTR:11379.11.100451 | 前端捕获 | CSTR:11379.11.100451 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：CSTR:11379.11.100451=ok | 2026-07-12 23:54:09 |
| Q014：query DOI: 10.12149/100451 | 前端捕获 | DOI: 10.12149/100451 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：10.12149/100451=ok | 2026-07-12 23:54:24 |
| Q015：query DOI: 10.11878/db.202607.000041 | 前端捕获 | DOI: 10.11878/db.202607.000041 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：10.11878/db.202607.000041=error，正常 | 2026-07-13 00:00:13 |
| Q016：query CSTR:10441.11.202607.000041 | 前端捕获 | CSTR:10441.11.202607.000041 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：CSTR:10441.11.202607.000041=ok | 2026-07-13 00:00:41 |
| Q017：query DOI: 10.11888/Terre.tpdc.301311 | 前端捕获 | DOI: 10.11888/Terre.tpdc.301311 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：10.11888/Terre.tpdc.301311=ok | 2026-07-13 00:34:16 |
| Q018：query DOI: 10.12072/ncdc.BoMi.db0006.2020 | 前端捕获 | DOI: 10.12072/ncdc.BoMi.db0006.2020 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：10.12072/ncdc.BoMi.db0006.2020=ok | 2026-07-13 03:30:52 |
| Q019：query CSTR:11738.11.ncdc.BoMi.2020.16 | 前端捕获 | CSTR:11738.11.ncdc.BoMi.2020.16 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：CSTR:11738.11.ncdc.BoMi.2020.16=ok | 2026-07-13 03:30:59 |
| Q020：query DOI10.12009/YRDR.2026.1008.ver1.db | 前端捕获 | DOI10.12009/YRDR.2026.1008.ver1.db | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 无 | 2026-07-13 12:21:01 |
| Q021：query 10.48550/arXiv.2303.14524 | 前端捕获 | 10.48550/arXiv.2303.14524 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 通过 | 标识符查询返回 1 项：10.48550/arXiv.2303.14524=ok | 2026-07-13 12:30:26 |
| Q022：query CSTR:16666.11.nbsdc.eppl30tx | 前端捕获 | CSTR:16666.11.nbsdc.eppl30tx | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 不通过 | 与原网页不一致，可能是共性问题 | 2026-07-13 12:44:23 |
| Q023：query CSTR:17058.11.sciencedb.agriculture.00184 | 前端捕获 | CSTR:17058.11.sciencedb.agriculture.00184 | 应返回标识符查询结果，至少包含 items 列表和每个标识符的处理状态。 | 不通过 | 与原网页不对应是正常的，但通过scids兜底查出来有一些格式错误（学科是数字编码），可以改一下 | 2026-07-13 13:11:51 |
