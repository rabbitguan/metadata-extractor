import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


def load_module(module_name, filename):
    backend_dir = Path(__file__).resolve().parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    spec = importlib.util.spec_from_file_location(module_name, backend_dir / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_backend_module():
    llm_api = types.ModuleType('llm_api')
    llm_api.qwen_chat = lambda *args, **kwargs: {}
    sys.modules['llm_api'] = llm_api

    field_filter = types.ModuleType('field_filter')
    field_filter.apply_requirement_filter = lambda data, schema_name=None: data
    sys.modules['field_filter'] = field_filter

    identifier = types.ModuleType('identifier')
    identifier.process_source_code = lambda html: html
    sys.modules['identifier'] = identifier

    return load_module('metadata_backend_under_test', 'backend.py')


class IdentifierEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend = load_backend_module()
        cls.doi_resolver = load_module('doi_resolver_under_test', 'doi_resolver.py')
        cls.cstr_resolver = load_module('cstr_resolver_under_test', 'cstr_resolver.py')

    def test_extracts_unique_doi_and_cstr_identifiers(self):
        text = 'DOI: 10.1234/ABC. CSTR: 12345.12.123456.123456, repeated doi 10.1234/abc'

        identifiers = self.backend.extract_doi_cstr_identifiers(text)

        self.assertEqual(
            identifiers,
            [
                {'type': 'doi', 'id': '10.1234/ABC'},
                {'type': 'cstr', 'id': '12345.12.123456.123456'},
            ],
        )

    def test_returns_error_when_no_identifier_is_found(self):
        resolved, error = self.backend.resolve_identifier_content({'identifiers': 'not an identifier'})

        self.assertIsNone(resolved)
        self.assertEqual(error['message'], 'No DOI or CSTR identifier found')

    def test_resolves_multiple_identifiers_into_one_llm_input(self):
        with (
            patch.object(self.backend, 'resolve_doi', return_value={
                'content': 'cleaned DOI content',
                'url': 'https://example.org/doi',
                'source': 'doi.org',
            }),
            patch.object(self.backend, 'resolve_cstr', return_value={
                'content': 'cleaned CSTR content',
                'url': 'https://cstr.cn/12345.12.123456.123456',
                'source': 'cstr.cn',
            }),
        ):
            resolved, error = self.backend.resolve_identifier_content({
                'identifiers': '10.1234/example, 12345.12.123456.123456',
            })

        self.assertIsNone(error)
        self.assertIn('Identifier: 10.1234/example', resolved['text'])
        self.assertIn('Resolver Source: doi.org', resolved['text'])
        self.assertIn('cleaned DOI content', resolved['text'])
        self.assertIn('Identifier: 12345.12.123456.123456', resolved['text'])
        self.assertIn('Resolver Source: cstr.cn', resolved['text'])
        self.assertIn('cleaned CSTR content', resolved['text'])
        self.assertEqual(resolved['url'], 'https://example.org/doi\nhttps://cstr.cn/12345.12.123456.123456')

    def test_backend_no_longer_imports_search_id(self):
        backend_path = Path(__file__).resolve().parent / 'backend.py'
        self.assertNotIn('search_id', backend_path.read_text(encoding='utf-8'))
        self.assertFalse((Path(__file__).resolve().parent / 'search_id.py').exists())

    def test_doi_resolver_uses_doi_org_successfully(self):
        response = Mock()
        response.text = '<html><body>DOI landing page</body></html>'
        response.url = 'https://example.org/doi'
        response.raise_for_status = Mock()

        with patch.object(self.doi_resolver.requests, 'get', return_value=response):
            resolved = self.doi_resolver.resolve_doi('10.1234/example', clean_html=lambda html: f'cleaned {html}')

        self.assertEqual(resolved['source'], 'doi.org')
        self.assertEqual(resolved['url'], 'https://example.org/doi')
        self.assertEqual(resolved['content'], 'cleaned <html><body>DOI landing page</body></html>')

    def test_doi_resolver_falls_back_to_crossref_when_landing_page_fails(self):
        forbidden_response = Mock()
        forbidden_response.raise_for_status.side_effect = self.doi_resolver.requests.exceptions.HTTPError(
            '403 Client Error: Forbidden',
        )

        crossref_response = Mock()
        crossref_response.json.return_value = {
            'message': {
                'DOI': '10.1145/3691620.3695329',
                'URL': 'https://dl.acm.org/doi/10.1145/3691620.3695329',
                'title': ['Example ACM paper'],
                'publisher': 'ACM',
            },
        }
        crossref_response.raise_for_status = Mock()

        with patch.object(self.doi_resolver.requests, 'get', side_effect=[forbidden_response, crossref_response]):
            resolved = self.doi_resolver.resolve_doi('10.1145/3691620.3695329')

        self.assertEqual(resolved['source'], 'crossref')
        self.assertIn('Metadata Source: Crossref', resolved['content'])
        self.assertIn('title: Example ACM paper', resolved['content'])
        self.assertEqual(resolved['url'], 'https://dl.acm.org/doi/10.1145/3691620.3695329')

    def test_doi_resolver_reports_all_failures(self):
        failing_response = Mock()
        failing_response.raise_for_status.side_effect = self.doi_resolver.requests.exceptions.HTTPError('failure')

        with patch.object(self.doi_resolver.requests, 'get', return_value=failing_response):
            with self.assertRaisesRegex(ValueError, 'Failed to resolve DOI'):
                self.doi_resolver.resolve_doi('10.1234/missing')

    def test_cstr_resolver_uses_cstr_cn_successfully(self):
        response = Mock()
        response.text = '<html><body>CSTR landing page</body></html>'
        response.url = 'https://cstr.cn/15398.11.A00120001'
        response.raise_for_status = Mock()

        with patch.object(self.cstr_resolver.requests, 'get', return_value=response):
            resolved = self.cstr_resolver.resolve_cstr('15398.11.A00120001', clean_html=lambda html: f'cleaned {html}')

        self.assertEqual(resolved['source'], 'cstr.cn')
        self.assertEqual(resolved['url'], 'https://cstr.cn/15398.11.A00120001')
        self.assertEqual(resolved['content'], 'cleaned <html><body>CSTR landing page</body></html>')

    def test_cstr_resolver_falls_back_to_identifiers_org(self):
        first_response = Mock()
        first_response.raise_for_status.side_effect = self.cstr_resolver.requests.exceptions.HTTPError('cstr failed')

        fallback_response = Mock()
        fallback_response.text = '<html><body>Identifiers page</body></html>'
        fallback_response.url = 'https://identifiers.org/cstr:15398.11.A00120001'
        fallback_response.raise_for_status = Mock()

        with patch.object(self.cstr_resolver.requests, 'get', side_effect=[first_response, fallback_response]):
            resolved = self.cstr_resolver.resolve_cstr('15398.11.A00120001', clean_html=lambda html: f'cleaned {html}')

        self.assertEqual(resolved['source'], 'identifiers.org')
        self.assertEqual(resolved['url'], 'https://identifiers.org/cstr:15398.11.A00120001')
        self.assertEqual(resolved['content'], 'cleaned <html><body>Identifiers page</body></html>')

    def test_cstr_resolver_follows_json_redirect_to_target_resource(self):
        redirect_response = Mock()
        redirect_response.headers = {'content-type': 'application/json'}
        redirect_response.url = 'https://cstr.cn/15398.11.A00120001'
        redirect_response.json.return_value = {'url': 'https://www.plantdiversity.cn/mobile/records/1111300'}
        redirect_response.raise_for_status = Mock()

        target_response = Mock()
        target_response.headers = {'content-type': 'text/html'}
        target_response.text = '<html><body>Full plant diversity record</body></html>'
        target_response.url = 'https://www.plantdiversity.cn/mobile/records/1111300'
        target_response.raise_for_status = Mock()

        with patch.object(self.cstr_resolver.requests, 'get', side_effect=[redirect_response, target_response]):
            resolved = self.cstr_resolver.resolve_cstr('15398.11.A00120001', clean_html=lambda html: f'cleaned {html}')

        self.assertEqual(resolved['source'], 'cstr.cn->redirect')
        self.assertEqual(resolved['url'], 'https://www.plantdiversity.cn/mobile/records/1111300')
        self.assertEqual(resolved['content'], 'cleaned <html><body>Full plant diversity record</body></html>')

    def test_cstr_resolver_follows_html_redirect_to_target_resource(self):
        redirect_response = Mock()
        redirect_response.headers = {'content-type': 'text/html'}
        redirect_response.text = '<html><script>window.location.href="/mobile/records/1111300"</script></html>'
        redirect_response.url = 'https://www.plantdiversity.cn/redirect'
        redirect_response.raise_for_status = Mock()

        target_response = Mock()
        target_response.headers = {'content-type': 'application/json'}
        target_response.json.return_value = {'title': 'Full plant diversity record', 'id': '1111300'}
        target_response.text = '{"title":"Full plant diversity record","id":"1111300"}'
        target_response.url = 'https://www.plantdiversity.cn/mobile/records/1111300'
        target_response.raise_for_status = Mock()

        with patch.object(self.cstr_resolver.requests, 'get', side_effect=[redirect_response, target_response]):
            resolved = self.cstr_resolver.resolve_cstr('15398.11.A00120001', clean_html=lambda html: f'cleaned {html}')

        self.assertEqual(resolved['source'], 'cstr.cn->redirect')
        self.assertEqual(resolved['url'], 'https://www.plantdiversity.cn/mobile/records/1111300')
        self.assertIn('"title": "Full plant diversity record"', resolved['content'])

    def test_cstr_resolver_reports_all_failures(self):
        failing_response = Mock()
        failing_response.raise_for_status.side_effect = self.cstr_resolver.requests.exceptions.HTTPError('failure')

        with patch.object(self.cstr_resolver.requests, 'get', return_value=failing_response):
            with self.assertRaisesRegex(ValueError, 'Failed to resolve CSTR'):
                self.cstr_resolver.resolve_cstr('15398.11.A00120001')


if __name__ == '__main__':
    unittest.main()
