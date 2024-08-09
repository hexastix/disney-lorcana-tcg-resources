import os
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

from html.parser import HTMLParser


URL_PREFIXES = (
    "https://cdn.ravensburger.com/lorcana/",
    "https://files.disneylorcana.com/",
)

FILES_TO_CONVERT = (
    "Disney Lorcana Comprehensive Rules_EN_08.09.24.pdf",
    "Disney-Lorcana-Comprehensive-Rules_DE_08.09.24.pdf",
    "Disney Lorcana Comprehensive Rules_FR_08.09.24.pdf",
    "Disney_Lorcana_Play_Correction_Guidelines_052124update.pdf",
    "Disney_Lorcana_Tournament_Rules_052224update.pdf",
    "community-code-en.pdf",
    "op-diversity-and-inclusion-policy-en.pdf",
    "s1-set-notes-en.pdf",
)


class ResourcesHTMLParser(HTMLParser):
    def __init__(self, readme_file, output_dir):
        super().__init__()

        self.readme_file = readme_file
        self.output_dir = output_dir

        self.in_faq_section = False
        self.in_faq_block_title = False
        self.in_accordion_header = False
        self.list_item = None

    def download_pdf_file(self, url):
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "")

        result = urllib.parse.urlparse(url)

        file_path = pathlib.Path(
            self.output_dir,
            f"{result.netloc.replace('.', '_')}{urllib.parse.unquote(result.path)}",
        ).with_suffix(".pdf")

        os.makedirs(file_path.parent, exist_ok=True)

        print(f"Downloading {url} to {file_path}")

        with urllib.request.urlopen(request) as r:
            with open(file_path, "wb") as w:
                w.write(r.read())

        return file_path

    def convert_pdf_to_text(self, pdf_file_path):
        text_file_path = pathlib.Path(
            self.output_dir, "text", pdf_file_path.with_suffix(".txt").name
        )
        os.makedirs(text_file_path.parent, exist_ok=True)
        print(f"Converting {pdf_file_path} to {text_file_path}")
        subprocess.run(
            ["pdftotext", "-layout", "-nopgbrk", pdf_file_path, text_file_path]
        )
        return text_file_path

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
                        if attr_value.startswith(URL_PREFIXES):
                            pdf_file_path = self.download_pdf_file(attr_value)
                            link_to_pdf_file = urllib.parse.quote(
                                str(pdf_file_path.relative_to(self.output_dir))
                            )
                            self.list_item = f"[{{data}}]({link_to_pdf_file})"
                            if pdf_file_path.name in FILES_TO_CONVERT:
                                text_file_path = self.convert_pdf_to_text(pdf_file_path)
                                link_to_text_file = urllib.parse.quote(
                                    str(text_file_path.relative_to(self.output_dir))
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


def main():
    subprocess.run(["pdftotext", "-h"], capture_output=True, check=True)

    request = urllib.request.Request("https://www.disneylorcana.com/en-US/resources")
    request.add_header("User-Agent", "")

    with urllib.request.urlopen(request) as f:
        contents = f.read().decode("utf-8")

    output_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(output_dir, "README.md"), "w") as readme_file:
        print("# Disney Lorcana TCG Resources", file=readme_file)

        parser = ResourcesHTMLParser(readme_file, output_dir)
        parser.feed(contents)


if __name__ == "__main__":
    main()
