import os
import pathlib
import sys
import urllib.parse
import urllib.request

from html.parser import HTMLParser


URL_PREFIXES = (
    "https://cdn.ravensburger.com/lorcana/",
    "https://files.disneylorcana.com/",
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
                f"- {self.list_item.format(data=data)}",
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
