document.addEventListener('DOMContentLoaded', function() {
    const status = document.getElementById('status');
    const sourceCodeElement = document.getElementById('sourceCode');

    // 显示加载状态
    status.textContent = 'Loading page source...';
    status.className = 'status loading';

    // 获取当前活动标签页
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
        const tab = tabs[0];

        // 执行脚本获取页面源代码
        chrome.scripting.executeScript({
            target: {tabId: tab.id},
            function: () => document.documentElement.outerHTML
        }).then((results) => {
            if (results && results[0] && results[0].result) {
                let sourceCode = results[0].result;

                // 创建一个临时的 DOM 元素来解析 HTML
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = sourceCode;

                // 过滤不可见元素
                const allElements = tempDiv.getElementsByTagName('*');
                for (let i = allElements.length - 1; i >= 0; i--) {
                    const element = allElements[i];
                    const style = window.getComputedStyle(element);
                    if (
                        style.display === 'none' ||
                        style.visibility === 'hidden' ||
                        parseFloat(style.opacity) === 0
                    ) {
                        element.parentNode.removeChild(element);
                    }
                }

                // 获取过滤后的源代码
                sourceCode = tempDiv.innerHTML;
                // 移除 CSS 片段
                sourceCode = sourceCode.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
                sourceCode = sourceCode.replace(/<link[^>]*rel="stylesheet"[^>]*>/gi, '');
                // 删除 HTML 注释
                sourceCode = sourceCode.replace(/<!--[\s\S]*?-->/g, '');
                // 删除 script 标签及其内容
                sourceCode = sourceCode.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
                sourceCode = sourceCode.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
                // 删除标签前后的空格，并只保留最原始的标签名称
                sourceCode = sourceCode.replace(/\s*<(\/?)([^ >]+)[^>]*>\s*/g, '<$1$2>');
                // 移除多个空格和换行符
                sourceCode = sourceCode.replace(/\s+/g, ' ').trim();
                // 合并嵌套的相同标签
                sourceCode = mergeNestedTags(sourceCode);
                // 递归删除空标签
                sourceCode = removeEmptyTags(sourceCode);
                // // 合并嵌套的相同标签，保留最内层
                // sourceCode = mergeNestedTagsKeepInnermost(sourceCode);

                sourceCodeElement.textContent = sourceCode;
                const resourceUrlInput = document.getElementById('resourceurl');
                resourceUrlInput.value = tab.url;
                status.textContent = `Loaded ${sourceCode.length} characters`;
                status.className = 'status success';
            } else {
                throw new Error('No result returned');
            }
        }).catch((error) => {
            console.error('Error:', error);
            status.textContent = 'Failed to load source code';
            status.className = 'status error';
        });
    });
    // 合并嵌套的相同标签的函数
    function mergeNestedTags(html) {
        const tagRegex = /<(\/?)([^>]+)>/g;
        let matches;
        const stack = [];
        let result = '';
        let lastIndex = 0;

        while ((matches = tagRegex.exec(html)) !== null) {
            const isClosing = matches[1] === '/';
            const tagName = matches[2];
            const matchIndex = matches.index;
            const matchLength = matches[0].length;

            result += html.substring(lastIndex, matchIndex);
            lastIndex = matchIndex + matchLength;

            if (isClosing) {
                if (stack.length > 0 && stack[stack.length - 1] === tagName) {
                    stack.pop();
                    if (stack.length > 0 && stack[stack.length - 1] === tagName) {
                        continue;
                    }
                }
                result += `</${tagName}>`;
            } else {
                if (stack.length > 0 && stack[stack.length - 1] === tagName) {
                    continue;
                }
                stack.push(tagName);
                result += `<${tagName}>`;
            }
        }

        result += html.substring(lastIndex);
        return result;
    }

    // 递归删除空标签的函数
    function removeEmptyTags(html) {
        let prevHtml;
        // 循环处理直到没有变化
        do {
            prevHtml = html;
            // 匹配空标签模式
            html = html.replace(/<([^>]+)><\/\1>/g, '');
        } while (html !== prevHtml);
        return html;
    }
    // 合并嵌套标签并保留最内层的函数实现
    function mergeNestedTagsKeepInnermost(html) {
        const tagRegex = /<(\/?)([^>]+)>/g;
        let matches;
        const stack = [];
        let result = '';
        let lastIndex = 0;

        while ((matches = tagRegex.exec(html)) !== null) {
            const isClosing = matches[1] === '/';
            const tagName = matches[2];
            const matchIndex = matches.index;
            const matchLength = matches[0].length;

            result += html.substring(lastIndex, matchIndex);
            lastIndex = matchIndex + matchLength;

            if (isClosing) {
                // 闭合标签：检查栈顶是否有相同标签
                let foundMatch = false;
                while (stack.length > 0) {
                    const topTagName = stack.pop();
                    if (topTagName === tagName) {
                        // 找到匹配的开始标签，添加到结果
                        result += `</${tagName}>`;
                        foundMatch = true;
                        break;
                    }
                    // 不匹配的标签被丢弃
                }
                
                if (!foundMatch) {
                    // 没有找到匹配的开始标签，添加闭合标签（异常情况）
                    result += `</${tagName}>`;
                }
            } else {
                // 开始标签：如果与栈顶标签相同，则跳过
                if (stack.length > 0 && stack[stack.length - 1] === tagName) {
                    // 嵌套的相同标签，跳过当前开始标签
                    continue;
                }
                // 正常添加开始标签到栈
                stack.push(tagName);
                result += `<${tagName}>`;
            }
        }

        result += html.substring(lastIndex);
        return result;
    }
    // 处理下载按钮点击事件
    const downloadButton = document.getElementById('downloadButton');
    downloadButton.addEventListener('click', function() {
        const identifier = document.getElementById('identifier').value || null;
        const name = document.getElementById('name').value || null;
        const description = document.getElementById('description').value || null;
        const keyword = document.getElementById('keyword').value || null;
        const dataofcreate = document.getElementById('dataofcreate').value || null;
        const dataoflast = document.getElementById('dataoflast').value || null;
        const resourceurl = document.getElementById('resourceurl').value || null;
        const resourceauthor = document.getElementById('resourceauthor').value || null;
        const resourceorginazation = document.getElementById('resourceorginazation').value || null;
        const authoremail = document.getElementById('authoremail').value || null;
        const journal = document.getElementById('journal').value || null;
        const sourceCode = sourceCodeElement.textContent;

        const data = {
            identifier,
            name,
            description,
            keyword,
            dataofcreate,
            dataoflast,
            resourceurl,
            resourceauthor,
            resourceorginazation,
            authoremail,
            journal,
            sourceCode
        };

        const jsonData = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = 'page_info.json';
        a.click();

        URL.revokeObjectURL(url);
    });
});