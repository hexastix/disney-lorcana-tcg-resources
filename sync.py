import concurrent.futures
import os
import pathlib
import subprocess
import urllib.parse
import urllib.request

from html.parser import HTMLParser


def fetch_html_contents(url):
    print(f"Fetching {url}")
    request = urllib.request.Request(url, headers={"User-Agent": ""})
    with urllib.request.urlopen(request) as f:
        return f.read().decode("utf-8")


def url_to_path(url):
    result = urllib.parse.urlparse(url)
    return pathlib.Path(
        f"{result.netloc.replace('.', '_')}{urllib.parse.unquote(result.path)}"
    )


def md_link(path):
    return urllib.parse.quote(str(path))


class ResourcesHTMLParser(HTMLParser):
    URL_PREFIXES = (
        "https://cdn.ravensburger.com/lorcana/",
        "https://files.disneylorcana.com/",
    )

    TEXT_FILE_NAMES = {
        "Disney Lorcana Comprehensive Rules - 103125 - DE.pdf": "comprehensive-rules-de.txt",
        "Disney Lorcana Comprehensive Rules - 103125 - FR.pdf": "comprehensive-rules-fr.txt",
        "Disney Lorcana Comprehensive Rules - 103125 - IT.pdf": "comprehensive-rules-it.txt",
        "Disney Lorcana TCG Tournament Rules S2_09-Sep-25.pdf": "tournament-rules-en.txt",
        "Disney-Lorcana-Comprehensive-Rules-Updated-11252025.pdf": "comprehensive-rules-en.txt",
        "Disney_Lorcana_Play_Correction_Guidelines_052124update.pdf": "play-correction-guidelines-en.txt",
        "Season 2 Tournament Rules 090925 update-Italian.pdf": "tournament-rules-it.txt",
        "Season 2 Turnierregeln 090925-DE.pdf": "tournament-rules-de.txt",
        "community-code-de.pdf": "community-code-de.txt",
        "community-code-en.pdf": "community-code-en.txt",
        "community-code-fr.pdf": "community-code-fr.txt",
        "community-code-it.pdf": "community-code-it.txt",
        "op-diversity-and-inclusion-policy-de.pdf": "op-diversity-and-inclusion-policy-de.txt",
        "op-diversity-and-inclusion-policy-en.pdf": "op-diversity-and-inclusion-policy-en.txt",
        "op-diversity-and-inclusion-policy-fr.pdf": "op-diversity-and-inclusion-policy-fr.txt",
        "op-diversity-and-inclusion-policy-it.pdf": "op-diversity-and-inclusion-policy-it.txt",
        "s1-set-notes-de.pdf": "s1-set-notes-de.txt",
        "s1-set-notes-en.pdf": "s1-set-notes-en.txt",
        "s1-set-notes-fr.pdf": "s1-set-notes-fr.txt",
        "s1-set-notes-it.pdf": "s1-set-notes-it.txt",
        "完整规则.pdf": "comprehensive-rules-zh.txt",
        "纠正指南.pdf": "play-correction-guidelines-zh.txt",
        "迪士尼洛卡纳中国区比赛规则v20241230.pdf": "tournament-rules-zh.txt",
        "迪士尼洛卡纳集换式卡牌游戏社群规则v20241230.pdf": "community-code-zh.txt",
        "迪士尼洛卡纳集换式卡牌游戏组织游戏多样性和包容性方针v20241225.pdf": "op-diversity-and-inclusion-policy-zh.txt",
        "迪士尼洛卡纳集换式卡牌游戏：《泼墨第一章》常见问题.pdf": "s1-set-notes-zh.txt",
    }

    def __init__(self, readme_file, pdf_files):
        super().__init__()

        self.readme_file = readme_file
        self.pdf_files = pdf_files

        self.in_faq_section = False
        self.in_faq_block_title = False
        self.in_accordion_header = False
        self.document_name = None
        self.list_item = None

    def handle_starttag(self, tag, attrs):
        if self.in_faq_section:
            if tag == "h2":
                for attr_name, attr_value in attrs:
                    if attr_name == "class":
                        if "faq-block-title" in attr_value:
                            assert not self.in_faq_block_title
                            self.in_faq_block_title = True
                            break
                        elif "accordion-header" in attr_value:
                            assert not self.in_accordion_header
                            self.in_accordion_header = True
                            break

            elif tag == "a":
                for attr_name, attr_value in attrs:
                    if attr_name == "href":
                        assert self.list_item is None
                        if attr_value.startswith(self.URL_PREFIXES):
                            url = attr_value
                            pdf_file_path = url_to_path(url).with_suffix(".pdf")
                            if pdf_file_path.name in self.TEXT_FILE_NAMES:
                                text_file_path = pathlib.Path(
                                    "text", self.TEXT_FILE_NAMES[pdf_file_path.name]
                                )
                                self.list_item = (
                                    f"[{{data}}]({md_link(pdf_file_path)})"
                                    f" ([as text]({md_link(text_file_path)}))"
                                )
                                self.pdf_files.append(
                                    (url, pdf_file_path, text_file_path)
                                )
                            else:
                                self.list_item = f"[{{data}}]({md_link(pdf_file_path)})"
                                self.pdf_files.append((url, pdf_file_path, None))
                        else:
                            self.list_item = f"[{{data}}]({attr_value})"
                        break

        elif tag == "section":
            for attr_name, attr_value in attrs:
                if attr_name == "class" and "faq" in attr_value:
                    self.in_faq_section = True
                    break

    def handle_data(self, data):
        if self.in_faq_block_title:
            print(f"\n\n## {data}", file=self.readme_file)

        elif self.in_accordion_header:
            self.document_name = data
            print(f"\n### {data}\n", file=self.readme_file)

        elif self.list_item is not None:
            print(
                f"- {self.list_item.format(data=data.strip())}",
                file=self.readme_file,
            )

    def handle_endtag(self, tag):
        if tag == "section":
            self.in_faq_section = False

        elif tag == "h2":
            self.in_faq_block_title = False
            self.in_accordion_header = False

        elif tag == "a":
            self.list_item = None


class RuleFaqHTMLParser(HTMLParser):
    TEXT_FILE_NAMES = {
        "Disney-Lorcana-Comprehensive-Rules_JP.pdf": "comprehensive-rules-jp.txt",
        "Disney_Lorcana_Play_Correction_Guidelines_JP.pdf": "play-correction-guidelines-jp.txt",
        "Disney_Lorcana_Tournament_Rules_JP.pdf": "tournament-rules-jp.txt",
        "s1_set_notes.pdf": "s1-set-notes-jp.txt",
    }

    def __init__(self, readme_file, pdf_files):
        super().__init__()

        self.readme_file = readme_file
        self.pdf_files = pdf_files

        self.rule_div = False
        self.in_heading_2 = False
        self.in_heading_3 = False
        self.in_heading_3_main = False
        self.item = None

    def handle_starttag(self, tag, attrs):
        if self.rule_div:
            if tag == "h2":
                assert not self.in_heading_2
                self.in_heading_2 = True

            elif tag == "h3":
                assert not self.in_heading_3
                self.in_heading_3 = True
                print("\n### ", end="", file=self.readme_file)

            elif tag == "span":
                for attr_name, attr_value in attrs:
                    if attr_name == "class" and "heading-3-main" in attr_value:
                        assert not self.in_heading_3_main
                        self.in_heading_3_main = True
                        break

            elif tag == "a":
                for attr_name, attr_value in attrs:
                    if attr_name == "href":
                        assert self.item is None
                        url = f"https://takaratomy.co.jp{attr_value}"
                        pdf_file_path = url_to_path(url).with_suffix(".pdf")
                        text_file_path = pathlib.Path(
                            "text", self.TEXT_FILE_NAMES[pdf_file_path.name]
                        )
                        self.item = (
                            f"[{{data}}]({md_link(pdf_file_path)})"
                            f" ([as text]({md_link(text_file_path)}))"
                        )
                        self.pdf_files.append((url, pdf_file_path, text_file_path))
                        break

        elif tag == "div":
            for attr_name, attr_value in attrs:
                if attr_name == "id" and attr_value == "rule":
                    self.rule_div = True
                    break

    def handle_data(self, data):
        if self.in_heading_2:
            print(f"\n\n## {data}", file=self.readme_file)

        elif self.in_heading_3_main:
            print(data, end="", file=self.readme_file)

        elif self.item is not None:
            print(f"\n{self.item.format(data=data)}", file=self.readme_file)

    def handle_endtag(self, tag):
        if tag == "div":
            self.rule_div = False

        elif self.rule_div:
            if tag == "h2":
                self.in_heading_2 = False

            elif tag == "h3":
                print("", file=self.readme_file)
                self.in_heading_3 = False

            elif tag == "span":
                self.in_heading_3_main = False

            elif tag == "a":
                self.item = None


def download_file(url, file_path):
    print(f"Downloading {url} to {file_path}")
    os.makedirs(file_path.parent, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": ""})
    with urllib.request.urlopen(request) as r:
        with open(file_path, "wb") as w:
            w.write(r.read())


def convert_pdf_to_text(pdf_file_path, text_file_path):
    print(f"Converting {pdf_file_path} to {text_file_path}")
    os.makedirs(text_file_path.parent, exist_ok=True)
    subprocess.run(["pdftotext", "-layout", "-nopgbrk", pdf_file_path, text_file_path])


def download_and_convert_pdf_file(output_dir, url, pdf_file_path, text_file_path):
    download_file(url, pathlib.Path(output_dir, pdf_file_path))
    if text_file_path:
        convert_pdf_to_text(
            pathlib.Path(output_dir, pdf_file_path),
            pathlib.Path(output_dir, text_file_path),
        )


def main():
    subprocess.run(["pdftotext", "-h"], capture_output=True, check=True)

    output_dir = os.path.dirname(os.path.abspath(__file__))

    pdf_files = []

    with open(os.path.join(output_dir, "README.md"), "w") as readme_file:
        print("# Disney Lorcana TCG Resources", file=readme_file)

        url = "https://www.disneylorcana.com/en-US/resources"
        print(f"\n\n*from {url}*", file=readme_file)

        contents = fetch_html_contents(url)

        parser = ResourcesHTMLParser(readme_file, pdf_files)
        parser.feed(contents)

        print("\n\n------", file=readme_file)

        url = "https://www.disneylorcana.com/zh-CN/resources"
        print(f"\n\n*from {url}*", file=readme_file)

        contents = fetch_html_contents(url)

        parser = ResourcesHTMLParser(readme_file, pdf_files)
        parser.feed(contents)

        print("\n\n------", file=readme_file)

        url = "https://www.takaratomy.co.jp/products/disneylorcana/rule-faq/"
        print(f"\n\n*from {url}*", file=readme_file)

        contents = fetch_html_contents(url)

        parser = RuleFaqHTMLParser(readme_file, pdf_files)
        parser.feed(contents)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(download_and_convert_pdf_file, output_dir, *pdf_file)
            for pdf_file in pdf_files
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
