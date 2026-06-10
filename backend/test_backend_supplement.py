import sys
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

spec = importlib.util.spec_from_file_location('backend_app', BACKEND_DIR / 'backend.py')
backend_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_module)


def _payload(resource_url='https://example.org/resource'):
    return {
        'zh': {
            '核心元数据': {
                '标题': '原始标题',
                '描述': '未提取到',
                '资源链接': resource_url,
            }
        },
        'en': {
            'Core Metadata': {
                'Title': 'Original title',
                'Description': 'Not extracted',
                'Resource URL': resource_url,
            }
        },
    }


def _fallback_payload():
    return {
        'zh': {
            '核心元数据': {
                '标题': '补充标题',
                '描述': '补充描述',
            }
        },
        'en': {
            'Core Metadata': {
                'Title': 'Supplemental title',
                'Description': 'Supplemental description',
            }
        },
    }


class MetadataSupplementTests(unittest.TestCase):
    def test_extract_core_resource_urls_from_zh_and_en_fields(self):
        payload = _payload('访问地址: https://example.org/resource, backup https://example.org/other')
        payload['en']['Core Metadata']['Resource URL'] = 'https://example.org/resource/'

        urls = backend_module._extract_core_resource_urls(payload)

        self.assertEqual(urls, ['https://example.org/resource', 'https://example.org/other'])

    def test_extract_core_resource_urls_skips_missing_placeholders(self):
        payload = _payload('未提取到')
        payload['en']['Core Metadata']['Resource URL'] = 'Not extracted'

        urls = backend_module._extract_core_resource_urls(payload)

        self.assertEqual(urls, [])

    def test_supplement_fills_only_missing_values(self):
        initial = _payload()

        with patch.object(backend_module, 'build_url_metadata_payload', return_value=_fallback_payload()):
            merged = backend_module.supplement_payload_from_resource_url(initial, 'common')

        self.assertEqual(merged['zh']['核心元数据']['标题'], '原始标题')
        self.assertEqual(merged['zh']['核心元数据']['描述'], '补充描述')
        self.assertEqual(merged['en']['Core Metadata']['Title'], 'Original title')
        self.assertEqual(merged['en']['Core Metadata']['Description'], 'Supplemental description')

    def test_supplement_failure_keeps_original_payload(self):
        initial = _payload()

        with patch.object(backend_module, 'build_url_metadata_payload', side_effect=RuntimeError('fetch failed')):
            merged = backend_module.supplement_payload_from_resource_url(initial, 'common')

        self.assertIs(merged, initial)

    def test_identifier_query_keeps_outer_item_fields_and_supplements_payload(self):
        initial = _payload()
        resolved_items = [
            {
                'identifier': '10.1234/example',
                'type': 'doi',
                'resolved_url': 'https://doi.org/10.1234/example',
                'source': 'crossref',
                'content': 'metadata text',
                'status': 'ok',
            }
        ]

        with backend_module.app.app_context():
            with patch.object(backend_module, 'resolve_identifier_content', return_value=(resolved_items, None)):
                with patch.object(backend_module, 'build_metadata_payload', return_value=initial):
                    with patch.object(backend_module, 'build_url_metadata_payload', return_value=_fallback_payload()):
                        response = backend_module.handle_identifier_request({'mode': 'common'})

        item = response.get_json()['items'][0]

        self.assertEqual(
            set(item.keys()),
            {'identifier', 'type', 'resolved_url', 'source', 'status', 'payload', 'updated_at'},
        )
        self.assertEqual(item['payload']['zh']['核心元数据']['标题'], '原始标题')
        self.assertEqual(item['payload']['zh']['核心元数据']['描述'], '补充描述')


if __name__ == '__main__':
    unittest.main()
