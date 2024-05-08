import os
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
        self.href = None

    def download_file(self, url):
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "")

        result = urllib.parse.urlparse(url)
        relative_url = f"{result.netloc.replace('.', '_')}{result.path}"
        if not relative_url.endswith(".pdf"):
            relative_url = f"{relative_url}.pdf"

        file_path = os.path.join(self.output_dir, urllib.parse.unquote(relative_url))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        print(f"Downloading {url} to {file_path}")

        with urllib.request.urlopen(request) as r:
            with open(file_path, "wb") as w:
                w.write(r.read())

        return relative_url

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
                        assert self.href is None
                        if attr_value.startswith(URL_PREFIXES):
                            self.href = self.download_file(attr_value)
                        else:
                            self.href = attr_value
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

        elif self.href is not None:
            print(f"- [{data}]({self.href})", file=self.readme_file)

    def handle_endtag(self, tag):
        if tag == "section":
            self.in_faq_section = False

        elif tag == "h2":
            self.in_faq_block_title = False
            self.in_accordion_header = False

        elif tag == "a":
            self.href = None


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
