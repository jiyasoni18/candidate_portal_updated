import re
text = 'Check my [LinkedIn](https://linkedin.com&foo=1) and <a href="https://github.com" color="blue">GitHub</a>.'
# 1. Convert markdown links
text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
# 2. Fix a tags
text = re.sub(r'<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', r'<link href="\1"><font color="blue"><u>\2</u></font></link>', text)
# 3. Escape lone ampersands (but not if they are part of &amp; or &lt; etc)
# Actually, ReportLab expects &amp;, &lt;, &gt;
# We need to escape & to &amp; but avoid double escaping
text = re.sub(r'&(?!(amp|lt|gt|quot|apos);)', '&amp;', text)
print(text)
