import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import backend  # noqa: E402
import cstr_resolver  # noqa: E402
from extractors import chinare, geodata, nadc, nbsdc, ncdc, ncmi, nesdc, nfgsdc, nhepsdc, noda, tpdc, vsso  # noqa: E402


def test_english_cjk_language_values_are_removed_from_core_and_domain():
    payload = {
        "zh": {
            "核心元数据": {
                "metadatas": [
                    {
                        "titles": [{"lang": "zh", "name": "中文标题"}],
                        "descriptions": [{"lang": "zh", "description": "中文摘要"}],
                        "resource_type": "Dataset",
                    }
                ]
            },
            "数据集基本信息": {"标题": "中文标题", "摘要": "中文摘要"},
        },
        "en": {
            "Core Metadata": {
                "metadatas": [
                    {
                        "titles": [{"lang": "en", "name": "中文标题"}],
                        "descriptions": [{"lang": "en", "description": "中文摘要"}],
                        "keywords": [{"lang": "en", "keyword": ["中文关键词"]}],
                        "resource_type": "Dataset",
                    }
                ]
            },
            "Dataset Basic Information": {"Title": "中文标题", "Abstract": "中文摘要", "Keywords": ["中文关键词"]},
        },
    }

    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    domain_basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert core["titles"] == [{"lang": "zh", "name": "中文标题"}]
    assert core["descriptions"] == [{"lang": "zh", "description": "中文摘要"}]
    assert core["keywords"] == [{"lang": "en", "keyword": ["中文关键词"]}]
    assert domain_basic["标题"] == [{"lang": "zh", "name": "中文标题"}]
    assert domain_basic["摘要"] == [{"lang": "zh", "description": "中文摘要"}]
    assert domain_basic["关键词"] == [{"lang": "en", "keyword": ["中文关键词"]}]


def test_real_english_language_values_are_preserved():
    payload = {
        "zh": {
            "核心元数据": {"metadatas": [{"titles": [{"lang": "zh", "name": "中文标题"}], "resource_type": "Dataset"}]},
            "数据集基本信息": {"标题": "中文标题"},
        },
        "en": {
            "Core Metadata": {"metadatas": [{"titles": [{"lang": "en", "name": "English title"}], "resource_type": "Dataset"}]},
            "Dataset Basic Information": {"Title": "English title"},
        },
    }

    unified = backend._build_unified_metadata(payload)

    assert {"lang": "en", "name": "English title"} in unified["核心元数据"]["metadatas"][0]["titles"]
    assert {"lang": "en", "name": "English title"} in unified["领域元数据"]["metadatas"][0]["数据集基本信息"]["标题"]


def test_deep_english_cjk_language_values_are_removed_without_empty_lists():
    payload = {
        "zh": {
            "资源类型判定": "数据集",
            "数据集基本信息": {"标题": "中文标题"},
        },
        "en": {
            "Resource Type Classification": "Dataset",
            "Dataset Basic Information": {
                "Title": "English title",
                "Dataset Authors": {
                    "Author Name": ["中文作者"],
                    "Affiliation": "中文机构",
                    "Email": "person@example.org",
                },
            },
            "Extension Info": {
                "Data Producer": "中文团队",
                "Telephone": "123456",
            },
        },
    }

    domain = backend._build_unified_metadata(payload)["领域元数据"]["metadatas"][0]

    authors = domain["数据集基本信息"]["数据集作者"]
    assert "作者姓名" not in authors
    assert "工作单位" not in authors
    assert authors["电子邮箱"] == [{"lang": "en", "value": "person@example.org"}]


def test_noisy_subject_terms_are_removed_from_core_and_domain():
    subjects = backend._normalize_subjects(
        [
            {
                "standard_gbt": ["生态学", "长城站", "团队", "17058"],
                "standard_oecd": ["Environmental Sciences", "cs.IR", "101"],
            }
        ]
    )
    domain = backend._normalize_domain_metadata_shape(
        {
            "数据集基本信息": {
                "学科分类": ["生态学", "长城站", "团队", "17058"],
                "主题分类": "长城站",
            }
        },
        "zh",
    )

    assert subjects == [
        {
            "standard_gbt": ["生态学"],
            "standard_oecd": ["Environmental Sciences", "cs.IR"],
        }
    ]
    assert domain["数据集基本信息"]["学科分类"] == ["生态学"]
    assert "主题分类" not in domain["数据集基本信息"]


def test_subject_language_wrappers_drop_numeric_codes():
    domain = backend._normalize_domain_metadata_shape(
        {
            "学科": [
                {"lang": "zh", "value": ["999"]},
                {"lang": "en", "value": [{"standard_gbt": None, "standard_oecd": ["999"]}]},
            ],
            "学科分类": [
                {"lang": "zh", "value": ["生态学", "999"]},
                {"lang": "en", "value": ["Environmental Sciences", "101"]},
            ],
            "主题分类": [
                {"lang": "zh", "value": ["210"]},
                {"lang": "en", "value": ["17058"]},
            ],
        },
        "zh",
    )

    assert "学科" not in domain
    assert "主题分类" not in domain
    assert domain["学科分类"] == [
        {"lang": "zh", "value": ["生态学"]},
        {"lang": "en", "value": ["Environmental Sciences"]},
    ]


def test_already_unified_domain_metadata_is_normalized():
    payload = {
        "核心元数据": {
            "metadatas": [
                {
                    "titles": [{"lang": "zh", "name": "数据集"}],
                    "identifier": "CSTR:17058.11.sciencedb.agriculture.00184",
                    "resource_type": "Dataset",
                }
            ]
        },
        "领域元数据": {
            "metadata_type": "数据集元数据",
            "metadatas": [
                {
                    "学科": [
                        {"lang": "zh", "value": ["210"]},
                        {"lang": "en", "value": [{"standard_gbt": None, "standard_oecd": ["210"]}]},
                    ],
                    "Resource URL": "https://example.org/data",
                    "Dataset Basic Information": {"Identifier": {"type": "CSTR", "identifier": "17058.11.sciencedb.agriculture.00184"}},
                }
            ],
        },
    }

    domain = backend._build_unified_metadata(payload)["领域元数据"]["metadatas"][0]

    assert "学科" not in domain
    assert "Resource URL" not in domain
    assert domain["资源链接"] == "https://example.org/data"
    assert domain["数据集基本信息"]["标识符"] == "CSTR:17058.11.sciencedb.agriculture.00184"
    assert backend._map_keys_to_zh_recursive({"Publisher": [{"lang": "en", "value": "Science Data Bank"}]}) == {
        "发布机构": [{"lang": "en", "value": "Science Data Bank"}]
    }


def test_dataset_domain_english_aliases_merge_to_chinese_keys():
    payload = {
        "zh": {
            "资源类型判定": "数据集",
            "数据集基本信息": {"数据量": "12KB"},
            "数据集服务信息": {"数据集引用格式": "中文引用"},
        },
        "en": {
            "Resource Type Classification": "Dataset",
            "Dataset Basic Information": {
                "Data Size": "12KB",
                "Project/Funder": "2016YFB0600200",
            },
            "Dataset Service Information": {"Dataset Citation Format": "English citation"},
        },
    }

    domain = backend._build_unified_metadata(payload)["领域元数据"]["metadatas"][0]
    basic = domain["数据集基本信息"]
    service = domain["数据集服务信息"]

    assert "Data Size" not in basic
    assert "Project/Funder" not in basic
    assert basic["数据量"] == "12KB"
    assert basic["基金项目"] == [{"lang": "en", "value": "2016YFB0600200"}]
    assert "Dataset Citation Format" not in service
    assert service["数据集引用格式"] == [
        {"lang": "zh", "value": "中文引用"},
        {"lang": "en", "value": "English citation"},
    ]


def test_cstr_language_value_objects_are_preserved_in_domain_metadata():
    payload = {
        "zh": {
            "资源类型判定": "数据集",
            "领域判定": "数据集元数据",
            "标识符": "CSTR:A0006.11.A0001.202006.001024",
            "CSTR标识符": "A0006.11.A0001.202006.001024",
            "标题": "北京市提供新冠病毒核酸检测服务的医疗卫生机构数据集",
            "数据集基本信息": {
                "标识符": "CSTR:A0006.11.A0001.202006.001024",
                "CSTR标识符": "A0006.11.A0001.202006.001024",
            },
        },
        "en": {
            "Resource Type Classification": "Dataset",
            "Domain Classification": "Dataset Metadata",
            "Identifier": "CSTR:A0006.11.A0001.202006.001024",
            "CSTR Identifier": "A0006.11.A0001.202006.001024",
            "Title": "COVID-19 testing institutions in Beijing",
            "Dataset Basic Information": {
                "Identifier": "CSTR:A0006.11.A0001.202006.001024",
                "CSTR Identifier": "A0006.11.A0001.202006.001024",
            },
        },
    }

    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    domain = unified["领域元数据"]["metadatas"][0]

    assert core["identifier"] == "CSTR:A0006.11.A0001.202006.001024"
    assert domain["CSTR标识符"] == "CSTR:A0006.11.A0001.202006.001024"
    assert domain["数据集基本信息"]["CSTR标识符"] == "CSTR:A0006.11.A0001.202006.001024"


def test_geodata_cstr_and_timezone_dates_are_preserved():
    payload = geodata._payload_from_data(
        {
            "guid": "274461948639522",
            "sciIdentification": "CSTR:17099.11.G274461948639522.20260703.v1",
            "doi": "10.12009/YRDR.2026.1008.ver1.db",
            "title": "全球10km高分辨率无缝逐日XCH4数据集(2003-2020年)",
            "dataStartTime": "2002-12-31T16:00:00.000+0000",
            "dataEndTime": "2020-12-30T16:00:00.000+0000",
        },
        "https://www.geodata.cn/main/face_science_detail?typeName=face_science&guid=274461948639522",
        "",
    )

    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert core["identifier"] == "CSTR:17099.11.G274461948639522.20260703.v1"
    assert {"type": "DOI", "identifier": "10.12009/YRDR.2026.1008.ver1.db"} in core["alternative_identifiers"]
    assert "2003-01-01 - 2020-12-31" in str(basic["范围"]["时间范围"])
    assert geodata._is_geodata_detail_url("https://nnu.geodata.cn/data/datadetails.html?dataguid=274461948639522")


def test_vsso_producer_units_are_split_and_byte_size_is_formatted(monkeypatch):
    monkeypatch.setattr(
        vsso,
        "_fetch_detail_data",
        lambda url, html="", title="": {
            "dataNameCh": "中国旱区多源降水融合数据集（XGB-RF）",
            "dataNameEn": "Multi-Source Precipitation Forced Dataset for China's Dryland (XGB-RF)",
            "dataProducerCh": "中国科学院大气物理研究所/王雯；中国科学院大气物理研究所/王鑫",
            "dataProducerEn": "Institute of Atmospheric Physics,CAS/Wen Wang;Institute of Atmospheric Physics,CAS/Xin Wang",
            "datasetTotalSize": "212457108",
            "cstr": "CSTR:14804.11.01.60.00023-V01",
            "doi": "10.12176/01.60.00023-V01",
            "versionNum": "V1.0",
            "serverName": "国家空间科学数据中心",
            "generationDate": "2026-06-30 00:00:00",
            "releaseDate": "2026-07-09 14:58:31",
            "shareMathod": "线上共享",
            "shareScope": "有条件共享",
            "sharePlan": "即时公开",
            "applicationProcedure": "需提交数据申请，经数据生产者审核通过后获取数据。",
            "license": "CC BY 4.0",
            "subjectCategory": "地球科学",
        },
    )
    payload = vsso.extract(
        "<html></html>",
        "https://vsso.nssdc.ac.cn/nssdc_zh/html/vssoinfo.html?16242",
        "",
    )
    assert payload

    basic = payload["zh"]["数据集基本信息"]
    author = basic["数据集作者"]

    assert payload["zh"]["创建者"] == ["王雯", "王鑫"]
    assert author["工作单位"] == "中国科学院大气物理研究所"
    assert basic["文件内容"] is None
    assert basic["数据格式"] is None
    assert basic["数据量"].endswith("MB")
    assert payload["zh"]["数据集服务信息"]["数据集引用格式"] == (
        "中国科学院大气物理研究所/王雯；中国科学院大气物理研究所/王鑫. "
        "中国旱区多源降水融合数据集（XGB-RF）. V1.0. 国家空间科学数据中心. "
        "DOI:10.12176/01.60.00023-V01. 2026-07-09."
    )
    assert payload["en"]["Creators"] == ["Wen Wang", "Xin Wang"]
    assert payload["en"]["Rights"]["Sharing Method"] == "Online Shared"
    assert payload["en"]["Rights"]["Sharing Scope"] == "Conditionally Shared"
    assert payload["en"]["Rights"]["Sharing Status"] == "Immediate Public"
    assert payload["en"]["Rights"]["Application Procedure"] == "需提交数据申请，经数据生产者审核通过后获取数据。"
    assert payload["zh"]["学科分类"] is None
    assert payload["en"]["Discipline Classification"] is None
    assert payload["en"]["Dataset Basic Information"]["Dataset Authors"]["Author Name"] == ["Wen Wang", "Xin Wang"]
    assert payload["en"]["Dataset Service Information"]["Dataset Citation Format"] == (
        "Institute of Atmospheric Physics,CAS/Wen Wang;Institute of Atmospheric Physics,CAS/Xin Wang. "
        "Multi-Source Precipitation Forced Dataset for China's Dryland (XGB-RF). V1.0. "
        "National Space Science Data Center. DOI:10.12176/01.60.00023-V01. 2026-06-30."
    )
    assert payload["en"]["Extension Info"]["Data Producer"] == "Institute of Atmospheric Physics,CAS/Wen Wang;Institute of Atmospheric Physics,CAS/Xin Wang"

    unified = backend._build_unified_metadata(payload)
    assert unified["核心元数据"]["metadatas"][0]["subjects"] is None
    core_rights = unified["核心元数据"]["metadatas"][0]["rights"][0]["description"]
    assert {
        "lang": "en",
        "value": (
            "Sharing Method: Online Shared；Sharing Scope: Conditionally Shared；"
            "Sharing Status: Immediate Public；"
            "Application Procedure: 需提交数据申请，经数据生产者审核通过后获取数据。；"
            "License: CC BY 4.0"
        ),
    } in core_rights


def test_nbsdc_update_time_is_not_used_as_publication_date_or_author_email():
    payload = nbsdc._payload_from_data(
        {
            "id": "63f4697887c4324cadaeda85",
            "updateTime": "2023-02-21T06:49:28.758+0000",
            "dataInfoMap": {
                "dataSetCnName": "东锅660MW高效超超临界循环流化床锅炉水动力计算",
                "contentCn": "摘要",
            },
            "dataBaoShiMap": {"cstr": "CSTR:16666.11.nbsdc.eppl30tx"},
            "dataOrgUnitMap": [
                {
                    "orgUnitCn": "东方电气集团东方锅炉股份有限公司",
                    "orgUnitEmail": "2461377075@qq.com",
                }
            ],
            "authorList": {"authorsCn": ""},
        },
        "https://www.nbsdc.cn/general/dataDetail?id=63f4697887c4324cadaeda85&type=1",
        "",
    )

    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    domain = unified["领域元数据"]["metadatas"][0]
    author = domain["数据集基本信息"]["数据集作者"]

    assert core["publish_date"] is None
    assert "发布日期" not in domain["数据集出版信息"]
    assert author["作者姓名"] == ["东方电气集团东方锅炉股份有限公司"]
    assert "电子邮箱" not in author
    assert domain["扩展信息"]["最近更新时间"] == [{"lang": "zh", "value": "2023-02-21"}]
    assert domain["扩展信息"]["机构邮箱"] == [{"lang": "zh", "value": "2461377075@qq.com"}]


def test_ncmi_citation_drops_empty_doi_url():
    assert ncmi._clean_citation(
        "中国医学科学院.北京市提供新冠病毒核酸检测服务的医疗卫生机构数据集.https://doi.org/.",
        None,
    ) == "中国医学科学院.北京市提供新冠病毒核酸检测服务的医疗卫生机构数据集."
    assert ncmi._clean_citation(
        "中国医学科学院.数据集.https://doi.org/.",
        "10.12213/11.A0001.202006.001024",
    ) == "中国医学科学院.数据集.https://doi.org/10.12213/11.A0001.202006.001024"
    payload = ncmi._payload_from_html(
        """
        <table>
          <tr><td>科技资源标识符</td><td>CSTR:A0006.11.A0001.202006.001024</td></tr>
          <tr><td>DOI</td><td>.</td></tr>
          <tr><td>引用格式</td><td>中国医学科学院.数据集.https://doi.org/.</td></tr>
        </table>
        <div id="dataSetNameZh">北京市提供新冠病毒核酸检测服务的医疗卫生机构数据集</div>
        """,
        "https://www.ncmi.cn/phda/dataDetails.do?id=CSTR:A0006.11.A0001.202006.001024",
        "",
    )
    service = payload["zh"]["数据集服务信息"]

    assert service["数据集引用格式"] == "中国医学科学院.数据集."


def test_ncmi_beijing_spatial_range_creator_english_and_no_contact_contributor():
    payload = ncmi._payload_from_html(
        """
        <table>
          <tr><td>科技资源标识符</td><td>CSTR:A0006.11.A0001.202006.001024</td></tr>
          <tr><td>DOI</td><td>10.12213/11.A0001.202006.001024</td></tr>
          <tr><td>数据集中文名称</td><td>北京市提供新冠病毒核酸检测服务的医疗卫生机构数据集</td></tr>
          <tr><td>数据集英文名称</td><td>Dataset of Medical Institutions for COVID19 Nucleic Acid Testing in Beijing</td></tr>
          <tr><td>关键词</td><td>新冠病毒；核酸检测；医疗机构；北京市</td></tr>
          <tr><td>数据描述</td><td>北京市卫生健康委员会公布了医疗卫生机构。</td></tr>
          <tr><td>资源创建者</td><td>中国医学科学院</td></tr>
          <tr><td>数据资源创建机构</td><td>中国医学科学院</td></tr>
          <tr><td>创建机构英文名称</td><td>ChineseAcademyofMedicalSciences</td></tr>
          <tr><td>数据资源联系人</td><td>罗葳</td></tr>
        </table>
        """,
        "https://www.ncmi.cn/phda/dataDetails.do?id=CSTR:A0006.11.A0001.202006.001024",
        "",
    )
    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    domain = unified["领域元数据"]["metadatas"][0]
    basic = domain["数据集基本信息"]

    assert basic["范围"]["空间范围"] == [{"lang": "zh", "value": "北京"}, {"lang": "en", "value": "Beijing"}]
    assert core["contributors"] is None
    assert "贡献者" not in domain
    creator_names = core["creators"][0]["person"]["names"]
    assert {"lang": "zh", "name": "中国医学科学院"} in creator_names
    assert {"lang": "en", "name": "Chinese Academy of Medical Sciences"} in creator_names
    assert basic["数据集作者"]["作者姓名"] == [
        {"lang": "zh", "value": ["中国医学科学院"]},
        {"lang": "en", "value": ["Chinese Academy of Medical Sciences"]},
    ]


def test_tpdc_author_and_funder_fields_are_display_ready():
    payload = tpdc._payload_from_api_context(
        {
            "metadataVO": {
                "id": "b0f1d740-0928-4c47-8085-11f55d16f735",
                "title": "华北平原农作物种植区分布图（2001-2018）",
                "titleEn": "Distribution maps of crop planting areas in the North China Plain (2001-2018)",
                "cstr": "18406.11.Terre.tpdc.301311",
                "doi": "10.11888/Terre.tpdc.301311",
                "language": "zh",
                "tsPublish": "2022-09-27 09:10:42",
            },
            "metadataWordVO": {
                "title": "Distribution maps of crop planting areas in the North China Plain (2001-2018)",
                "language": "en",
            },
            "authorVOList": [
                {
                    "name": "雷慧闽",
                    "nameEn": "LEI Huimin",
                    "unit": "清华大学",
                    "email": "leihm@tsinghua.edu.cn",
                    "daid": "D-0656-2022",
                }
            ],
            "fundVOList": [
                {
                    "titleCn": "流域生态水文学",
                    "titleEn": "Excellent Young Scientists Fund of China",
                    "typeCn": "优秀青年科学基金项目",
                    "typeEn": "Excellent Young Scientists Fund of China",
                    "code": "51922063",
                },
                {
                    "titleCn": "国家重点研发计划",
                    "titleEn": "National Key Research and Development Program of China",
                    "typeCn": "国家重点研发计划",
                    "typeEn": "National Key Research and Development Program of China",
                    "code": "2018YFC0407703",
                },
            ],
            "keywordStandVOList": [
                {"name": "遥感", "enName": "Remote Sensing Technology"},
                {"name": "陆地表层", "enName": "Terrestrial Surface"},
            ],
        },
        "https://data.tpdc.ac.cn/zh-hans/data/b0f1d740-0928-4c47-8085-11f55d16f735/",
    )

    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    author = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]["数据集作者"]
    fund_project = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]["基金项目"]

    assert author["作者姓名"] == [
        {"lang": "zh", "value": ["雷慧闽"]},
        {"lang": "en", "value": ["LEI Huimin"]},
    ]
    assert author["工作单位"] == [
        {"lang": "zh", "value": "国家青藏高原科学数据中心"},
        {"lang": "en", "value": "National Tibetan Plateau / Third Pole Environment Data Center"},
    ]
    assert author["电子邮箱"] == "data@itpcas.ac.cn"
    assert core["subjects"] == [
        {"lang": "zh", "value": ["遥感", "陆地表层"]},
        {"lang": "en", "value": ["Remote Sensing Technology", "Terrestrial Surface"]},
    ]
    assert core["creators"] == [
        {
            "type": "Organize",
            "affiliation": {
                "names": [
                    {"lang": "zh", "name": "国家青藏高原科学数据中心"},
                    {"lang": "en", "name": "National Tibetan Plateau / Third Pole Environment Data Center"},
                ],
                "identifiers": None,
                "emails": ["data@itpcas.ac.cn"],
            },
        }
    ]
    assert core["funders"] == [
        {
            "name": [
                {"lang": "zh", "value": "优秀青年科学基金项目：流域生态水文学（51922063）"},
                {"lang": "en", "value": "Excellent Young Scientists Fund of China（51922063）"},
            ],
            "proj_type": None,
            "proj_num": None,
            "proj_name": None,
        },
        {
            "name": [
                {"lang": "zh", "value": "国家重点研发计划（2018YFC0407703）"},
                {"lang": "en", "value": "National Key Research and Development Program of China（2018YFC0407703）"},
            ],
            "proj_type": None,
            "proj_num": None,
            "proj_name": None,
        },
    ]
    assert fund_project == [
        {
            "lang": "zh",
            "value": "优秀青年科学基金项目：流域生态水文学（51922063）；国家重点研发计划（2018YFC0407703）",
        },
        {
            "lang": "en",
            "value": "Excellent Young Scientists Fund of China（51922063）；National Key Research and Development Program of China（2018YFC0407703）",
        },
    ]


def test_chinare_file_content_is_left_empty():
    payload = chinare.extract(
        json.dumps(
            {
                "id": "f6b318b5-1ba7-46b8-9566-b16728db0989",
                "dif_id": "f6b318b5-1ba7-46b8-9566-b16728db0989",
                "entry_title": "中国第14次南极科学考察(1997-1998)长城站常规气象观测数据",
                "team_name": "中国第14次南极科学考察",
                "sites_name": "长城站",
                "survey_platform": "自动气象站",
                "quality": "仪器经过标定",
                "cstr": "CSTR:11738.11.NCDC.POLAR.2020.160",
            },
            ensure_ascii=False,
        ),
        "https://datacenter.chinare.org.cn/data-center/metadata?id=f6b318b5-1ba7-46b8-9566-b16728db0989",
        "",
    )

    unified = backend._build_unified_metadata(payload)
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert payload["zh"]["数据集基本信息"]["文件内容"] is None
    assert payload["en"]["Dataset Basic Information"]["File Content"] is None
    assert "文件内容" not in basic
    assert basic["范围"]["空间范围"] == "长城站"


def test_noda_chinese_api_response_keeps_default_branch_and_clean_spatial_range():
    payload = noda.extract(
        json.dumps(
            {
                "id": "6a51f07f6e9d28541b592582",
                "title": "2026年7月9日广西南宁洪涝灾区GF3B卫星遥感影像数据集",
                "description": "本数据集包含灾区GF3B卫星遥感影像数据。",
                "language": "中文",
                "spatialLocation": {
                    "spatialLocation": "Nanning",
                    "westLng": "107.75",
                    "eastLng": "108.85",
                    "southLat": "22.2167",
                    "northLat": "23.5333",
                    "projectInfo": "WGS84",
                    "scale": "10m",
                },
                "dataFile": {
                    "metaLanguage": "中文",
                    "author": "Yang Xiangfei",
                    "authorEmail": "chinageoss_office@aircas.ac.cn",
                },
                "dataDistribute": {"fileSize": 10055.68, "fileItemNum": 4},
                "contributor": {
                    "fullName": "国家对地观测科学数据中心",
                    "email": "chinageoss_office@aircas.ac.cn",
                    "contributorUnitName": "国家对地观测科学数据中心",
                },
                "category": {
                    "categorySubject": ["420测绘科学技术", "420.20摄影测量与遥感技术"],
                    "categoryTheme": ["对地观测数据产品", "微波数据产品"],
                    "productType": "除原始遥感影像外的栅格数据",
                },
                "copyRight": {
                    "redistributeArea": "国内国外均可分发",
                    "dataSharingMod": "离线申请",
                    "dataLevel": "无差别访问",
                    "dataReference": "国家综合地球观测数据共享平台，2026年7月9日广西南宁洪涝灾区GF3B卫星遥感影像数据集，网址为：https://www.noda.ac.cn/datasharing/datasetDetails/6a51f07f6e9d28541b592582",
                },
                "download": 5,
                "ftp": {"ftpAddress": "112.6.51.173"},
                "keyword": ["南宁", "洪涝灾区"],
                "cstr": "10441.11.202607.000041",
                "doi": "10.11878/db.202607.000041",
            },
            ensure_ascii=False,
        ),
        "https://www.noda.ac.cn/datasharing/datasetDetails/6a51f07f6e9d28541b592582",
        "",
    )

    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    domain = unified["领域元数据"]["metadatas"][0]
    basic = domain["数据集基本信息"]
    service = domain["数据集服务信息"]

    assert core["titles"] == [
        {
            "lang": "zh",
            "name": "2026年7月9日广西南宁洪涝灾区GF3B卫星遥感影像数据集",
        }
    ]
    assert core["descriptions"] == [{"lang": "zh", "description": "本数据集包含灾区GF3B卫星遥感影像数据。"}]
    assert core["keywords"] == [{"lang": "zh", "keyword": ["南宁", "洪涝灾区"]}]
    assert core["subjects"] == [{"standard_gbt": ["420测绘科学技术", "420.20摄影测量与遥感技术"]}]
    assert core["rights"] == [{"description": "国内国外均可分发；离线申请；无差别访问"}]
    assert core["urls"] == ["https://www.noda.ac.cn/datasharing/datasetDetails/6a51f07f6e9d28541b592582"]
    assert basic["标题"] == core["titles"]
    assert basic["文件内容"].startswith("4个文件；")
    assert basic["数据量"] == "10055.68 MB"
    assert basic["数据集作者"]["作者姓名"] == ["国家对地观测科学数据中心"]
    assert basic["范围"]["空间范围"] == {
        "西部边界经度": "107.75",
        "东部边界经度": "108.85",
        "南部边界纬度": "22.2167",
        "北部边界纬度": "23.5333",
    }
    assert service["数据集共享许可协议"] == "离线申请"
    assert service["数据集使用声明"] == "国内国外均可分发；无差别访问"
    assert service["数据集下载地址"] == "https://www.noda.ac.cn/datasharing/datasetDetails/6a51f07f6e9d28541b592582"
    assert "数据论文访问地址" not in service


def test_noda_fetches_chinese_api_payload_by_default(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"responseBody": {"id": "abc", "title": "中文标题", "language": "中文"}}

    def fake_post(url, headers=None, timeout=None):
        captured["headers"] = headers or {}
        return Response()

    monkeypatch.setattr(noda.requests, "post", fake_post)

    payload = noda.extract("", "https://www.noda.ac.cn/datasharing/datasetDetails/abc", "")

    assert "zh-CN" in captured["headers"]["Accept-Language"]
    assert payload["zh"]["核心元数据"]["metadatas"][0]["titles"] == [{"lang": "zh", "name": "中文标题"}]


def test_nhepsdc_english_page_and_version_are_merged(monkeypatch):
    zh_html = """
    <main class="main data-particulars-page">
      <div class="detail-info">
        <div class="detail-title">劳厄衍射数据_CaSTS-S</div>
        <div class="info-row"><div class="info-label">关键词</div><div><span class="tag">白光劳厄衍射</span></div></div>
        <div class="info-row"><div class="info-label">数据标识</div><div>
          <a class="card-link" href="https://cstr.cn/CSTR:17081.11.photon.laue.dataset-20260120111231">CSTR:17081.11.photon.laue.dataset-20260120111231</a>
          <a class="card-link" href="https://doi.org/10.12402/photon/laue/dataset-20260120111231">DOI:10.12402/photon/laue/dataset-20260120111231</a>
        </div></div>
        <div class="info-row"><div class="info-label">来源机构</div><div>国家高能物理科学数据中心</div></div>
        <div class="info-row"><div class="info-label">摘要</div><div>CaSTS蛋白质晶体的白光劳厄衍射数据。</div></div>
      </div>
      <table class="meta-table">
        <tr><td class="label">汇交人姓名（中文）</td><td>郝权</td></tr>
        <tr><td class="label">汇交人电子邮箱</td><td>haoquan@ihep.ac.cn</td></tr>
        <tr><td class="label">汇交人所在任职机构</td><td>散裂中子源科学中心</td></tr>
        <tr><td class="label">文件数量</td><td>1</td></tr>
        <tr><td class="label">共享途径</td><td>线上共享</td></tr>
        <tr><td class="label">共享范围</td><td>完全共享</td></tr>
        <tr><td class="label">访问权限</td><td>开放共享</td></tr>
        <tr><td class="label">许可协议</td><td>署名 4.0(CC BY 4.0)</td></tr>
      </table>
      <table class="version-table"><tbody><tr><td>3.0</td><td></td></tr></tbody></table>
      <script type="text/template" id="defaultMarkdownTemplate">中文卡片</script>
    </main>
    """
    en_html = """
    <main class="main data-particulars-page">
      <div class="detail-info">
        <div class="detail-title">Laue_diffraction_dataset_CaSTS-S</div>
        <div class="info-row"><div class="info-label">Keywords</div><div><span class="tag">white beam Laue diffraction</span></div></div>
        <div class="info-row"><div class="info-label">CSTR</div><div>
          <a class="card-link" href="https://cstr.cn/CSTR:17081.11.photon.laue.dataset-20260120111231">CSTR:17081.11.photon.laue.dataset-20260120111231</a>
        </div></div>
        <div class="info-row"><div class="info-label">Source Organization</div><div>National High Energy Physics Scientific Data Center</div></div>
        <div class="info-row"><div class="info-label">Abstract</div><div>White beam Laue diffraction dataset of CaSTS protein crystal.</div></div>
      </div>
      <table class="meta-table">
        <tr><td class="label">Submitter Name</td><td>Hao Quan</td></tr>
        <tr><td class="label">Submitter Institution</td><td>Spallation Neutron Source Science Center</td></tr>
      </table>
      <table class="version-table"><tbody><tr><td>3.0</td><td></td></tr></tbody></table>
      <script type="text/template" id="defaultMarkdownTemplate">English card</script>
    </main>
    """
    monkeypatch.setattr(nhepsdc, "_fetch_english_content", lambda url: en_html)

    raw_payload = nhepsdc.extract(zh_html, "https://www.nhepsdc.cn/resource/photon/Other/dataset-20260120111231", "")
    assert raw_payload["en"]["Core Metadata"]["metadatas"][0]["rights"][0]["description"] == (
        "Sharing channel: Online sharing; Sharing scope: Full sharing; Access rights: Open sharing"
    )
    assert raw_payload["en"]["Dataset Basic Information"]["Data Size"] == "1 file"
    assert raw_payload["en"]["Dataset Service Information"]["Dataset License"] == "署名 4.0(CC BY 4.0)"
    assert raw_payload["en"]["Dataset Service Information"]["Dataset Usage Statement"] == "Open sharing"

    unified = backend._build_unified_metadata(raw_payload)
    core = unified["核心元数据"]["metadatas"][0]
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert {"lang": "zh", "value": "共享途径: 线上共享；共享范围: 完全共享；访问权限: 开放共享"} in core["rights"][0]["description"]
    assert {
        "lang": "en",
        "value": "Sharing channel: Online sharing; Sharing scope: Full sharing; Access rights: Open sharing",
    } in core["rights"][0]["description"]
    assert {"lang": "en", "name": "Laue_diffraction_dataset_CaSTS-S"} in core["titles"]
    assert {"lang": "en", "description": "White beam Laue diffraction dataset of CaSTS protein crystal."} in core["descriptions"]
    assert {"lang": "en", "keyword": ["white beam Laue diffraction"]} in core["keywords"]
    assert core["version"] == "3.0"
    assert {"lang": "en", "name": "Laue_diffraction_dataset_CaSTS-S"} in basic["标题"]


def test_ncdc_fetches_and_merges_english_page(monkeypatch):
    zh_html = """
    <html lang="zh-CN"><body>
      <div class="metadata-details-title">2017-2019年藏东南 松宗曲宗臧布 冰川径流观测数据</div>
      <div class="metadata-details-subtitle">发布时间：2020/12/24 11:50</div>
      <div class="metadata-detail">
        <div class="row"><span class="t-title">英文名称</span><span class="t-value">Runoff observation data</span></div>
        <div class="row"><span class="t-title">CSTR</span><span class="t-value">CSTR:11738.11.ncdc.BoMi.2020.16</span></div>
        <div class="row"><span class="t-title">DOI</span><span class="t-value">10.12072/ncdc.BoMi.db0006.2020</span></div>
        <div class="row"><span class="t-title">数据分类</span><span class="t-value">冰川</span></div>
      </div>
      <table class="metadata-detail"><tr><th>采集时间</th><td>2017/10/13 - 2019/08/25</td></tr><tr><th>采集地点</th><td>西藏自治区波密县松宗镇</td></tr></table>
      <div class="info-box abstract-box"><div class="title-bar">数据集摘要</div><div class="info-block"><p>中文摘要。</p></div></div>
      <div class="info-box"><div class="title-bar">许可协议</div><div class="info-block">本作品采用 CC BY 4.0 进行许可。</div></div>
      <ol class="ref-content"><div class="ref-list"><li>陈宁生, 丁海涛, 邓明枫. 中文标题. 国家冰川冻土沙漠科学数据中心, 2020. https://cstr.cn/CSTR:11738.11.ncdc.BoMi.2020.16.</li></div></ol>
      <li class="list-group-item"><span class="list-group-item-heading">主题:</span><p class="list-group-item-text"><a>流速</a><a>水深</a></p></li>
      <li class="list-group-item"><span class="list-group-item-heading">地点:</span><p class="list-group-item-text"><a>西藏自治区</a><a>波密县</a></p></li>
      东: 96.12 西: 96.06 南: 29.75 北: 29.82
    </body></html>
    """
    en_html = """
    <html lang="en"><body>
      <div class="metadata-details-title">Runoff observation data of Songzongquzongzangbu glacier in Southeast Tibet from 2017 to 2019</div>
      <div class="metadata-details-subtitle">Publish time：2020/12/24 11:50</div>
      <div class="metadata-detail">
        <div class="row"><span class="t-title">English name</span><span class="t-value">Runoff observation data of Songzongquzongzangbu glacier in Southeast Tibet from 2017 to 2019</span></div>
        <div class="row"><span class="t-title">CSTR</span><span class="t-value">CSTR:11738.11.ncdc.BoMi.2020.16</span></div>
        <div class="row"><span class="t-title">DOI</span><span class="t-value">10.12072/ncdc.BoMi.db0006.2020</span></div>
        <div class="row"><span class="t-title">Category</span><span class="t-value">Glacier</span></div>
      </div>
      <table class="metadata-detail"><tr><th>collect time</th><td>2017/10/13 - 2019/08/25</td></tr><tr><th>collect place</th><td>Songzong Town, Bomi County, Tibet Autonomous Region</td></tr></table>
      <div class="info-box abstract-box"><div class="title-bar">Datasets description</div><div class="info-block"><p>English abstract.</p></div></div>
      <div class="info-box"><div class="title-bar">license agreement</div><div class="info-block">This work is licensed under CC BY 4.0.</div></div>
      <ol class="ref-content"><div class="ref-list"><li>Chen Ningsheng, Ding Haitao, Deng Mingfeng. English title. National Cryosphere Desert Data Center, 2020. https://cstr.cn/CSTR:11738.11.ncdc.BoMi.2020.16.</li></div></ol>
      <li class="list-group-item"><span class="list-group-item-heading">Theme:</span><p class="list-group-item-text"><a>Velocity</a><a>water depth</a></p></li>
      <li class="list-group-item"><span class="list-group-item-heading">Place:</span><p class="list-group-item-text"><a>Songzong Town</a><a>Bomi County</a></p></li>
      east 96.12 west 96.06 south 29.75 north 29.82
    </body></html>
    """
    monkeypatch.setattr(ncdc, "_fetch_localized_content", lambda url, lang: en_html if lang == "en" else zh_html)

    unified = backend._build_unified_metadata(
        ncdc.extract(zh_html, "https://www.ncdc.ac.cn/portal/metadata/59e517ca-aaf6-44f0-8676-16e647f4f426", "")
    )
    core = unified["核心元数据"]["metadatas"][0]
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert {"lang": "zh", "name": "2017-2019年藏东南 松宗曲宗臧布 冰川径流观测数据"} in core["titles"]
    assert {"lang": "en", "name": "Runoff observation data of Songzongquzongzangbu glacier in Southeast Tibet from 2017 to 2019"} in core["titles"]
    assert {"lang": "en", "description": "English abstract."} in core["descriptions"]
    assert {"lang": "en", "keyword": ["Velocity", "water depth", "Songzong Town", "Bomi County"]} in core["keywords"]
    assert core["subjects"] == [{"lang": "zh", "value": ["冰川"]}, {"lang": "en", "value": ["Glacier"]}]
    assert {"lang": "en", "value": "English"} in basic["语种"]
    creator_names = [agent["person"]["names"][1]["name"] for agent in core["creators"]]
    assert creator_names == ["Chen Ningsheng", "Ding Haitao", "Deng Mingfeng"]
    assert {"lang": "en", "description": "English abstract."} in basic["摘要"]


def test_nhepsdc_english_keywords_fall_back_to_chinese_keywords(monkeypatch):
    zh_html = """
    <main class="main data-particulars-page">
      <div class="detail-info">
        <div class="detail-title">劳厄衍射数据_CaSTS-S</div>
        <div class="info-row"><div class="info-label">关键词</div><div><span class="tag">白光劳厄衍射</span></div></div>
        <div class="info-row"><div class="info-label">数据标识</div><div>
          <a class="card-link" href="https://cstr.cn/CSTR:17081.11.photon.laue.dataset-20260120111231">CSTR:17081.11.photon.laue.dataset-20260120111231</a>
        </div></div>
        <div class="info-row"><div class="info-label">摘要</div><div>CaSTS蛋白质晶体的白光劳厄衍射数据。</div></div>
      </div>
    </main>
    """
    en_html = """
    <main class="main data-particulars-page">
      <div class="detail-info">
        <div class="detail-title">Laue_diffraction_dataset_CaSTS-S</div>
        <div class="info-row"><div class="info-label">Abstract</div><div>White beam Laue diffraction dataset.</div></div>
      </div>
    </main>
    """
    monkeypatch.setattr(nhepsdc, "_fetch_english_content", lambda url: en_html)

    unified = backend._build_unified_metadata(nhepsdc.extract(zh_html, "https://www.nhepsdc.cn/resource/photon/Other/dataset-20260120111231", ""))
    core = unified["核心元数据"]["metadatas"][0]
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert {"lang": "en", "keyword": ["白光劳厄衍射"]} in core["keywords"]
    assert {"lang": "en", "keyword": ["白光劳厄衍射"]} in basic["关键词"]


def test_nhepsdc_file_content_uses_file_list_not_markdown_card(monkeypatch):
    zh_html = """
    <main class="main data-particulars-page">
      <div class="detail-info">
        <div class="detail-title">劳厄衍射数据_CaSTS-S</div>
        <div class="info-row"><div class="info-label">数据标识</div><div>
          <a class="card-link" href="https://cstr.cn/CSTR:17081.11.photon.laue.dataset-20260120111231">CSTR:17081.11.photon.laue.dataset-20260120111231</a>
        </div></div>
        <div class="info-row"><div class="info-label">摘要</div><div>摘要文本</div></div>
      </div>
      <div class="file-info">
        <div class="name">casts-s.zip</div>
        <div class="meta">文件大小：289.27 MB 文件类型：zip</div>
      </div>
      <script type="text/template" id="defaultMarkdownTemplate">这是一段页面说明，不是文件内容。</script>
    </main>
    """
    monkeypatch.setattr(nhepsdc, "_fetch_english_content", lambda url: None)

    unified = backend._build_unified_metadata(nhepsdc.extract(zh_html, "https://www.nhepsdc.cn/resource/photon/Other/dataset-20260120111231", ""))
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert basic["文件内容"] == "casts-s.zip"
    assert "页面说明" not in basic["文件内容"]


def test_nadc_english_page_description_and_keywords_are_merged(monkeypatch):
    zh_html = """
    <div id="title">LAMOST光谱巡天第七次数据发布第2.0版 中分辨率巡天</div>
    <div id="title_en">LAMOST DR7 V2.0 Medium Resolution Survey</div>
    <div id="description">中文摘要</div>
    <div id="keywords">郭守敬望远镜 , 光谱 , 星表</div>
    <div id="doi">10.12149/100451</div>
    <div id="cstr">CSTR:11379.11.100451</div>
    <div id="author_name">LAMOST运行发展中心</div>
    <div id="tags">
    <div class="col-auto"><div class="dataset-tag-name">子学科</div></div>
    <div class="col-sm-7"><div class="dataset-tagBlock">恒星与星际物质</div></div>
    <div class="col-auto"><div class="dataset-tag-name">观测波段</div></div>
    <div class="col-sm-7"><div class="dataset-tagBlock">光学波段</div></div>
    <div class="col-auto"><div class="dataset-tag-name">观测装置和计划</div></div>
    <div class="col-sm-7"><div class="dataset-tagBlock">大天区面积多目标光纤光谱天文望远镜(LAMOST)</div></div>
    <div class="col-auto"><div class="dataset-tag-name">数据类型</div></div>
    <div class="col-sm-7"><div class="dataset-tagBlock">光谱数据</div><div class="dataset-tagBlock">星表数据</div></div>
    </div>
    <div id="sharemode">线上共享</div>
    <div id="sharescope">有条件共享</div>
    <div id="procedure">若需访问未完全公开的观测数据，请注册LAMOST用户。</div>
    """
    en_html = """
    <div id="title">LAMOST DR7 V2.0 Medium Resolution Survey</div>
    <div id="description">LAMOST DR7 V2.0 Medium Resolution Survey includes spectra and catalogs.</div>
    <div id="keywords">LAMOST , Spectrum , Catalog</div>
    <div id="data_amount">4 tables 17551171 rows 9.13 GB</div>
    <div id="author_name">LAMOST Operation and Development Center</div>
    <div id="sharemode">online</div>
    <div id="sharescope">Share with conditions</div>
    <div id="tags">
    <div class="col-auto"><div class="dataset-tag-name">subject</div></div>
    <div class="col-sm-7"><div class="dataset-tagBlock">Star and Interstellar Matter</div></div>
    <div class="col-auto"><div class="dataset-tag-name">data type</div></div>
    <div class="col-sm-7"><div class="dataset-tagBlock">Spectrum Data</div><div class="dataset-tagBlock">Catalog Data</div></div>
    </div>
    """
    monkeypatch.setattr(nadc, "_fetch_english_html", lambda url: en_html)

    raw_payload = nadc.extract(zh_html, "https://nadc.china-vo.org/res/r100451/", "")
    assert raw_payload["en"]["Dataset Basic Information"]["File Content"] is None
    assert raw_payload["en"]["Dataset Basic Information"]["Data Format"] == "Spectrum Data; Catalog Data"
    assert raw_payload["en"]["Dataset Basic Information"]["Dataset Authors"]["Author Name"] == ["LAMOST Operation and Development Center"]
    assert raw_payload["en"]["Dataset Service Information"]["Dataset Usage Statement"] == "Sharing Method: online；Sharing Scope: Share with conditions"
    assert raw_payload["en"]["Core Metadata"]["metadatas"][0]["rights"][0] == {
        "license_type": None,
        "license": None,
        "type": None,
        "description": "Sharing Method: online；Sharing Scope: Share with conditions",
        "cert_num": None,
    }

    unified = backend._build_unified_metadata(raw_payload)
    core = unified["核心元数据"]["metadatas"][0]
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert core["subjects"] == [
        {"lang": "zh", "value": ["恒星与星际物质"]},
        {"lang": "en", "value": ["Star and Interstellar Matter"]},
    ]
    assert {"lang": "en", "description": "LAMOST DR7 V2.0 Medium Resolution Survey includes spectra and catalogs."} in core["descriptions"]
    assert {"lang": "en", "keyword": ["LAMOST", "Spectrum", "Catalog"]} in core["keywords"]
    assert {"lang": "en", "description": "LAMOST DR7 V2.0 Medium Resolution Survey includes spectra and catalogs."} in basic["摘要"]
    assert {"lang": "en", "keyword": ["LAMOST", "Spectrum", "Catalog"]} in basic["关键词"]
    assert "文件内容" not in basic


def test_nfgsdc_subject_file_content_and_usage_fields_are_precise():
    payload = nfgsdc._payload_from_data(
        {
            "data": {
                "id": "a47fe3ac-b57d-4a35-81ba-513e15e576d5",
                "title": "西南高山峡谷区2000~2022年逐年水土流失风险数据",
                "desc": "摘要",
                "shareType": "完全公开数据",
                "quote": "北京林业大学，西南高山峡谷区2000~2022年逐年水土流失风险数据，国家林业和草原科学数据中心，2000-2022，CSTR:17575.11.0420260611001.0000.V1",
            },
            "dataset": {"code": "CSTR:17575.11.0420260611001"},
            "meta": [
                {"key": "学科分类", "value": "生态学"},
                {"key": "数据资源", "value": "科学数据"},
                {"key": "数据来源", "value": "个人或机构汇交"},
                {"key": "获取方式", "value": "线上共享"},
                {"key": "数据质量", "value": "质量说明"},
                {"key": "数据加工方法", "value": "加工方法说明"},
            ],
            "catalog": [
                {"key": "14", "value": "遥感数据"},
                {"key": "1411", "value": "生态产品"},
            ],
            "extent": [{"key": "100000", "value": "中国"}],
        },
        "https://www.forestdata.cn/dataDetail.html?id=a47fe3ac-b57d-4a35-81ba-513e15e576d5",
        "",
        {
            "data": {
                "title": "Annual Soil and Water Loss Risk Data for the Southwest Alpine Canyon Area of China (2000-2022)",
                "desc": "English abstract",
                "shareType": "Full public data",
                "quote": "Beijing Forestry University, Annual Soil and Water Loss Risk Data. National Forestry and Grassland Science Data Center, CSTR:17575.11.0420260611001.0000.V1",
            },
            "meta": [
                {"key": "Subject Type", "value": "Ecology"},
                {"key": "Resource Type", "value": "Scientific Data"},
                {"key": "Data From", "value": "Individual or institutional submission"},
                {"key": "Get Type", "value": "Online Sharing"},
                {"key": "Share Level", "value": "Full public data"},
                {"key": "Data Type", "value": "Raster"},
                {"key": "Data Time", "value": "2000-2022"},
                {"key": "Data Amount", "value": "37.21 MB"},
            ],
            "keyword": ["soil erosion risk", "250 m resolution"],
            "catalog": [
                {"key": "14", "value": "Remote sensing"},
                {"key": "1411", "value": "Ecological products"},
            ],
            "extent": [{"key": "100000", "value": "China"}],
        },
    )

    unified = backend._build_unified_metadata(payload)
    core = unified["核心元数据"]["metadatas"][0]
    domain = unified["领域元数据"]["metadatas"][0]
    basic = domain["数据集基本信息"]
    service = domain["数据集服务信息"]
    extra = domain["扩展信息"]

    assert {"lang": "zh", "value": ["生态学"]} in core["subjects"]
    assert {"lang": "en", "value": ["Ecology"]} in core["subjects"]
    assert basic["文件内容"] == [{"lang": "zh", "value": "科学数据"}, {"lang": "en", "value": "Scientific Data"}]
    assert "质量说明" not in basic["文件内容"]
    assert {"lang": "en", "name": "Annual Soil and Water Loss Risk Data for the Southwest Alpine Canyon Area of China (2000-2022)"} in core["titles"]
    assert {"lang": "en", "description": "English abstract"} in core["descriptions"]
    assert {"lang": "en", "keyword": ["soil erosion risk", "250 m resolution"]} in core["keywords"]
    assert {"lang": "en", "value": ["Ecology"]} in core["subjects"]
    assert basic["标题"] == [
        {"lang": "zh", "name": "西南高山峡谷区2000~2022年逐年水土流失风险数据"},
        {"lang": "en", "name": "Annual Soil and Water Loss Risk Data for the Southwest Alpine Canyon Area of China (2000-2022)"},
    ]
    assert basic["范围"]["空间范围"] == [{"lang": "zh", "value": "中国"}, {"lang": "en", "value": "China"}]
    assert {"lang": "zh", "value": "科学数据"} in basic["文件内容"]
    assert {"lang": "en", "value": "Scientific Data"} in basic["文件内容"]
    assert service["数据集使用声明"] == [{"lang": "zh", "value": "线上共享"}, {"lang": "en", "value": "Online Sharing"}]
    assert service["数据集引用格式"] == [
        {
            "lang": "zh",
            "value": "北京林业大学，西南高山峡谷区2000~2022年逐年水土流失风险数据，国家林业和草原科学数据中心，2000-2022，CSTR:17575.11.0420260611001.0000.V1",
        },
        {
            "lang": "en",
            "value": "Beijing Forestry University, Annual Soil and Water Loss Risk Data. National Forestry and Grassland Science Data Center, CSTR:17575.11.0420260611001.0000.V1",
        },
    ]
    assert core["rights"] == [
        {
            "description": [
                {"lang": "zh", "value": "完全公开数据；线上共享"},
                {"lang": "en", "value": "Full public data; Online Sharing"},
            ]
        }
    ]
    assert "加工方法说明" not in service["数据集使用声明"]
    assert extra["数据质量"] == [{"lang": "zh", "value": "质量说明"}]
    assert extra["数据加工方法"] == [{"lang": "zh", "value": "加工方法说明"}]
    assert extra["目录分类"] == [{"lang": "zh", "value": ["遥感数据", "生态产品"]}]


def test_nesdc_file_content_does_not_include_subject_tags():
    payload = nesdc.extract(
        json.dumps(
            {
                "id": "60f68d757e28174f0e7d8d49",
                "title": "2000-2022年中国30米年最大NDVI数据集",
                "desc": "摘要",
                "creator": "董金玮",
                "sdo": {
                    "id": "60f68d757e28174f0e7d8d49",
                    "customConfigurationData": [
                        {
                            "dataSetTitle": "2000-2022年中国30米年最大NDVI数据集",
                            "dataSource": "团队",
                            "tag": "主题分类::植被/作物",
                            "storageType": "栅格图像",
                            "storageFormat": "GeoTIFF",
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        "https://www.nesdc.org.cn/sdo/detail?id=60f68d757e28174f0e7d8d49",
        "",
    )

    unified = backend._build_unified_metadata(payload)
    basic = unified["领域元数据"]["metadatas"][0]["数据集基本信息"]

    assert basic["文件内容"] == "栅格图像"
    assert "团队" not in basic["文件内容"]
    assert "主题分类" not in basic["文件内容"]


def test_funder_value_wrappers_are_normalized_to_standard_fields():
    payload = {
        "zh": {
            "核心元数据": {
                "metadatas": [
                    {
                        "funders": [
                            {"value": "国家重点研发计划"},
                            {
                                "projectCnName": "基础学科数据共享项目",
                                "projectNumber": "2026YFA000001",
                                "projectTypeName": "国家科技计划",
                            },
                        ],
                        "resource_type": "Dataset",
                    }
                ]
            }
        },
        "en": {
            "Core Metadata": {
                "metadatas": [
                    {
                        "funders": [{"value": "National Key R&D Program"}],
                        "resource_type": "Dataset",
                    }
                ]
            }
        },
    }

    funders = backend._build_unified_metadata(payload)["核心元数据"]["metadatas"][0]["funders"]

    assert {
        "lang": "zh",
        "value": "国家重点研发计划",
    } in funders[0]["name"]
    assert {
        "lang": "en",
        "value": "National Key R&D Program",
    } in funders[0]["name"]
    assert {"lang": "zh", "value": "基础学科数据共享项目"} in funders[1]["name"]
    assert {"lang": "zh", "value": "国家科技计划"} in funders[1]["proj_type"]
    assert funders[1]["proj_num"] == "2026YFA000001"
    assert funders[1]["proj_name"] is None


def test_funder_project_number_scalar_maps_to_proj_num():
    assert backend._normalize_funder("国家重点研发计划") == {
        "name": "国家重点研发计划",
        "proj_type": None,
        "proj_num": None,
        "proj_name": None,
    }
    assert backend._normalize_funder("2016YFB0600200") == {
        "name": None,
        "proj_type": None,
        "proj_num": "2016YFB0600200",
        "proj_name": None,
    }


def test_cstr_resolver_exposes_resource_urls_as_supplemental_sources():
    result = {
        "url": "https://scids.bdware.cn/idutil/resolve?id=16666.11.nbsdc.eppl30tx",
        "content": """
        {
          "data": {
            "data": {
              "content": {
                "urls": ["https://www.nbsdc.cn/general/dataLinks/16666.11.nbsdc.eppl30tx"]
              }
            }
          }
        }
        """,
    }

    supplemented = cstr_resolver._append_escience_supplemental(result, "CSTR:16666.11.nbsdc.eppl30tx")

    assert {
        "source": "cstr-resource-url",
        "url": "https://www.nbsdc.cn/general/dataLinks/16666.11.nbsdc.eppl30tx",
        "priority": "resource",
    } in supplemented["supplemental_urls"]


def test_url_payload_is_supplemented_from_discovered_cstr_without_overriding_webpage(monkeypatch):
    primary = {
        "核心元数据": {
            "metadatas": [
                {
                    "identifier": "CSTR:16666.11.nbsdc.eppl30tx",
                    "titles": [{"lang": "zh", "name": "网页标题"}],
                    "resource_type": "Dataset",
                }
            ]
        },
        "领域元数据": {
            "metadata_type": "数据集元数据",
            "metadatas": [
                {
                    "数据集基本信息": {"标题": [{"lang": "zh", "name": "网页标题"}]},
                    "数据集出版信息": {"版本信息": "V1"},
                    "数据集服务信息": {"数据集引用格式": "网页引用"},
                }
            ],
        },
    }
    fallback = {
        "核心元数据": {
            "metadatas": [
                {
                    "identifier": "CSTR:16666.11.nbsdc.eppl30tx",
                    "titles": [{"lang": "zh", "name": "CSTR标题"}],
                    "publish_date": "2023-02-21",
                    "resource_type": "Dataset",
                }
            ]
        },
        "领域元数据": {
            "metadata_type": "数据集元数据",
            "metadatas": [
                {
                    "数据集基本信息": {"标题": [{"lang": "zh", "name": "CSTR标题"}]},
                    "数据集出版信息": {"版本信息": "V1", "发布日期": "2023-02-21"},
                    "数据集服务信息": {"数据集引用格式": "CSTR引用"},
                }
            ],
        },
    }

    monkeypatch.setattr(
        backend,
        "_metadata_source_for_identifier",
        lambda identifier_type, identifier: (
            "cstr",
            {
                "source": "scids.bdware.cn",
                "url": "https://scids.bdware.cn/idutil/resolve?id=16666.11.nbsdc.eppl30tx",
                "content": "{}",
            },
        ),
    )
    monkeypatch.setattr(
        backend,
        "_build_payload_from_identifier_source",
        lambda source_item, mode, llm_api_key="", llm_provider="siliconflow": (fallback, []),
    )

    supplemented, results = backend.supplement_payload_from_identifier_metadata(primary, "common")
    domain = supplemented["领域元数据"]["metadatas"][0]

    assert results[0]["priority"] == "cstr"
    assert domain["数据集基本信息"]["标题"] == [{"lang": "zh", "name": "网页标题"}]
    assert domain["数据集服务信息"]["数据集引用格式"] == "网页引用"
    assert domain["数据集出版信息"]["发布日期"] == "2023-02-21"
