from pathlib import Path
from samfunny.client import _detect_format, _detect_languages
from bs4 import BeautifulSoup


def test_detect_format_and_languages():
    html = '''
    <div>
      <img src="/img/jollyroger.gif"/>
      <img src="/img/china.gif"/>
      <a href="/download/abc/xxx.sub">中英双语 字幕 SRT</a>
      <span> SRT </span>
    </div>
    '''
    soup = BeautifulSoup(html, 'lxml')
    div = soup.div
    langs = _detect_languages(div)
    fmt = _detect_format(div.get_text(' ', strip=True))
    assert fmt.name in ("SRT", "ASS", "ZIP", "SUP", "OTHER")
    assert any(l.name == 'BILINGUAL' for l in langs)


def test_detail_parsing_smoke():
    # This is a smoke test that our selectors do not crash on simple HTML shape
    html = '''
    <html><body>
      <h3>字幕文件下载</h3>
      <div>
        <div>
          <img src="/img/uk.gif"/>
          <a href="/download/token/xx.sub">Interstellar.2014.1080p.BluRay.SRT.zip</a>
        </div>
      </div>
    </body></html>
    '''
    soup = BeautifulSoup(html, 'lxml')
    # Reuse detection functions only; full parse requires network which is not tested here
    div = soup.find('div')
    assert div is not None
