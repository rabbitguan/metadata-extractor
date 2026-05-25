import re
from bs4 import BeautifulSoup
import cssutils
from cstr_resolver import resolve_cstr
from doi_resolver import resolve_doi
from get_id import get_typed_identifiers


def merge_nested_tags(html):
    """合并嵌套的相同标签"""
    tag_pattern = re.compile(r'<(\/?)([^>]+)>')
    stack = []
    result = []
    last_index = 0
    
    for match in tag_pattern.finditer(html):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2)
        match_start = match.start()
        match_end = match.end()
        
        # 添加标签前的文本
        result.append(html[last_index:match_start])
        last_index = match_end
        
        if is_closing:
            if stack and stack[-1] == tag_name:
                stack.pop()
                # 如果栈顶还是相同标签，则不添加这个闭合标签
                if stack and stack[-1] == tag_name:
                    continue
            result.append(f'</{tag_name}>')
        else:
            # 如果栈顶是相同标签，则不添加这个开始标签
            if stack and stack[-1] == tag_name:
                continue
            stack.append(tag_name)
            result.append(f'<{tag_name}>')
    
    # 添加剩余的文本
    result.append(html[last_index:])
    return ''.join(result)

def remove_empty_tags(html):
    """递归删除空标签"""
    prev_html = None
    pattern = re.compile(r'<([^>]+)></\1>')
    
    while html != prev_html:
        prev_html = html
        html = pattern.sub('', html)
    return html

def process_source_code(source_code):
    """处理源代码的主函数"""
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(source_code, 'html.parser')
    
    # 过滤不可见元素
    for element in soup.find_all():
        # 简单模拟计算样式检查（实际应用中可能需要更复杂的处理）
        style = element.get('style', '')
        if style:
            try:
                css = cssutils.parseStyle(style)
                if (css.get('display') == 'none' or 
                    css.get('visibility') == 'hidden' or 
                    (css.get('opacity') is not None and float(css.get('opacity')) == 0)):
                    element.decompose()
                    continue
            except:
                pass
        
        # 检查是否有隐藏相关的类名（简单判断）
        if 'hidden' in element.get('class', []):
            element.decompose()
            continue
    
    # 移除CSS片段
    for style_tag in soup.find_all('style'):
        style_tag.decompose()
    for link_tag in soup.find_all('link', rel='stylesheet'):
        link_tag.decompose()
    
    # 删除HTML注释
    for comment in soup.find_all(text=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
        comment.extract()
    
    # 删除script标签及其内容
    for script_tag in soup.find_all('script'):
        script_tag.decompose()
    
    # 获取处理后的HTML字符串
    source_code = str(soup)
    
    # 简化标签格式（移除属性）
    source_code = re.sub(r'\s*<(\/?)([^ >]+)[^>]*>\s*', r'<\1\2>', source_code)
    
    # 移除多余空格和换行
    source_code = re.sub(r'\s+', ' ', source_code).strip()
    
    # 合并嵌套相同标签
    source_code = merge_nested_tags(source_code)
    
    # 递归删除空标签
    source_code = remove_empty_tags(source_code)
    
    return source_code

def identify_and_process(text):
    typed_identifiers = get_typed_identifiers(text)
    dois = [item['id'] for item in typed_identifiers if item['type'] == 'doi']
    cstrs = [item['id'] for item in typed_identifiers if item['type'] == 'cstr']
    # print("DOIs found:", dois)
    # print("CSTRs found:", cstrs)
    content_list = []
    for doi in dois:
        try:
            content_list.append(resolve_doi(doi, clean_html=process_source_code)['content'])
        except Exception as e:
            print(f"[WARNING] Error processing DOI {doi}: {e}")
            continue
    for cstr in cstrs:
        try:
            content_list.append(resolve_cstr(cstr, clean_html=process_source_code)['content'])
        except Exception as e:
            print(f"[WARNING] Error processing CSTR {cstr}: {e}")
            continue
    return content_list
