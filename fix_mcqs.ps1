$file = "F:\muni48\frontend\src\pages\MCQs.jsx"
Copy-Item $file "F:\muni48\backup_MCQs_before_http.jsx" -Force

$utf8 = New-Object System.Text.UTF8Encoding($false)
$c = [System.IO.File]::ReadAllText($file, $utf8)

# 1) Import: axios -> http
$c = $c.Replace('import axios from "axios";', 'import http from "../api";')

# 2) Practice call: axios.get(...) -> http.get(...)
$pattern1 = '(?s)const response\s*=\s*await axios\.get\(\s*`\$\{API_URL\}/news/mcqs/practice`,.*?\n\s*\}\s*\n\s*\);'
$replace1 = @'
const response = await http.get("/news/mcqs/practice", {
                        timeout: 20000,
                        params: {
                            page: 1,
                            page_size: PRACTICE_PAGE_SIZE,
                            language: currentLanguage,
                        },
                    });
'@
$c = [regex]::Replace($c, $pattern1, $replace1.TrimEnd(), 1)

# 3) Generate call: axios.post(...) -> http.post(...)
$pattern2 = '(?s)const response\s*=\s*await axios\.post\(\s*`\$\{API_URL\}/news/\$\{articleId\}/mcqs/generate`,.*?\n\s*\}\s*\n\s*\);'
$replace2 = @'
const response = await http.post(
                        `/news/${articleId}/mcqs/generate`,
                        {},
                        {
                            timeout: 60000,
                            params: { language: currentLanguage },
                        }
                    );
'@
$c = [regex]::Replace($c, $pattern2, $replace2.TrimEnd(), 1)

[System.IO.File]::WriteAllText($file, $c, $utf8)
Write-Host "Done"