import os
import pathlib
import subprocess
import urllib.parse
import urllib.request

from html.parser import HTMLParser


def fetch_html_contents(url):
    request = urllib.request.Request(url, headers={"User-Agent": ""})
    with urllib.request.urlopen(request) as f:
        return f.read().decode("utf-8")


def url_to_path(url):
    result = urllib.parse.urlparse(url)
    return pathlib.Path(
        f"{result.netloc.replace('.', '_')}{urllib.parse.unquote(result.path)}"
    )


def download_pdf_file(url, output_dir):
    request = urllib.request.Request(url)
    request.add_header("User-Agent", "")

    file_path = pathlib.Path(output_dir, url_to_path(url).with_suffix(".pdf"))

    os.makedirs(file_path.parent, exist_ok=True)

    print(f"Downloading {url} to {file_path}")

    with urllib.request.urlopen(request) as r:
        with open(file_path, "wb") as w:
            w.write(r.read())

    return file_path


def convert_pdf_to_text(pdf_file_path, output_dir, file_names):
    text_file_name = pdf_file_path.with_suffix(".txt").name
    if text_file_name in file_names:
        text_file_name = file_names[text_file_name]
    text_file_path = pathlib.Path(output_dir, "text", text_file_name)
    os.makedirs(text_file_path.parent, exist_ok=True)
    print(f"Converting {pdf_file_path} to {text_file_path}")
    subprocess.run(["pdftotext", "-layout", "-nopgbrk", pdf_file_path, text_file_path])
    return text_file_path


def md_link(file_path, md_file_dir):
    return urllib.parse.quote(str(file_path.relative_to(md_file_dir)))


class ResourcesHTMLParser(HTMLParser):
    URL_PREFIXES = (
        "https://cdn.ravensburger.com/lorcana/",
        "https://files.disneylorcana.com/",
    )

    DOCUMENTS_TO_CONVERT_TO_TXT = (
        "Community Code",
        "Comprehensive Rules",
        "Disney Lorcana TCG: The First Chapter Set Notes",
        "Diversity & Inclusion Policy",
        "Play Correction Guidelines",
        "Tournament Rules",
        "《泼墨第一章》常见问题",
        "多样性和包容性方针",
        "完整规则",
        "比赛规则",
        "社群规则",
        "纠正指南",
    )

    TEXT_FILE_NAMES = {
        "Disney Lorcana Comprehensive Rules - 022825 - DE.txt": "comprehensive-rules-de.txt",
        "Disney Lorcana Comprehensive Rules - 022825 - EN.txt": "comprehensive-rules-en.txt",
        "Disney Lorcana Comprehensive Rules - 022825 - FR.txt": "comprehensive-rules-fr.txt",
        "Disney Lorcana Comprehensive Rules - 022825 - IT.txt": "comprehensive-rules-it.txt",
        "Disney_Lorcana_Play_Correction_Guidelines_052124update.txt": "play-correction-guidelines-en.txt",
        "Disney_Lorcana_Tournament_Rules_052224update.txt": "tournament-rules-en.txt",
        "完整规则.txt": "comprehensive-rules-zh.txt",
        "纠正指南.txt": "play-correction-guidelines-zh.txt",
        "迪士尼洛卡纳中国区比赛规则v20241230.txt": "tournament-rules-zh.txt",
        "迪士尼洛卡纳集换式卡牌游戏社群规则v20241230.txt": "community-code-zh.txt",
        "迪士尼洛卡纳集换式卡牌游戏组织游戏多样性和包容性方针v20241225.txt": "op-diversity-and-inclusion-policy-zh.txt",
        "迪士尼洛卡纳集换式卡牌游戏：《泼墨第一章》常见问题.txt": "s1-set-notes-zh.txt",
    }

    def __init__(self, readme_file, output_dir):
        super().__init__()

        self.readme_file = readme_file
        self.output_dir = output_dir

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
                            pdf_file_path = download_pdf_file(
                                attr_value, self.output_dir
                            )
                            link_to_pdf_file = md_link(pdf_file_path, self.output_dir)
                            self.list_item = f"[{{data}}]({link_to_pdf_file})"
                            if self.document_name in self.DOCUMENTS_TO_CONVERT_TO_TXT:
                                text_file_path = convert_pdf_to_text(
                                    pdf_file_path, self.output_dir, self.TEXT_FILE_NAMES
                                )
                                link_to_text_file = md_link(
                                    text_file_path, self.output_dir
                                )
                                self.list_item = (
                                    f"[{{data}}]({link_to_pdf_file})"
                                    f" ([as text]({link_to_text_file}))"
                                )
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
        "comprehensive_rules.txt": "comprehensive-rules-jp.txt",
        "Disney_Lorcana_Play_Correction_Guidelines_JP.txt": "play-correction-guidelines-jp.txt",
        "Disney_Lorcana_Tournament_Rules_JP.txt": "tournament-rules-jp.txt",
        "s1_set_notes.txt": "s1-set-notes-jp.txt",
    }

    def __init__(self, readme_file, output_dir):
        super().__init__()

        self.readme_file = readme_file
        self.output_dir = output_dir

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
                        pdf_file_path = download_pdf_file(
                            f"https://takaratomy.co.jp{attr_value}", self.output_dir
                        )
                        text_file_path = convert_pdf_to_text(
                            pdf_file_path, self.output_dir, self.TEXT_FILE_NAMES
                        )
                        self.item = (
                            f"[{{data}}]({md_link(pdf_file_path, self.output_dir)})"
                            f" ([as text]({md_link(text_file_path, self.output_dir)}))"
                        )
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


def main():
    subprocess.run(["pdftotext", "-h"], capture_output=True, check=True)

    output_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(output_dir, "README.md"), "w") as readme_file:
        print("# Disney Lorcana TCG Resources", file=readme_file)

        url = "https://www.disneylorcana.com/en-US/resources"
        print(f"\n\n*from {url}*", file=readme_file)

        contents = fetch_html_contents(url)

        parser = ResourcesHTMLParser(readme_file, output_dir)
        parser.feed(contents)

        print("\n\n------", file=readme_file)

        url = "https://www.disneylorcana.com/zh-CN/resources"
        print(f"\n\n*from {url}*", file=readme_file)

        contents = fetch_html_contents(url)

        parser = ResourcesHTMLParser(readme_file, output_dir)
        parser.feed(contents)

        print("\n\n------", file=readme_file)

        url = "https://www.takaratomy.co.jp/products/disneylorcana/rule-faq/"
        print(f"\n\n*from {url}*", file=readme_file)

        contents = fetch_html_contents(url)

        parser = RuleFaqHTMLParser(readme_file, output_dir)
        parser.feed(contents)


if __name__ == "__main__":
    main()
